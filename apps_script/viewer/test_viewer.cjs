// All data below is synthetic. No Drive or transcription-service calls.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const path = require('node:path');
const server = fs.readFileSync(path.join(__dirname, 'Code.gs'), 'utf8');
const html = fs.readFileSync(path.join(__dirname, 'Viewer.html'), 'utf8');
const bytes = Buffer.from('synthetic JPEG bytes');
const hash = crypto.createHash('sha256').update(bytes).digest('hex');

function fixture() {
  const scan = (id, order) => ({ image_id: id, filename: id + '.jpg', path: 'folder/' + id + '.jpg',
    folder: 'folder', order, status: 'ready', size: bytes.length, sha256: hash,
    drive_file_id: 'synthetic_drive_' + id, mapping_status: 'mapped' });
  return { schema_version: 1, letters: [{
    letter_id: 'ltr_one', active: true, execution: 'complete', grouping: 'provisional',
    metadata_review: 'unreviewed', transcription_review: 'unreviewed', relationship_review: 'unreviewed',
    review_reasons: [], metadata: { sender: { value: 'A <script>bad()</script>' },
      recipient: { value: 'B' }, date: { value: '1899-05-01', normalized: '1899-05-01', precision: 'day', certainty: 'explicit' } },
    summary: 'Synthetic test', notes: [], partial_response: '',
    pages: [{ image_id: 'img_B', status: 'text', text: '<img src=x onerror=bad()> & café\n0012', annotations: [] },
      { image_id: 'img_A', status: 'blank', text: '[blank]', annotations: [] }],
    scans: [scan('img_B', 1), scan('img_A', 2)], provenance: { model: 'synthetic' }
  }], links: [], unresolved: [], warnings: [] };
}

