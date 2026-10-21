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
    order, status: 'ready', size: bytes.length, sha256: hash,
    drive_file_id: 'synthetic_drive_' + id, mapping_status: 'mapped' });
  return { schema_version: 1, letters: [{
    letter_id: 'ltr_one', active: true, execution: 'complete', grouping: 'provisional',
    metadata_review: 'unreviewed', transcription_review: 'unreviewed', relationship_review: 'unreviewed',
    review_reasons: [], metadata: { sender: { value: 'A <script>bad()</script>' },
      recipient: { value: 'B' }, date: { value: '1899-05-01' } },
    summary: 'Synthetic test', notes: [], partial_response: '',
    pages: [{ image_id: 'img_B', status: 'text', text: '<img src=x onerror=bad()> & café\n0012', annotations: [] },
      { image_id: 'img_A', status: 'blank', text: '[blank]', annotations: [] }],
    scans: [scan('img_B', 1), scan('img_A', 2)], provenance: { model: 'synthetic' }
  }], links: [], unresolved: [], warnings: [] };
}

function context(bundle = fixture(), options = {}) {
  let gateReads = 0, imageReads = 0;
  const blob = { getDataAsString: () => JSON.stringify(bundle), getBytes: () => [...bytes] };
  const file = { getName: () => 'synthetic', isTrashed: () => false, getId: () => 'export',
    getSize: () => JSON.stringify(bundle).length, getLastUpdated: () => new Date(1000),
    getBlob: () => blob };
  const image = { ...file, getSize: () => bytes.length, getMimeType: () => 'image/jpeg',
    getBlob: () => { imageReads++; return blob; } };
  const sandbox = {
    DriveApp: { getFileById(id) {
      if (id === 'gate') { gateReads++; if (options.deny) throw Error('denied'); return file; }
      if (id === 'export') return file;
      if (options.imageError) throw Error('hidden existence');
      return { ...image, ...options.image };
    } },
    Utilities: { DigestAlgorithm: { SHA_256: 'sha256' },
      computeDigest: (_, data) => [...crypto.createHash('sha256').update(Buffer.from(data)).digest()],
      base64Encode: data => Buffer.from(data).toString('base64') },
    console
  };
  vm.createContext(sandbox);
  vm.runInContext(server.replace("ACCESS_FILE_ID: ''", "ACCESS_FILE_ID: 'gate'")
    .replace("EXPORT_FILE_ID: ''", "EXPORT_FILE_ID: 'export'"), sandbox);
  return { sandbox, counts: () => ({ gateReads, imageReads }) };
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

test('search bound clearly reports truncation', () => {
  const bundle = fixture(), sample = bundle.letters[0];
  bundle.letters = Array.from({ length: 102 }, (_, i) => ({ ...sample, letter_id: 'ltr_' + i }));
  const result = context(bundle).sandbox.searchLetters('');
  assert.equal(result.letters.length, 100);
  assert.equal(result.total, 102);
  assert.equal(result.limited, true);
});

class Element {
  constructor(tag) { this.tag = tag; this.children = []; this.textContent = ''; this.dataset = {}; }
  appendChild(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  addEventListener() {}
}
function frontend() {
  const ids = Object.fromEntries(['record', 'message', 'results', 'initial-error', 'query', 'search']
    .map(id => [id, new Element(id)]));
  const body = new Element('body'); body.dataset.url = 'https://script.google.com/synthetic/exec';
  const calls = [];
  const runner = {
    withSuccessHandler(fn) { this.success = fn; return this; },
    withFailureHandler(fn) { this.failure = fn; return this; },
    loadImage(req) { calls.push({ req, success: this.success, failure: this.failure }); }
  };
  const sandbox = { document: { body, getElementById: id => ids[id], createElement: tag => new Element(tag) },
    google: { script: { run: runner } } };
  vm.createContext(sandbox);
  vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], sandbox);
  return { sandbox, ids, calls };
}
function allNodes(root) { return [root, ...root.children.flatMap(allNodes)]; }

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
