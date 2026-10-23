/** Read-only correspondence viewer. Configure IDs; never change sharing here. */
const SETTINGS = Object.freeze({
  ACCESS_FILE_ID: '1dwIdqRS_urGeGyI-E9pUhMrh0AmSCnnP', // Reader must have access to the viewer JSON file.
  EXPORT_FILE_ID: '1dwIdqRS_urGeGyI-E9pUhMrh0AmSCnnP', // Viewer JSON file supplied by the user.
  SCAN_ROOT_FOLDER_ID: '1AvEal1n0hiB_MCuDbplb0RmhCeGFi8L0', // Collection folder containing all scan subfolders.
  MAX_EXPORT_BYTES: 10 * 1024 * 1024,
  MAX_IMAGE_BYTES: 12 * 1024 * 1024,
  MAX_LETTER_IMAGE_BYTES: 24 * 1024 * 1024
});

function gate_() {
  if (!SETTINGS.ACCESS_FILE_ID || !SETTINGS.EXPORT_FILE_ID) {
    throw new Error('Viewer is not configured. Set the access-gate and export file IDs.');
  }
  try {
    const file = DriveApp.getFileById(SETTINGS.ACCESS_FILE_ID);
    if (file.isTrashed()) throw new Error('Removed');
    file.getName(); // Recheck under USER_ACCESSING on every page and RPC.
  } catch (error) {
    throw new Error('Access denied. Sign in with an account allowed to read the configured collection access file.');
  }
}

function bundle_() {
  gate_();
  const file = DriveApp.getFileById(SETTINGS.EXPORT_FILE_ID);
  if (file.isTrashed() || file.getSize() > SETTINGS.MAX_EXPORT_BYTES) {
    throw new Error('Viewer export is removed or exceeds the 10 MiB limit.');
  }
  const token = file.getId() + ':' + file.getLastUpdated().getTime() + ':' + file.getSize();
  const value = JSON.parse(file.getBlob().getDataAsString('UTF-8'));
  if (value.schema_version !== 1 || !Array.isArray(value.letters)) {
    throw new Error('Unsupported viewer export schema.');
  }
  if (new Set(value.letters.map(x => x.letter_id)).size !== value.letters.length) {
    throw new Error('Duplicate archival IDs in export.');
  }
  return { value, token };
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
  return letters.filter(letter => {
    const meta = letter.metadata || {};
    const text = [letter.letter_id, JSON.stringify(letter.hints || {}), ...['sender', 'recipient', 'date'].map(k =>
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
  return { letter_id: letter.letter_id, metadata: letter.metadata, hints: letter.hints,
    execution: letter.execution, active: letter.active, page_count: (letter.scans || []).length,
    ...chronology_(letter) };
}

function searchLetters(query) {
  const { value } = bundle_();
  const matches = matchingLetters_(value.letters, query).sort(compareLetters_);
  return { total: matches.length, limited: matches.length > 100,
    letters: matches.slice(0, 100).map(letterRow_) };
}

function listFolders(query) {
  const { value } = bundle_();
  const matches = matchingLetters_(value.letters, query);
  const folders = new Map();
  for (const letter of matches) {
    const name = folderOf_(letter);
    if (!folders.has(name)) folders.set(name, []);
    folders.get(name).push(letter);
  }
  // The catalogue returns every row, including unprocessed and retired records.
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
  const siblings = value.letters.filter(item => folderOf_(item) === folder).sort(compareLetters_);
  const index = siblings.findIndex(item => item.letter_id === letter.letter_id);
  const displayLetter = { ...letter, scans: letter.scans.map(scan => ({ ...scan,
    mapping_status: !scan.drive_file_id && SETTINGS.SCAN_ROOT_FOLDER_ID ? 'folder_lookup' : scan.mapping_status })) };
  return { letter: displayLetter, token,
    navigation: { folder, position: index + 1, total: siblings.length,
      previous: index > 0 ? letterRow_(siblings[index - 1]) : null,
      next: index + 1 < siblings.length ? letterRow_(siblings[index + 1]) : null },
    links: value.links.filter(link => link.from_letter === id || link.to_letter === id),
    unresolved: value.unresolved.filter(ref => ref.from_letter === id),
    warnings: value.warnings || [] };
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
  const { value, token } = bundle_();
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
      url: 'https://drive.google.com/file/d/' + encodeURIComponent(file.getId()) + '/view' };
  } catch (error) {
    // Drive deliberately hides whether an inaccessible ID exists. Do not claim deletion.
    return { status: 'inaccessible', message: 'Drive scan or its collection folder cannot be read by this account. It may have been removed; Drive does not distinguish these cases.' };
  }
}
