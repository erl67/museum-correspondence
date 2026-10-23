/** Read-only correspondence viewer. Configure IDs; never change sharing here. */
const SETTINGS = Object.freeze({
  PUBLIC_MODE: true, // Intentionally publish current letters; deploy as Me / Anyone.
  ACCESS_FILE_ID: '1dwIdqRS_urGeGyI-E9pUhMrh0AmSCnnP', // Used only in restricted USER_ACCESSING mode.
  EXPORT_FILE_ID: '1dwIdqRS_urGeGyI-E9pUhMrh0AmSCnnP', // Viewer JSON file supplied by the user.
  SCAN_ROOT_FOLDER_ID: '1AvEal1n0hiB_MCuDbplb0RmhCeGFi8L0', // Collection folder containing all scan subfolders.
  MAX_EXPORT_BYTES: 10 * 1024 * 1024,
  MAX_IMAGE_BYTES: 12 * 1024 * 1024,
  MAX_LETTER_IMAGE_BYTES: 24 * 1024 * 1024,
  PUBLIC_REQUESTS_PER_MINUTE: 120, // Shared by all visitors, including page opens.
  PUBLIC_IMAGES_PER_MINUTE: 60
});

// Best-effort load shedding, not visitor authentication or denial-of-service protection.
// Cache eviction can reset these counters. Never cache private letters or image bytes.
function publicBudget_(imageRequest) {
  const busy = 'Viewer is busy. Please wait a minute and reload.';
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(100)) throw new Error(busy);
  try {
    const cache = CacheService.getScriptCache();
    const key = 'public-viewer-v1:' + Math.floor(Date.now() / 60000);
    const counts = JSON.parse(cache.get(key) || '{"requests":0,"images":0}');
    if (counts.requests >= SETTINGS.PUBLIC_REQUESTS_PER_MINUTE ||
        (imageRequest && counts.images >= SETTINGS.PUBLIC_IMAGES_PER_MINUTE)) throw new Error(busy);
    counts.requests++;
    if (imageRequest) counts.images++;
    cache.put(key, JSON.stringify(counts), 70);
  } catch (error) {
    throw new Error(busy);
  } finally {
    lock.releaseLock();
  }
}

function gate_(imageRequest) {
  if (!SETTINGS.EXPORT_FILE_ID || (!SETTINGS.PUBLIC_MODE && !SETTINGS.ACCESS_FILE_ID)) {
    throw new Error('Viewer is not configured. Set the access-gate and export file IDs.');
  }
  if (SETTINGS.PUBLIC_MODE) {
    publicBudget_(imageRequest);
    return; // Owner's Drive access is not visitor authorization; publication is intentional.
  }
  try {
    const file = DriveApp.getFileById(SETTINGS.ACCESS_FILE_ID);
    if (file.isTrashed()) throw new Error('Removed');
    file.getName(); // Recheck under USER_ACCESSING on every page and RPC.
  } catch (error) {
    throw new Error('Access denied. Sign in with an account allowed to read the configured collection access file.');
  }
}

function bundle_(imageRequest) {
  gate_(imageRequest);
  let value, token;
  try {
    const file = DriveApp.getFileById(SETTINGS.EXPORT_FILE_ID);
    if (file.isTrashed() || file.getSize() > SETTINGS.MAX_EXPORT_BYTES) throw new Error('Unavailable');
    token = file.getId() + ':' + file.getLastUpdated().getTime() + ':' + file.getSize();
    if (SETTINGS.PUBLIC_MODE) token = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, token)
      .map(byte => ('0' + (byte & 255).toString(16)).slice(-2)).join('');
    value = JSON.parse(file.getBlob().getDataAsString('UTF-8'));
  } catch (error) {
    // Do not return Drive exceptions, file IDs, or malformed JSON excerpts to visitors.
    throw new Error('Viewer export is unavailable. The maintainer must check access, valid JSON and the 10 MiB limit.');
  }
  if (!value || value.schema_version !== 1 || !Array.isArray(value.letters) ||
      value.letters.some(letter => !letter || typeof letter.letter_id !== 'string' || !Array.isArray(letter.scans))) {
    throw new Error('Unsupported viewer export schema.');
  }
  if (new Set(value.letters.map(x => x.letter_id)).size !== value.letters.length) {
    throw new Error('Duplicate archival IDs in export.');
  }
  // Enforce on the server for every RPC, including guessed historical IDs/image requests.
  if (SETTINGS.PUBLIC_MODE) value.letters = value.letters.filter(letter => letter.active === true);
  return { value, token };
}

function publicScalars_(source, keys) {
  const result = {};
  for (const key of keys) {
    const value = (source || {})[key];
    if (value === null || ['string', 'number', 'boolean'].includes(typeof value)) result[key] = value;
  }
  return result;
}