function context(bundle = fixture(), options = {}) {
  let gateReads = 0, imageReads = 0, folderReads = 0;
  const lookups = [];
  const blob = { getDataAsString: () => JSON.stringify(bundle), getBytes: () => [...bytes] };
  const file = { getName: () => 'synthetic', isTrashed: () => false, getId: () => 'export',
    getSize: () => JSON.stringify(bundle).length, getLastUpdated: () => new Date(1000),
    getBlob: () => blob };
  const image = { ...file, getSize: () => bytes.length, getMimeType: () => 'image/jpeg',
    getBlob: () => { imageReads++; return blob; } };
  function iterator(items) {
    let index = 0;
    return { hasNext: () => index < items.length, next: () => items[index++] };
  }
  function folder(tree) {
    return { isTrashed: () => Boolean(tree.trashed),
      getFoldersByName(name) {
        lookups.push('folder:' + name);
        return iterator(((tree.folders || {})[name] || []).map(folder));
      },
      getFilesByName(name) {
        lookups.push('file:' + name);
        return iterator(((tree.files || {})[name] || []).map(id => ({ ...image, getId: () => id, ...options.image })));
      } };
  }
  const folderTree = options.folderTree || { folders: { folder: [{ files: {
    'img_B.jpg': ['resolved_drive_img_B'], 'img_A.jpg': ['resolved_drive_img_A'] } }] } };
  const sandbox = {
    DriveApp: { getFileById(id) {
      if (id === 'gate') { gateReads++; if (options.deny) throw Error('denied'); return file; }
      if (id === 'export') return file;
      if (options.imageError) throw Error('hidden existence');
      return { ...image, getId: () => id, ...options.image };
    }, getFolderById(id) {
      folderReads++;
      if (options.folderError || id !== options.scanRoot) throw Error('hidden folder existence');
      return folder(folderTree);
    } },
    Utilities: { DigestAlgorithm: { SHA_256: 'sha256' },
      computeDigest: (_, data) => [...crypto.createHash('sha256').update(Buffer.from(data)).digest()],
      base64Encode: data => Buffer.from(data).toString('base64') },
    console
  };
  vm.createContext(sandbox);
  vm.runInContext(server.replace(/\bACCESS_FILE_ID:\s*'[^']*'/, "ACCESS_FILE_ID: 'gate'")
    .replace(/\bEXPORT_FILE_ID:\s*'[^']*'/, "EXPORT_FILE_ID: 'export'")
    .replace(/\bSCAN_ROOT_FOLDER_ID:\s*'[^']*'/, "SCAN_ROOT_FOLDER_ID: '" + (options.scanRoot || '') + "'"), sandbox);
  return { sandbox, lookups, counts: () => ({ gateReads, imageReads, folderReads }) };
}

test('search sender recipient date and saved text without image reads', () => {
  const c = context();
  for (const query of ['A <script>', 'B', '1899-05', 'café']) {
    assert.equal(c.sandbox.searchLetters(query).total, 1);
  }
  assert.equal(c.counts().imageReads, 0);
  assert.equal(c.counts().gateReads, 4);
});

test('access revoked denies export and scan RPC', () => {
  const { sandbox } = context(fixture(), { deny: true });
  assert.throws(() => sandbox.searchLetters(''), /Access denied/);
  assert.throws(() => sandbox.listFolders(''), /Access denied/);
  assert.throws(() => sandbox.loadLetter('ltr_one'), /Access denied/);
  assert.throws(() => sandbox.loadImage({}), /Access denied/);
});

test('source order remains exactly as exported', () => {
  const result = context().sandbox.loadLetter('ltr_one');
  assert.equal(result.letter.scans[0].image_id, 'img_B');
  assert.equal(result.letter.scans[1].image_id, 'img_A');
});

test('unprocessed filename hints remain searchable and distinct from metadata', () => {
  const bundle = fixture();
  bundle.letters[0].metadata = {};
  bundle.letters[0].hints = { sender: 'FilenameSender', recipient: 'FilenameRecipient', date: '1800' };
  bundle.letters[0].execution = 'unprocessed';
  const c = context(bundle);
  assert.equal(c.sandbox.searchLetters('FilenameSender').total, 1);
  const f = frontend();
  f.sandbox.renderLetter({ letter: bundle.letters[0], token: 't', links: [], unresolved: [], warnings: [] });
  assert.match(allNodes(f.ids.record).map(n => n.textContent).join('\n'), /Provisional filename\/folder hints/);
});

test('missing letter is not fabricated', () => {
  assert.throws(() => context().sandbox.loadLetter('unknown'), /absent/);
});

test('compact filenames are searchable and displayed in exported page order', () => {
  const bundle = fixture();
  const letter = bundle.letters[0];
  const names = ['Sender-Recipient-18990501_01.jpg', 'Sender-Recipient-18990501_02.jpg'];
  letter.hints = { sender: 'Sender', recipient: 'Recipient', date: '1899-05-01', filenames: names };
  letter.scans.forEach((scan, i) => { scan.filename = names[i]; scan.path = 'folder/' + names[i]; });
  const c = context(bundle);
  for (const query of ['18990501', '1899-05-01', names[1]]) {
    assert.equal(c.sandbox.searchLetters(query).total, 1);
  }
  const loaded = c.sandbox.loadLetter('ltr_one');
  const f = frontend();
  f.sandbox.renderLetter(loaded);
  const text = allNodes(f.ids.record).map(n => n.textContent).join('\n');
  assert.ok(text.includes(names[0]) && text.includes(names[1]));
  assert.equal(loaded.letter.scans[0].image_id, 'img_B');
  assert.equal(loaded.letter.scans[1].image_id, 'img_A');
  assert.equal(c.counts().imageReads, 0);
});

test('authenticated mapped image hash checked and original URL built server side', () => {
  const c = context();
  const result = c.sandbox.loadLetter('ltr_one');
  const image = c.sandbox.loadImage({ token: result.token, letter_id: 'ltr_one', image_id: 'img_B' });
  assert.equal(image.status, 'ready');
  assert.match(image.data, /^data:image\/jpeg;base64,/);
  assert.match(image.url, /^https:\/\/drive.google.com\/file\/d\/synthetic_drive_img_B/);
  assert.equal(c.counts().gateReads, 2);
});

test('missing mapping is different from missing local scan', () => {
  const bundle = fixture();
  delete bundle.letters[0].scans[0].drive_file_id;
  bundle.letters[0].scans[1].status = 'missing';
  const c = context(bundle), token = c.sandbox.loadLetter('ltr_one').token;
  assert.equal(c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'img_B' }).status, 'missing_mapping');
  assert.equal(c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'img_A' }).status, 'missing_scan');
});

test('Drive access failure does not assert that scan never existed', () => {
  const c = context(fixture(), { imageError: true }), token = c.sandbox.loadLetter('ltr_one').token;
  const answer = c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'img_B' });
  assert.equal(answer.status, 'inaccessible');
  assert.match(answer.message, /does not distinguish/);
});

test('trashed scan is explicitly missing', () => {
  const c = context(fixture(), { image: { isTrashed: () => true } }), token = c.sandbox.loadLetter('ltr_one').token;
  assert.equal(c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'img_B' }).status, 'missing_scan');
});

test('changed export or scan never substitutes different evidence', () => {
  const bundle = fixture();
  bundle.letters[0].scans[0].sha256 = '0'.repeat(64);
  const c = context(bundle), token = c.sandbox.loadLetter('ltr_one').token;
  assert.equal(c.sandbox.loadImage({ token: 'old', letter_id: 'ltr_one', image_id: 'img_B' }).status, 'changed');
  assert.equal(c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'img_B' }).status, 'changed');
});

test('cannot use RPC to read unrelated Drive file', () => {
  const c = context(), token = c.sandbox.loadLetter('ltr_one').token;
  assert.throws(() => c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'unrelated' }), /not part/);
});

