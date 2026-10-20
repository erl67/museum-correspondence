/** Read-only correspondence viewer. Configure IDs; never change sharing here. */
const SETTINGS = Object.freeze({
  ACCESS_FILE_ID: '', // Existing institutional access-gate file; do not copy unrelated IDs.
  EXPORT_FILE_ID: '', // Explicitly uploaded viewer.json, shared under existing access rules.
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
  page.appUrl = ScriptApp.getService().getUrl();
  page.error = '';
  try { gate_(); } catch (error) { page.error = error.message; }
  return page.evaluate().setTitle('Museum correspondence')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function searchLetters(query) {
  const { value } = bundle_();
  const q = String(query || '').trim().toLocaleLowerCase();
  if (q.length > 200) throw new Error('Search is limited to 200 characters.');
  const matches = value.letters.filter(letter => {
    const meta = letter.metadata || {};
    const text = [letter.letter_id, JSON.stringify(letter.hints || {}), ...['sender', 'recipient', 'date'].map(k =>
      JSON.stringify(meta[k] || {})), ...(letter.pages || []).map(p =>
      p.text + ' ' + p.annotations.map(a => a.text).join(' ')), letter.partial_response || ''].join(' ');
    return text.toLocaleLowerCase().includes(q);
  });
  return { total: matches.length, limited: matches.length > 100,
    letters: matches.slice(0, 100).map(letter => ({ letter_id: letter.letter_id,
      metadata: letter.metadata, hints: letter.hints, execution: letter.execution, active: letter.active })) };
}

function selectLetter_(value, id) {
  const letter = value.letters.find(item => item.letter_id === id);
  if (!letter) throw new Error('Letter is absent from this export.');
  return letter;
}

function loadLetter(id) {
  const { value, token } = bundle_();
  const letter = selectLetter_(value, String(id));
  return { letter, token,
    links: value.links.filter(link => link.from_letter === id || link.to_letter === id),
    unresolved: value.unresolved.filter(ref => ref.from_letter === id),
    warnings: value.warnings || [] };
}

function loadImage(request) {
  const { value, token } = bundle_();
  if (token !== request.token) return { status: 'changed', message: 'Export changed; reload this letter.' };
  const letter = selectLetter_(value, request.letter_id);
  const scan = letter.scans.find(image => image.image_id === request.image_id);
  if (!scan) throw new Error('Image is not part of this letter.');
  if (scan.status === 'missing') return { status: 'missing_scan', message: 'Scan missing from the local inventory.' };
  if (scan.status !== 'ready') return { status: 'unavailable', message: 'Inventory scan state: ' + scan.status };
  if (!scan.drive_file_id) return { status: 'missing_mapping', message: 'No Google Drive mapping supplied.' };
  if (!/^[A-Za-z0-9_-]{10,}$/.test(scan.drive_file_id)) throw new Error('Invalid Drive mapping.');
  const planned = letter.scans.reduce((n, item) => n + (item.size || 0), 0);
  if (planned > SETTINGS.MAX_LETTER_IMAGE_BYTES || scan.size > SETTINGS.MAX_IMAGE_BYTES) {
    return { status: 'too_large', message: 'Scan display limit reached; use the original Drive file.' };
  }
  let file;
  try {
    file = DriveApp.getFileById(scan.drive_file_id);
    if (file.isTrashed()) return { status: 'missing_scan', message: 'Mapped Drive scan is in Trash.' };
    if (file.getSize() > SETTINGS.MAX_IMAGE_BYTES || file.getMimeType() !== 'image/jpeg') {
      return { status: 'unavailable', message: 'Mapped file is too large or is not JPEG.' };
    }
    const bytes = file.getBlob().getBytes();
    if (bytes.length !== scan.size) return { status: 'changed', message: 'Mapped scan size changed; review mapping.' };
    const sha = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, bytes)
      .map(byte => ('0' + (byte & 255).toString(16)).slice(-2)).join('');
    if (sha !== scan.sha256) return { status: 'changed', message: 'Mapped scan hash differs; review mapping.' };
    return { status: 'ready', data: 'data:image/jpeg;base64,' + Utilities.base64Encode(bytes),
      url: 'https://drive.google.com/file/d/' + encodeURIComponent(scan.drive_file_id) + '/view' };
  } catch (error) {
    // Drive deliberately hides whether an inaccessible ID exists. Do not claim deletion.
    return { status: 'inaccessible', message: 'Drive scan cannot be read by this account. It may have been removed; Drive does not distinguish these cases.' };
  }
}