function publicEvidence_(items) {
  return (items || []).map(item => publicScalars_(item, ['image_id', 'quote']));
}

function publicLetter_(letter) {
  // Explicit publication fields: new export fields must not become public by accident.
  const result = publicScalars_(letter, ['letter_id', 'active', 'execution', 'grouping',
    'metadata_review', 'transcription_review', 'relationship_review', 'summary']);
  result.hints = publicScalars_(letter.hints, ['sender', 'recipient', 'date', 'folder']);
  result.metadata = {};
  for (const name of ['sender', 'recipient', 'date', 'place_written', 'addresses', 'affiliations',
      'language', 'document_type', 'attributed_author', 'physical_hand']) {
    const field = (letter.metadata || {})[name];
    if (field) result.metadata[name] = { ...publicScalars_(field, ['value', 'normalized', 'certainty', 'precision']),
      evidence: publicEvidence_(field.evidence) };
  }
  result.catalogue_names = {};
  for (const name of ['sender', 'recipient', 'attributed_author']) {
    const label = (letter.catalogue_names || {})[name];
    if (label) result.catalogue_names[name] = publicScalars_(label, ['name', 'basis']);
  }
  if (chronology_(letter).sort_basis === 'catalogue confirmation') {
    result.catalogue_date = { ...publicScalars_(letter.catalogue_date, ['value', 'precision']), source: 'Staff confirmation' };
  }
  result.pages = (letter.pages || []).map(page => ({ ...publicScalars_(page, ['image_id', 'status', 'text']),
    annotations: (page.annotations || []).map(note => publicScalars_(note, ['kind', 'text'])) }));
  result.translations = (letter.translations || []).map(item => publicScalars_(item, ['image_id', 'language', 'text']));
  result.notes = (letter.notes || []).filter(note => typeof note === 'string');
  result.scans = letter.scans.map(scan => ({ ...publicScalars_(scan,
    ['image_id', 'filename', 'path', 'folder', 'order', 'status']),
    mapping_status: scan.drive_file_id ? 'mapped' : SETTINGS.SCAN_ROOT_FOLDER_ID ? 'folder_lookup' : 'missing_mapping' }));
  return result;
}

function publicConnections_(value, id) {
  const ids = new Set(value.letters.map(letter => letter.letter_id));
  return {
    links: (value.links || []).filter(link => ids.has(link.from_letter) && ids.has(link.to_letter) &&
      (link.from_letter === id || link.to_letter === id)).map(link => ({
        ...publicScalars_(link, ['from_letter', 'to_letter', 'relation', 'status', 'needs_rematch', 'decision_needs_review']),
        evidence: publicEvidence_(link.evidence),
        contradictions: (link.contradictions || []).filter(text => typeof text === 'string') })),
    unresolved: (value.unresolved || []).filter(ref => ref.from_letter === id).map(ref => ({
      from_letter: id, reference: publicScalars_(ref.reference, ['description']) })),
    warnings: []
  };
}

function doGet(e) {
  const page = HtmlService.createTemplateFromFile('Viewer');
  page.letterId = String((e && e.parameter && e.parameter.letter) || '').slice(0, 100);
  page.folder = String((e && e.parameter && e.parameter.folder) || '').slice(0, 2000);
  page.appUrl = ScriptApp.getService().getUrl();
  page.error = '';
  try { gate_(); } catch (error) { page.error = error.message; }
  return page.evaluate().setTitle('Museum correspondence')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function matchingLetters_(letters, query) {
  const q = String(query || '').trim().toLocaleLowerCase();
  if (q.length > 200) throw new Error('Search is limited to 200 characters.');
  return letters.filter(source => {
    const letter = SETTINGS.PUBLIC_MODE ? publicLetter_(source) : source;
    const meta = letter.metadata || {};
    const text = [letter.letter_id, JSON.stringify(letter.hints || {}), JSON.stringify(letter.catalogue_names || {}), ...['sender', 'recipient', 'date'].map(k =>
      JSON.stringify(meta[k] || {})), ...(letter.pages || []).map(p =>
      p.text + ' ' + (p.annotations || []).map(a => a.text).join(' ')),
      folderOf_(letter), letter.partial_response || ''].join(' ');
    return text.toLocaleLowerCase().includes(q);
  });
}

function folderOf_(letter) {
  return (letter.hints && letter.hints.folder) ||
    (letter.scans && letter.scans[0] && letter.scans[0].folder) || '.';
}

function calendarDate_(input) {
  const match = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(String(input || ''));
  if (!match) return '';
  const year = Number(match[1]), month = Number(match[2] || 1), day = Number(match[3] || 1);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return year > 0 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1] ? match[0] : '';
}