test('large gallery refused before image read', () => {
  const bundle = fixture();
  bundle.letters[0].scans[0].size = 25 * 1024 * 1024;
  const c = context(bundle), token = c.sandbox.loadLetter('ltr_one').token;
  assert.equal(c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'img_B' }).status, 'too_large');
  assert.equal(c.counts().imageReads, 0);
});

function unmappedFixture() {
  const bundle = fixture();
  for (const scan of bundle.letters[0].scans) {
    delete scan.drive_file_id; scan.mapping_status = 'missing_mapping';
  }
  return bundle;
}

test('configured collection folder resolves exact exported paths and verifies bytes', () => {
  const bundle = unmappedFixture(), c = context(bundle, { scanRoot: 'synthetic_root' });
  c.sandbox.listFolders('');
  const result = c.sandbox.loadLetter('ltr_one');
  assert.equal(c.counts().folderReads, 0); // Resolve only during deferred image requests.
  assert.equal(result.letter.scans[0].mapping_status, 'folder_lookup');
  assert.equal(bundle.letters[0].scans[0].mapping_status, 'missing_mapping');
  const answer = c.sandbox.loadImage({ token: result.token, letter_id: 'ltr_one', image_id: 'img_B' });
  assert.equal(answer.status, 'ready');
  assert.equal(answer.url, 'https://drive.google.com/file/d/resolved_drive_img_B/view');
  assert.match(answer.data, /^data:image\/jpeg;base64,/);
  assert.deepEqual(c.lookups, ['folder:folder', 'file:img_B.jpg']);
  assert.equal(c.counts().gateReads, 3); assert.equal(c.counts().imageReads, 1);
  const f = frontend(); f.sandbox.renderLetter(result);
  assert.equal(f.calls[0].req.image_id, 'img_B');
  f.calls[0].failure({ message: 'Synthetic error' });
  assert.equal(f.calls[1].req.image_id, 'img_A');
});

test('collection lookup supports root scans and nested folders with exact Unicode names', () => {
  for (const pathname of ['img_B.jpg', 'Shufeldt, Percy/Été/img_B.jpg']) {
    const bundle = unmappedFixture(); bundle.letters[0].scans[0].path = pathname;
    const leaf = { files: { 'img_B.jpg': ['resolved_drive_img_B'] } };
    const tree = pathname.includes('/') ? { folders: { 'Shufeldt, Percy': [{ folders: { 'Été': [leaf] } }] } } : leaf;
    const c = context(bundle, { scanRoot: 'synthetic_root', folderTree: tree });
    const token = c.sandbox.loadLetter('ltr_one').token;
    assert.equal(c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'img_B' }).status, 'ready');
    assert.deepEqual(c.lookups, pathname.includes('/') ? ['folder:Shufeldt, Percy', 'folder:Été', 'file:img_B.jpg'] : ['file:img_B.jpg']);
  }
});

test('collection lookup refuses unavailable or duplicate names without choosing a substitute', () => {
  const leaf = { files: { 'img_B.jpg': ['resolved_drive_img_B'] } };
  for (const [folderTree, expected] of [
    [{}, 'path_unavailable'], [{ folders: { folder: [{}] } }, 'path_unavailable'],
    [{ folders: { folder: [leaf, leaf] } }, 'ambiguous_path'],
    [{ folders: { folder: [{ files: { 'img_B.jpg': ['one', 'two'] } }] } }, 'ambiguous_path'],
    [{ trashed: true }, 'missing_scan'], [{ folders: { folder: [{ trashed: true }] } }, 'missing_scan']
  ]) {
    const c = context(unmappedFixture(), { scanRoot: 'synthetic_root', folderTree });
    const token = c.sandbox.loadLetter('ltr_one').token;
    assert.equal(c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'img_B' }).status, expected);
    assert.equal(c.counts().imageReads, 0);
  }
});

test('folder-resolved scans retain hash, type, size and per-account access checks', () => {
  for (const [options, expected] of [
    [{ folderError: true }, 'inaccessible'],
    [{ image: { getMimeType: () => 'application/pdf' } }, 'unavailable'],
    [{ image: { getSize: () => 13 * 1024 * 1024 } }, 'unavailable'],
    [{ image: { getBlob: () => ({ getBytes: () => [1, 2, 3] }) } }, 'changed'],
    [{ image: { getBlob: () => ({ getBytes: () => [...Buffer.alloc(bytes.length)] }) } }, 'changed'],
    [{ image: { isTrashed: () => true } }, 'missing_scan']
  ]) {
    const c = context(unmappedFixture(), { scanRoot: 'synthetic_root', ...options });
    const token = c.sandbox.loadLetter('ltr_one').token;
    const answer = c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'img_B' });
    assert.equal(answer.status, expected); assert.equal(answer.data, undefined);
  }
  const denied = context(unmappedFixture(), { scanRoot: 'synthetic_root', deny: true });
  assert.throws(() => denied.sandbox.loadImage({}), /Access denied/);
  assert.equal(denied.counts().folderReads, 0);
});

test('unsafe exported paths are rejected before any folder read', () => {
  for (const pathname of ['../img_B.jpg', '/folder/img_B.jpg', 'folder//img_B.jpg',
    'folder/./img_B.jpg', 'folder/../img_B.jpg', 'folder\\img_B.jpg', 'C:/img_B.jpg',
    'folder/\u0000img_B.jpg', 'x/'.repeat(33) + 'img_B.jpg', null]) {
    const bundle = unmappedFixture(); bundle.letters[0].scans[0].path = pathname;
    const c = context(bundle, { scanRoot: 'synthetic_root' }), token = c.sandbox.loadLetter('ltr_one').token;
    assert.equal(c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'img_B' }).status, 'invalid_path');
    assert.equal(c.counts().folderReads, 0);
  }
});

test('explicit mappings take priority and never fall back when the mapped scan is inaccessible', () => {
  for (const imageError of [false, true]) {
    const c = context(fixture(), { scanRoot: 'synthetic_root', imageError });
    const result = c.sandbox.loadLetter('ltr_one');
    assert.equal(result.letter.scans[0].mapping_status, 'mapped');
    assert.equal(c.sandbox.loadImage({ token: result.token, letter_id: 'ltr_one', image_id: 'img_B' }).status,
      imageError ? 'inaccessible' : 'ready');
    assert.equal(c.counts().folderReads, 0);
  }
});

test('folder lookup cannot bypass export pinning, page membership, inventory state or payload bounds', () => {
  const bundle = unmappedFixture(), c = context(bundle, { scanRoot: 'synthetic_root' });
  const token = c.sandbox.loadLetter('ltr_one').token;
  assert.equal(c.sandbox.loadImage({ token: 'old', letter_id: 'ltr_one', image_id: 'img_B' }).status, 'changed');
  assert.throws(() => c.sandbox.loadImage({ token, letter_id: 'ltr_one', image_id: 'other', path: 'img_B.jpg' }), /not part/);
  bundle.letters[0].scans[0].status = 'missing';
  const missingToken = c.sandbox.loadLetter('ltr_one').token;
  assert.equal(c.sandbox.loadImage({ token: missingToken, letter_id: 'ltr_one', image_id: 'img_B' }).status, 'missing_scan');
  bundle.letters[0].scans[0].status = 'ready'; bundle.letters[0].scans[0].size = 25 * 1024 * 1024;
  const oversizedToken = c.sandbox.loadLetter('ltr_one').token;
  assert.equal(c.sandbox.loadImage({ token: oversizedToken, letter_id: 'ltr_one', image_id: 'img_B' }).status, 'too_large');
  assert.equal(c.counts().folderReads, 0);
});

test('search bound clearly reports truncation', () => {
  const bundle = fixture(), sample = bundle.letters[0];
  bundle.letters = Array.from({ length: 102 }, (_, i) => ({ ...sample, letter_id: 'ltr_' + i }));
  const result = context(bundle).sandbox.searchLetters('');
  assert.equal(result.letters.length, 100);
  assert.equal(result.total, 102);
  assert.equal(result.limited, true);
});

class Element {
  constructor(tag) {
    this.tag = tag; this.children = []; this.textContent = ''; this.dataset = {}; this.attributes = {};
    this.events = {}; this.style = { setProperty(name, value) { this[name] = value; } };
  }
  appendChild(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  addEventListener(name, fn) { this.events[name] = fn; }
  setAttribute(name, value) { this.attributes[name] = value; }
}
function frontend(dataset = {}, initialError = '') {
  const ids = Object.fromEntries(['record', 'message', 'results', 'initial-error', 'query', 'search', 'catalogue', 'clear-search']
    .map(id => [id, new Element(id)]));
  ids['initial-error'].textContent = initialError;
  const body = new Element('body'); body.dataset = { url: 'https://script.google.com/synthetic/exec', ...dataset };
  const calls = [], catalogueCalls = [], letterCalls = [];
  const runner = {
    withSuccessHandler(fn) { this.success = fn; return this; },
    withFailureHandler(fn) { this.failure = fn; return this; },
    loadImage(req) { calls.push({ req, success: this.success, failure: this.failure }); },
    listFolders(query) { catalogueCalls.push({ query, success: this.success, failure: this.failure }); },
    loadLetter(id) { letterCalls.push({ id, success: this.success, failure: this.failure }); }
  };
  const sandbox = { document: { body, getElementById: id => ids[id], createElement: tag => new Element(tag) },
    google: { script: { run: runner } } };
  vm.createContext(sandbox);
  vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], sandbox);
  return { sandbox, ids, calls, catalogueCalls, letterCalls };
}
function allNodes(root) { return [root, ...root.children.flatMap(allNodes)]; }