function chronology_(letter) {
  const date = (letter.metadata || {}).date || {};
  // Match the export's conservative date policy; never expand ambiguous years.
  const normalized = calendarDate_(date.normalized);
  const lengths = { year: 4, month: 7, day: 10 };
  const confirmed = letter.catalogue_date;
  if (confirmed && confirmed.source && confirmed.review_event && normalized &&
      confirmed.value === normalized && confirmed.precision === date.precision &&
      normalized.length === lengths[date.precision]) {
    return { sort_date: normalized, sort_basis: 'catalogue confirmation' };
  }
  if (normalized && normalized.length === lengths[date.precision] &&
      ['explicit', 'inferred'].includes(date.certainty) &&
      (String(date.value || '').match(/\b\d{4}\b/g) || []).includes(normalized.slice(0, 4))) {
    return { sort_date: normalized, sort_basis: 'document' };
  }
  // Filename dates are provisional, and cannot override an ambiguous document date.
  const hint = !date.value && !date.normalized && calendarDate_((letter.hints || {}).date);
  return { sort_date: hint || '', sort_basis: hint ? 'filename hint' : 'unknown' };
}

function compareLetters_(a, b) {
  return (chronology_(a).sort_date || '99999').localeCompare(chronology_(b).sort_date || '99999') ||
    a.letter_id.localeCompare(b.letter_id);
}

function letterRow_(letter) {
  const display = SETTINGS.PUBLIC_MODE ? publicLetter_(letter) : letter;
  return { letter_id: letter.letter_id, metadata: display.metadata, hints: display.hints,
    catalogue_names: display.catalogue_names, catalogue_date: display.catalogue_date,
    execution: letter.execution, active: letter.active, page_count: (letter.scans || []).length,
    ...chronology_(letter) };
}

function searchLetters(query) {
  const { value } = bundle_();
  const matches = matchingLetters_(value.letters.filter(letter => letter.active !== false), query).sort(compareLetters_);
  return { total: matches.length, limited: matches.length > 100,
    letters: matches.slice(0, 100).map(letterRow_) };
}

function listFolders(query) {
  const { value } = bundle_();
  const matches = matchingLetters_(value.letters.filter(letter => letter.active !== false), query);
  const folders = new Map();
  for (const letter of matches) {
    const name = folderOf_(letter);
    if (!folders.has(name)) folders.set(name, []);
    folders.get(name).push(letter);
  }
  // Retired groupings remain accessible by ID only in restricted reader mode.
  // Only lightweight metadata is sent; page text and images load on the letter view.
  return { total: matches.length, folders: [...folders.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, letters]) => ({ name, letters: letters.sort(compareLetters_).map(letterRow_) })) };
}

function selectLetter_(value, id) {
  const letter = value.letters.find(item => item.letter_id === id);
  if (!letter) throw new Error('Letter is absent from this export.');
  return letter;
}

function loadLetter(id) {
  const { value, token } = bundle_();
  const letter = selectLetter_(value, String(id));
  const folder = folderOf_(letter);
  const siblings = value.letters.filter(item => item.active !== false && folderOf_(item) === folder).sort(compareLetters_);
  const index = siblings.findIndex(item => item.letter_id === letter.letter_id);
  const displayLetter = SETTINGS.PUBLIC_MODE ? publicLetter_(letter) : { ...letter, scans: letter.scans.map(scan => ({ ...scan,
    mapping_status: !scan.drive_file_id && SETTINGS.SCAN_ROOT_FOLDER_ID ? 'folder_lookup' : scan.mapping_status })) };
  const currentScanLetters = letter.active === false ? value.letters.filter(item => item.active !== false &&
    item.scans.some(scan => letter.scans.some(old => old.image_id === scan.image_id))).map(letterRow_) : [];
  const connections = SETTINGS.PUBLIC_MODE ? publicConnections_(value, id) : {
    links: value.links.filter(link => link.from_letter === id || link.to_letter === id),
    unresolved: value.unresolved.filter(ref => ref.from_letter === id), warnings: value.warnings || [] };
  return { letter: displayLetter, token, currentScanLetters, publicMode: SETTINGS.PUBLIC_MODE,
    navigation: { folder, position: index + 1, total: siblings.length,
      previous: index > 0 ? letterRow_(siblings[index - 1]) : null,
      next: index >= 0 && index + 1 < siblings.length ? letterRow_(siblings[index + 1]) : null },
    ...connections };
}