function catalogueFixture() {
  const bundle = fixture(), sample = bundle.letters[0];
  function letter(id, folder, date, extra = {}) {
    return { ...sample, letter_id: id, hints: { folder }, metadata: { ...sample.metadata,
      date: { value: date, normalized: date, precision: date && ({ 4: 'year', 7: 'month', 10: 'day' })[date.length], certainty: 'explicit' } }, ...extra };
  }
  bundle.letters = [letter('late', 'A & B', '1900-01-01'), letter('other', 'Z', '1800'),
    letter('unknown', 'A & B', null), letter('early', 'A & B', '1899-05'),
    letter('hint', 'A & B', null, { metadata: {}, hints: { folder: 'A & B', date: '1898', sender: 'Hint sender' }, execution: 'unprocessed' }),
    letter('ambiguous', 'A & B', 'May 1, 99', { metadata: { date: { value: 'May 1, 99', normalized: '1899-05-01', precision: 'day', certainty: 'uncertain' } }, hints: { folder: 'A & B', date: '1700' } }),
    letter('same_date', 'A & B', '1900-01-01', { active: false })];
  return bundle;
}

test('folder catalogue includes all letters chronologically without loading scans', () => {
  const bundle = catalogueFixture(), c = context(bundle), result = c.sandbox.listFolders('');
  assert.deepEqual(Array.from(result.folders, f => f.name), ['A & B', 'Z']);
  assert.deepEqual(Array.from(result.folders[0].letters, l => l.letter_id), ['hint', 'early', 'late', 'same_date', 'ambiguous', 'unknown']);
  assert.equal(result.folders[0].letters[0].sort_basis, 'filename hint');
  assert.equal(result.folders[0].letters[1].sort_date, '1899-05');
  assert.equal(result.folders[0].letters[3].active, false);
  assert.equal(result.folders[0].letters[4].sort_basis, 'unknown');
  assert.equal(result.folders[0].letters[0].pages, undefined);
  assert.equal(c.counts().imageReads, 0);
  assert.equal(c.counts().gateReads, 1);
  assert.equal(bundle.letters[0].letter_id, 'late'); // Sorting cannot mutate the saved export.
  const sample = bundle.letters[0];
  bundle.letters = Array.from({ length: 125 }, (_, i) => ({ ...sample, letter_id: 'letter_' + i }));
  assert.equal(context(bundle).sandbox.listFolders('').folders[0].letters.length, 125);
});

test('folder search covers folders and saved text with no truncation, and root is explicit', () => {
  const c = context(catalogueFixture());
  assert.equal(c.sandbox.listFolders('a & b').total, 6);
  assert.equal(c.sandbox.listFolders('café').total, 7);
  assert.equal(c.sandbox.listFolders('missing phrase').folders.length, 0);
  assert.throws(() => c.sandbox.listFolders('x'.repeat(201)), /200 characters/);
  const bundle = fixture(); bundle.letters[0].scans = [];
  assert.equal(context(bundle).sandbox.listFolders('').folders[0].name, '.');
});

test('chronology rejects invalid and unsupported dates without overriding document evidence', () => {
  const { sandbox } = context();
  for (const date of ['1900-02-29', '1899-13', '0000', '1899-04-31']) {
    assert.equal(sandbox.chronology_({ hints: { date } }).sort_basis, 'unknown');
  }
  assert.equal(sandbox.chronology_({ hints: { date: '2000-02-29' } }).sort_date, '2000-02-29');
  for (const date of [
    { value: 'May 1, 99', normalized: '1899-05-01', precision: 'day', certainty: 'explicit' },
    { value: '1899', normalized: '1900', precision: 'year', certainty: 'inferred' },
    { value: '1899', normalized: '1899-01-01', precision: 'year', certainty: 'explicit' }
  ]) assert.equal(sandbox.chronology_({ metadata: { date }, hints: { date: '1700' } }).sort_basis, 'unknown');
});

test('previous and next follow the complete folder order and stop at its boundaries', () => {
  const { sandbox } = context(catalogueFixture());
  const middle = sandbox.loadLetter('early').navigation;
  assert.equal(middle.previous.letter_id, 'hint'); assert.equal(middle.next.letter_id, 'late');
  assert.equal(middle.position, 2); assert.equal(middle.total, 6);
  assert.equal(sandbox.loadLetter('hint').navigation.previous, null);
  assert.equal(sandbox.loadLetter('unknown').navigation.next, null);
  const single = sandbox.loadLetter('other').navigation;
  assert.equal(single.previous, null); assert.equal(single.next, null);
});

test('home loads collapsed folders automatically; search and return links expand matching folders', () => {
  const f = frontend(), result = context(catalogueFixture()).sandbox.listFolders('');
  assert.equal(f.catalogueCalls.length, 1); assert.equal(f.calls.length, 0);
  f.catalogueCalls[0].success(result);
  assert.equal(f.ids.results.children.length, 2);
  assert.ok(f.ids.results.children.every(n => n.tag === 'details' && !n.open));
  const text = allNodes(f.ids.results).map(n => n.textContent).join('\n');
  assert.match(text, /Hint sender/); assert.match(text, /Filename hint · unverified/); assert.match(text, /Retired record/);
  const returned = frontend({ folder: 'A & B' }); returned.catalogueCalls[0].success(result);
  assert.equal(returned.ids.results.children[0].open, true); assert.equal(returned.ids.results.children[1].open, false);
  f.sandbox.loadFolders('old'); f.sandbox.loadFolders('new');
  f.catalogueCalls[2].success({ total: 0, folders: [] }); f.catalogueCalls[1].success(result);
  assert.match(f.ids.results.children[0].textContent, /No letters match/); // Ignore a slow, older response.
  f.ids['clear-search'].events.click();
  assert.equal(f.ids.query.value, ''); assert.equal(f.catalogueCalls[3].query, '');
  const direct = frontend({ letter: 'early' });
  assert.equal(direct.catalogueCalls.length, 0); assert.equal(direct.letterCalls[0].id, 'early');
  assert.equal(frontend({}, 'Access denied').catalogueCalls.length, 0);
});

test('each scan is left of its own matched transcription; summary is above and metadata below all pages', () => {
  const bundle = fixture(), letter = bundle.letters[0];
  letter.pages.reverse(); // Match IDs, never zip independent arrays.
  letter.translations = [{ image_id: 'img_A', language: 'French', text: 'Translation A' }];
  letter.pages[1].annotations = [{ kind: 'marginal', text: 'Margin B' }];
  letter.metadata.place_written = { value: 'Synthetic place' };
  const f = frontend(); f.sandbox.renderLetter(context(bundle).sandbox.loadLetter('ltr_one'));
  const children = f.ids.record.children, pairs = children.filter(n => n.className === 'page-pair');
  assert.deepEqual(pairs.map(p => p.dataset.imageId), ['img_B', 'img_A']);
  for (const [i, pair] of pairs.entries()) {
    const columns = pair.children.find(n => n.className === 'page-columns');
    assert.equal(columns.children[0].tag, 'figure');
    const text = allNodes(columns.children[1]).map(n => n.textContent).join('\n');
    assert.match(text, i === 0 ? /0012/ : /\[blank\]/);
    assert.equal(text.includes('Translation A'), i === 1); assert.equal(text.includes('Margin B'), i === 0);
  }
  assert.ok(children.findIndex(n => n.className === 'letter-summary') < children.indexOf(pairs[0]));
  const metadata = children.find(n => n.className === 'panel');
  assert.ok(children.indexOf(metadata) > children.indexOf(pairs[1]));
  assert.match(allNodes(metadata).map(n => n.textContent).join('\n'), /Synthetic place/);
  assert.equal(f.ids.catalogue.hidden, true);
});

test('normalized names and ISO dates are consistent across catalogue, accessible links, heading and details', () => {
  const bundle = fixture(), letter = bundle.letters[0];
  letter.metadata.sender = { value: 'Alex. BENNETT', normalized: 'Alexandra Bennett', certainty: 'explicit', evidence: [] };
  letter.metadata.recipient = { value: 'Mr. C. Curator', normalized: 'Casey Curator', certainty: 'inferred', evidence: [] };
  letter.metadata.attributed_author = { value: 'A. Bennett', normalized: 'Alexandra Bennett', certainty: 'uncertain', evidence: [] };
  letter.metadata.date = { value: 'May 1st, 1899', normalized: '1899-05-01', precision: 'day', certainty: 'explicit', evidence: [] };
  const original = JSON.stringify(bundle), c = context(bundle), f = frontend();
  f.catalogueCalls[0].success(c.sandbox.listFolders(''));
  const catalogueNodes = allNodes(f.ids.results);
  assert.ok(catalogueNodes.some(n => n.textContent === 'Alexandra Bennett'));
  assert.ok(catalogueNodes.some(n => n.textContent === 'Casey Curator'));
  assert.ok(catalogueNodes.some(n => n.textContent === '1899-05-01'));
  assert.ok(!catalogueNodes.some(n => n.textContent === 'Alex. BENNETT' || n.textContent === 'May 1st, 1899'));
  assert.match(catalogueNodes.find(n => n.tag === 'a').attributes['aria-label'], /Alexandra Bennett to Casey Curator, 1899-05-01/);
  f.sandbox.renderLetter(c.sandbox.loadLetter('ltr_one'));
  const heading = f.ids.record.children.find(n => n.className === 'letter-heading');
  assert.ok(heading.children.some(n => n.tag === 'h2' && n.textContent === 'Alexandra Bennett → Casey Curator'));
  assert.ok(heading.children.some(n => n.textContent.startsWith('1899-05-01 ·')));
  const panel = f.ids.record.children.find(n => n.className === 'panel'), panelNodes = allNodes(panel);
  assert.equal(panelNodes.filter(n => n.tag === 'dd' && n.textContent === 'Alexandra Bennett').length, 2);
  assert.ok(panelNodes.some(n => n.tag === 'dd' && n.textContent === '1899-05-01'));
  assert.ok(panelNodes.some(n => n.tag === 'dt' && n.textContent === 'Date'));
  assert.ok(!panelNodes.some(n => n.textContent.startsWith('Normalized:')));
  assert.ok(panelNodes.some(n => n.textContent === 'Certainty: inferred'));
  assert.ok(panelNodes.some(n => n.textContent === 'Certainty: uncertain'));
  const evidence = f.ids.record.children.find(n => n.className === 'provenance');
  const preserved = JSON.parse(evidence.children.find(n => n.tag === 'pre').textContent);
  assert.equal(preserved.metadata.sender.value, 'Alex. BENNETT');
  assert.equal(preserved.metadata.date.value, 'May 1st, 1899');
  assert.equal(JSON.stringify(bundle), original);
  assert.equal(c.sandbox.searchLetters('Alex. BENNETT').total, 1);
  assert.equal(c.sandbox.searchLetters('Alexandra Bennett').total, 1);
});