function singleDriveChild_(iterator, path) {
  if (!iterator.hasNext()) return { status: 'path_unavailable',
    message: 'Scan path is not visible to this account in the collection folder: ' + path +
      '. Check the collection folder, exact names and access permissions.' };
  const item = iterator.next();
  if (iterator.hasNext()) return { status: 'ambiguous_path',
    message: 'More than one Drive item matches: ' + path + '. Supply an explicit image mapping to select the original.' };
  if (item.isTrashed()) return { status: 'missing_scan', message: 'An item in the scan path is in Trash: ' + path };
  return { item };
}

function scanByPath_(scan) {
  const path = scan.path;
  if (typeof path !== 'string' || path.length > 4096 || /[\\\u0000-\u001f]/.test(path) || /^[A-Za-z]:/.test(path)) {
    return { status: 'invalid_path', message: 'Exported scan path must be relative to the collection folder.' };
  }
  const parts = path.split('/');
  if (parts.length > 32 || parts.some(part => !part || part === '.' || part === '..')) {
    return { status: 'invalid_path', message: 'Exported scan path must be relative to the collection folder.' };
  }
  let folder = DriveApp.getFolderById(SETTINGS.SCAN_ROOT_FOLDER_ID);
  if (folder.isTrashed()) return { status: 'missing_scan', message: 'Configured collection folder is in Trash.' };
  for (const name of parts.slice(0, -1)) {
    const selected = singleDriveChild_(folder.getFoldersByName(name), path);
    if (!selected.item) return selected;
    folder = selected.item;
  }
  const selected = singleDriveChild_(folder.getFilesByName(parts[parts.length - 1]), path);
  return selected.item ? { file: selected.item } : selected;
}

function loadImage(request) {
  const { value, token } = bundle_(true);
  if (!request || typeof request !== 'object') throw new Error('Invalid image request.');
  if (token !== request.token) return { status: 'changed', message: 'Export changed; reload this letter.' };
  const letter = selectLetter_(value, request.letter_id);
  const scan = letter.scans.find(image => image.image_id === request.image_id);
  if (!scan) throw new Error('Image is not part of this letter.');
  if (scan.status === 'missing') return { status: 'missing_scan', message: 'Scan missing from the local inventory.' };
  if (scan.status !== 'ready') return { status: 'unavailable', message: 'Inventory scan state: ' + scan.status };
  if (!scan.drive_file_id && !SETTINGS.SCAN_ROOT_FOLDER_ID) {
    return { status: 'missing_mapping', message: 'No Google Drive mapping supplied. Set the collection scan folder or provide an image mapping.' };
  }
  if (scan.drive_file_id && !/^[A-Za-z0-9_-]{10,}$/.test(scan.drive_file_id)) throw new Error('Invalid Drive mapping.');
  if (!scan.drive_file_id && !/^[A-Za-z0-9_-]{10,}$/.test(SETTINGS.SCAN_ROOT_FOLDER_ID)) throw new Error('Invalid collection folder ID.');
  const planned = letter.scans.reduce((n, item) => n + (item.size || 0), 0);
  if (planned > SETTINGS.MAX_LETTER_IMAGE_BYTES || scan.size > SETTINGS.MAX_IMAGE_BYTES) {
    return { status: 'too_large', message: 'Scan display limit reached; use the original Drive file.' };
  }
  let file;
  try {
    if (scan.drive_file_id) file = DriveApp.getFileById(scan.drive_file_id);
    else {
      const resolved = scanByPath_(scan);
      if (!resolved.file) return resolved;
      file = resolved.file;
    }
    if (file.isTrashed()) return { status: 'missing_scan', message: 'Drive scan is in Trash.' };
    if (file.getSize() > SETTINGS.MAX_IMAGE_BYTES || file.getMimeType() !== 'image/jpeg') {
      return { status: 'unavailable', message: 'Drive file is too large or is not JPEG.' };
    }
    const bytes = file.getBlob().getBytes();
    if (bytes.length !== scan.size) return { status: 'changed', message: 'Drive scan size differs from the export; review the scan path or mapping.' };
    const sha = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, bytes)
      .map(byte => ('0' + (byte & 255).toString(16)).slice(-2)).join('');
    if (sha !== scan.sha256) return { status: 'changed', message: 'Drive scan hash differs from the export; review the scan path or mapping.' };
    return { status: 'ready', data: 'data:image/jpeg;base64,' + Utilities.base64Encode(bytes),
      url: SETTINGS.PUBLIC_MODE ? '' : 'https://drive.google.com/file/d/' + encodeURIComponent(file.getId()) + '/view' };
  } catch (error) {
    // Drive deliberately hides whether an inaccessible ID exists. Do not claim deletion.
    return { status: 'inaccessible', message: 'Drive scan or its collection folder cannot be read by this account. It may have been removed; Drive does not distinguish these cases.' };
  }
}