test('display falls back to original readings and preserves partial dates and uncertainty', () => {
  const f = frontend();
  for (const normalized of [null, '', '   ', undefined]) {
    const letter = fixture().letters[0];
    letter.metadata.sender = { value: 'Original sender', normalized };
    letter.metadata.date = { value: 'May, year unclear', normalized, precision: 'ambiguous', certainty: 'uncertain' };
    f.sandbox.renderLetter({ letter, token: 't', links: [], unresolved: [], warnings: [] });
    const heading = f.ids.record.children.find(n => n.className === 'letter-heading');
    assert.ok(heading.children.some(n => n.textContent.startsWith('Original sender →')));
    assert.ok(heading.children.some(n => n.textContent.startsWith('May, year unclear ·')));
  }
  for (const [normalized, precision] of [['1899', 'year'], ['1899-05', 'month']]) {
    const letter = fixture().letters[0];
    letter.metadata.date = { value: precision === 'year' ? 'In 1899' : 'May 1899', normalized, precision, certainty: 'inferred' };
    f.sandbox.renderLetter({ letter, token: 't', links: [], unresolved: [], warnings: [] });
    const heading = f.ids.record.children.find(n => n.className === 'letter-heading');
    assert.ok(heading.children.some(n => n.textContent.startsWith(normalized + ' ·')));
    const text = allNodes(f.ids.record).map(n => n.textContent).join('\n');
    assert.match(text, /Certainty: inferred/);
    assert.ok(!text.includes(normalized + '-01'));
  }
  assert.equal(f.sandbox.value({}, 'sender'), 'Unknown');
});

test('normalized labels remain literal text and do not rewrite page text, folder names or other metadata readings', () => {
  const bundle = fixture(), letter = bundle.letters[0];
  const dangerous = '<img src=x onerror=bad()> & Émile';
  letter.metadata.sender = { value: 'Original sender', normalized: dangerous };
  letter.metadata.place_written = { value: 'Place as written', normalized: 'Search place' };
  const f = frontend(), c = context(bundle);
  f.catalogueCalls[0].success(c.sandbox.listFolders(''));
  assert.equal(f.ids.results.children[0].children[0].textContent, 'folder');
  f.sandbox.renderLetter(c.sandbox.loadLetter('ltr_one'));
  const nodes = allNodes(f.ids.record);
  assert.ok(nodes.some(n => n.tag === 'h2' && n.textContent === dangerous + ' → B'));
  assert.ok(nodes.some(n => n.tag === 'dd' && n.textContent === 'Place as written'));
  assert.ok(nodes.some(n => n.textContent === 'Normalized: Search place'));
  assert.ok(nodes.some(n => n.tag === 'pre' && n.textContent === letter.pages[0].text));
  assert.equal(nodes.filter(n => n.tag === 'img' || n.tag === 'script').length, 0);
});

test('both navigation bars link to adjacent letters and reopen the source folder', () => {
  const f = frontend(); f.sandbox.renderLetter(context(catalogueFixture()).sandbox.loadLetter('early'));
  const navs = f.ids.record.children.filter(n => n.tag === 'nav');
  assert.equal(navs.length, 2);
  for (const nav of navs) {
    const links = allNodes(nav).filter(n => n.tag === 'a');
    assert.match(links[0].href, /\?folder=A%20%26%20B$/);
    assert.match(links[1].href, /\?letter=hint$/); assert.match(links[2].href, /\?letter=late$/);
  }
  f.sandbox.renderLetter(context(catalogueFixture()).sandbox.loadLetter('other'));
  assert.equal(allNodes(f.ids.record).filter(n => n.attributes['aria-disabled'] === 'true').length, 4);
});

test('scan dimensions size the paired sheets and decode errors preserve text and source link', () => {
  const f = frontend(); f.sandbox.renderLetter(context().sandbox.loadLetter('ltr_one'));
  f.calls[0].success({ status: 'ready', data: 'data:image/jpeg;base64,test', url: 'https://drive.google.com/synthetic' });
  const pair = f.ids.record.children.find(n => n.className === 'page-pair');
  const image = allNodes(pair).find(n => n.tag === 'img');
  image.naturalWidth = 1600; image.naturalHeight = 900; image.onload();
  assert.equal(pair.style['--page-ratio'], '1600 / 900');
  image.onerror();
  assert.equal(image.hidden, true);
  assert.match(allNodes(pair).map(n => n.textContent).join('\n'), /Image bytes could not be displayed/);
  assert.match(allNodes(pair).map(n => n.textContent).join('\n'), /0012/);
  assert.ok(allNodes(pair).some(n => n.href === 'https://drive.google.com/synthetic'));
  assert.equal(f.calls[1].req.image_id, 'img_A');
});

test('missing transcription and unmatched saved text retain their own page slots', () => {
  const bundle = fixture(), letter = bundle.letters[0];
  letter.pages[1].image_id = 'orphan';
  letter.partial_response = 'Partial raw response';
  const f = frontend(); f.sandbox.renderLetter(context(bundle).sandbox.loadLetter('ltr_one'));
  const pairs = f.ids.record.children.filter(n => n.className === 'page-pair');
  assert.equal(pairs.length, 3);
  assert.match(allNodes(pairs[1]).map(n => n.textContent).join('\n'), /No complete transcription/);
  assert.match(allNodes(pairs[2]).map(n => n.textContent).join('\n'), /No source scan is listed/);
  assert.match(allNodes(pairs[2]).map(n => n.textContent).join('\n'), /\[blank\]/);
  assert.match(allNodes(f.ids.record).map(n => n.textContent).join('\n'), /Partial raw response/);
});

test('actual renderer treats historical HTML as literal text', () => {
  const f = frontend();
  f.sandbox.renderLetter({ letter: fixture().letters[0], token: 't', links: [], unresolved: [], warnings: [] });
  const nodes = allNodes(f.ids.record);
  assert.ok(nodes.some(n => n.textContent === '<img src=x onerror=bad()> & café\n0012'));
  assert.ok(nodes.some(n => n.textContent.includes('A <script>bad()</script>')));
  assert.equal(nodes.filter(n => n.tag === 'script').length, 0);
  assert.doesNotMatch(html, /innerHTML|document\.write|<\?!/);
});

test('actual renderer keeps ordered scan positions and text after image failure', () => {
  const f = frontend();
  f.sandbox.renderLetter({ letter: fixture().letters[0], token: 't', links: [], unresolved: [], warnings: [] });
  assert.equal(f.calls[0].req.image_id, 'img_B');
  f.calls[0].failure({ message: 'Synthetic inaccessible image' });
  assert.equal(f.calls[1].req.image_id, 'img_A');
  const nodes = allNodes(f.ids.record);
  assert.ok(nodes.some(n => n.textContent.includes('Synthetic inaccessible image')));
  assert.ok(nodes.some(n => n.textContent.includes('0012')));
});

test('relationship directions and candidate/confirmed/rejected labels are explicit', () => {
  const f = frontend();
  for (const status of ['candidate', 'confirmed', 'rejected']) {
    const outgoing = f.sandbox.relationshipLabel({ from_letter: 'one', to_letter: 'two', relation: 'reply_to', status }, 'one');
    assert.equal(outgoing.label, status.toUpperCase() + ': Replies to earlier letter');
    const incoming = f.sandbox.relationshipLabel({ from_letter: 'one', to_letter: 'two', relation: 'reply_to', status }, 'two');
    assert.match(incoming.label, /Later reply/);
  }
});

test('unresolved reference and absent transcription displayed separately', () => {
  const f = frontend(), letter = fixture().letters[0];
  letter.pages = []; letter.execution = 'unprocessed'; letter.scans[0].mapping_status = 'missing_mapping';
  f.sandbox.renderLetter({ letter, token: 't', links: [],
    unresolved: [{ reference: { description: 'Letter of 1898, scan unavailable' } }], warnings: [] });
  const text = allNodes(f.ids.record).map(n => n.textContent).join('\n');
  assert.match(text, /No complete transcription/);
  assert.match(text, /UNRESOLVED/);
  assert.match(text, /No Google Drive mapping/);
});

test('manifest permits read-only Drive and USER_ACCESSING only', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'appsscript.json'), 'utf8'));
  assert.deepEqual(manifest.oauthScopes, ['https://www.googleapis.com/auth/drive.readonly']);
  assert.equal(manifest.webapp.executeAs, 'USER_ACCESSING');
  assert.doesNotMatch(server, /setSharing|setTrashed|createFile|UrlFetchApp/);
});
