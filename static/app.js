// ─── State ──────────────────────────────────────────────────────────────────
let currentSkip = 0;
let currentTotal = 0;
let currentResults = [];
let bulkSource = null;
let activePdfPath = null;
let libSearchTimer = null;

const PAGE_SIZE = 10;

// ─── Tab routing ─────────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
    if (tab.dataset.tab === 'library') loadLibrary();
  });
});

// ─── Boot ────────────────────────────────────────────────────────────────────
async function boot() {
  try {
    const data = await apiFetch('/api/filters');
    populateSelect('s-committee', data.committees);
    populateSelect('s-appraiser', data.appraisers);
    populateSelect('s-version', data.versions);
    populateSelect('b-committee', data.committees);
    populateSelect('b-appraiser', data.appraisers);
    populateSelect('b-version', data.versions);
  } catch (e) {
    console.error('Failed to load filters:', e);
  }
}

function populateSelect(id, items) {
  const sel = document.getElementById(id);
  (items || []).forEach(item => {
    const opt = document.createElement('option');
    opt.value = item;
    opt.textContent = item;
    sel.appendChild(opt);
  });
}

// ─── Search tab ──────────────────────────────────────────────────────────────
async function doSearch(skip) {
  currentSkip = skip;
  const params = new URLSearchParams({ skip });
  const add = (k, id) => { const v = document.getElementById(id)?.value; if (v) params.set(k, v); };
  add('Committee', 's-committee');
  add('DecisiveAppraiser', 's-appraiser');
  add('AppraisalVersion', 's-version');
  add('Block', 's-block');
  add('Plot', 's-plot');
  add('DateFrom', 's-from');
  add('DateTo', 's-to');
  add('PubDateFrom', 's-pub-from');
  add('PubDateTo', 's-pub-to');
  add('FreeText', 's-text');

  try {
    const data = await apiFetch('/api/search?' + params.toString());
    currentTotal = data.TotalResults || 0;
    currentResults = data.Results || [];

    document.getElementById('s-count').textContent =
      currentTotal.toLocaleString('he-IL') + ' תוצאות';

    renderSearchResults(currentResults);
    renderPagination(skip, currentTotal);
  } catch (e) {
    document.getElementById('s-count').textContent = 'שגיאה בחיפוש';
    console.error('Search failed:', e);
  }
}

function renderSearchResults(results) {
  const tbody = document.getElementById('s-results');
  tbody.innerHTML = '';
  results.forEach(item => {
    const d = item.Data;
    const date = (d.DecisionDate || '').slice(0, 10);
    const isOriginal = (d.AppraisalVersion || '').includes('מקורית');
    const badgeClass = isOriginal ? 'badge-original' : 'badge-revised';
    const badgeText = isOriginal ? 'מקורית' : 'מתוקנת';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${esc(d.AppraisalHeader || '')}</td>
      <td style="color:var(--muted)">${esc(d.DecisiveAppraiser || '')}</td>
      <td style="color:var(--muted)">${esc(d.Committee || '')}</td>
      <td style="color:var(--muted)">${date}</td>
      <td><span class="badge ${badgeClass}">${badgeText}</span></td>
      <td class="actions-cell"></td>
    `;

    const actionsCell = tr.querySelector('.actions-cell');

    const dlLink = document.createElement('a');
    dlLink.className = 'action-link';
    dlLink.textContent = '↓ PDF';
    dlLink.addEventListener('click', () => downloadOne(d));

    const claudeLink = document.createElement('a');
    claudeLink.className = 'action-link purple';
    claudeLink.textContent = 'Claude ✦';
    claudeLink.addEventListener('click', () => analyzeFromSearch(d));

    actionsCell.appendChild(dlLink);
    actionsCell.appendChild(claudeLink);

    tbody.appendChild(tr);
  });
}

function renderPagination(skip, total) {
  const container = document.getElementById('s-pagination');
  container.innerHTML = '';
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(skip / PAGE_SIZE);
  if (totalPages <= 1) return;

  const maxPages = 5;
  const start = Math.max(0, currentPage - 2);
  const end = Math.min(totalPages - 1, start + maxPages - 1);

  if (currentPage > 0) addPageBtn(container, currentPage - 1, '◀ הקודם');
  for (let i = start; i <= end; i++) addPageBtn(container, i, String(i + 1), i === currentPage);
  if (currentPage < totalPages - 1) addPageBtn(container, currentPage + 1, 'הבא ▶');
}

function addPageBtn(container, page, label, active = false) {
  const btn = document.createElement('div');
  btn.className = 'page-btn' + (active ? ' active' : '');
  btn.textContent = label;
  btn.onclick = () => doSearch(page * PAGE_SIZE);
  container.appendChild(btn);
}

async function downloadOne(data) {
  try {
    const res = await apiFetch('/api/download', { method: 'POST', body: JSON.stringify({ data }) });
    alert(res.status === 'exists' ? 'הקובץ כבר קיים: ' + res.path : 'הורד: ' + res.path);
  } catch (e) {
    alert('שגיאה בהורדה: ' + e.message);
  }
}

async function downloadPage() {
  let downloaded = 0, existed = 0, errors = 0;
  for (const item of currentResults) {
    try {
      const res = await apiFetch('/api/download', { method: 'POST', body: JSON.stringify({ data: item.Data }) });
      if (res.status === 'exists') existed++;
      else downloaded++;
    } catch {
      errors++;
    }
  }
  const parts = [];
  if (downloaded) parts.push(`הורדו ${downloaded}`);
  if (existed) parts.push(`${existed} קיימים`);
  if (errors) parts.push(`${errors} שגיאות`);
  alert(parts.join(' • ') || 'לא היו קבצים להורדה');
}

async function analyzeFromSearch(data) {
  try {
    const res = await apiFetch('/api/download', { method: 'POST', body: JSON.stringify({ data }) });
    // Switch to library tab
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.querySelector('[data-tab="library"]').classList.add('active');
    document.getElementById('panel-library').classList.add('active');
    await loadLibrary();
    // Only open Claude panel if file already had OCR done (status === 'exists')
    // For newly downloaded files, user sees library and needs to run OCR first
    if (res.status === 'exists') {
      openClaudePanel(res.path, data.AppraisalHeader || res.path);
    }
  } catch (e) {
    alert('שגיאה: ' + e.message);
  }
}

// ─── Bulk tab ────────────────────────────────────────────────────────────────
function startBulk() {
  const params = new URLSearchParams({
    max_results: document.getElementById('b-max').value || '100',
    auto_ocr: document.getElementById('b-ocr').checked ? 'true' : 'false',
    skip_existing: document.getElementById('b-skip').checked ? 'true' : 'false',
  });
  const add = (k, id) => { const v = document.getElementById(id)?.value; if (v) params.set(k, v); };
  add('Committee', 'b-committee');
  add('DecisiveAppraiser', 'b-appraiser');
  add('AppraisalVersion', 'b-version');
  add('FreeText', 'b-text');
  add('DateFrom', 'b-from');
  add('DateTo', 'b-to');
  add('PubDateFrom', 'b-pub-from');
  add('PubDateTo', 'b-pub-to');

  document.getElementById('btn-bulk-start').classList.add('hidden');
  document.getElementById('btn-bulk-stop').classList.remove('hidden');
  document.getElementById('b-log').innerHTML = '';

  const maxResults = parseInt(params.get('max_results'));
  let downloaded = 0, errors = 0;

  bulkSource = new EventSource('/api/bulk?' + params.toString());

  bulkSource.onmessage = (e) => {
    const msg = JSON.parse(e.data);

    if (msg.status === 'done') {
      stopBulk();
      addLog(`✓ הסתיים — ${msg.downloaded} הורדו, ${msg.errors} שגיאות`, 'ok');
      return;
    }

    if (msg.downloaded !== undefined) downloaded = msg.downloaded;
    if (msg.errors !== undefined) errors = msg.errors;

    const pct = maxResults > 0 ? Math.round((downloaded / maxResults) * 100) : 0;
    document.getElementById('b-bar').style.width = pct + '%';
    document.getElementById('b-pct').textContent = `${downloaded} / ${maxResults} • ${pct}%`;
    document.getElementById('b-dl').textContent = downloaded;
    document.getElementById('b-err').textContent = errors;
    document.getElementById('b-rem').textContent = maxResults - downloaded;

    const cls = { ok: 'ok', error: 'err', downloading: 'downloading', skip: 'skip' }[msg.status] || '';
    const prefix = { ok: '✓', error: '⚠', downloading: '⟳', skip: '—' }[msg.status] || '';
    addLog(`${prefix} ${msg.name}${msg.error ? ' — ' + msg.error : ''}`, cls);
  };

  bulkSource.onerror = () => {
    stopBulk();
    addLog('⚠ חיבור ל-server נותק', 'err');
  };
}

function stopBulk() {
  if (bulkSource) { bulkSource.close(); bulkSource = null; }
  document.getElementById('btn-bulk-start').classList.remove('hidden');
  document.getElementById('btn-bulk-stop').classList.add('hidden');
}

function addLog(text, cls) {
  const log = document.getElementById('b-log');
  const line = document.createElement('div');
  line.className = cls ? 'log-' + cls : '';
  line.textContent = text;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

// ─── Library tab ─────────────────────────────────────────────────────────────
async function loadLibrary(query = '', committee = '', appraiser = '') {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (committee) params.set('committee', committee);
  if (appraiser) params.set('appraiser', appraiser);

  const data = await apiFetch('/api/library?' + params.toString());
  const results = data.results || [];

  document.getElementById('lib-stats').textContent =
    results.length.toLocaleString('he-IL') + ' קבצים';

  const tbody = document.getElementById('lib-results');
  tbody.innerHTML = '';

  results.forEach(row => {
    const ocrStatus = row.ocr_status;
    const ocrHtml = ocrStatus === 'done'
      ? '<span class="ocr-status-done">✓ OCR</span>'
      : ocrStatus === 'pending'
      ? '<span class="ocr-status-pending">⟳ ממתין</span>'
      : '<span class="ocr-status-none">—</span>';

    const date = (row.decision_date || '').slice(0, 10);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${esc(row.filename || '')}</td>
      <td style="color:var(--muted)">${esc(row.committee || '')}</td>
      <td style="color:var(--muted)">${esc(row.appraiser || '')}</td>
      <td style="color:var(--muted)">${date}</td>
      <td>${ocrHtml}</td>
      <td class="actions-cell"></td>
    `;

    const actionsCell = tr.querySelector('.actions-cell');

    const openLink = document.createElement('a');
    openLink.className = 'action-link';
    openLink.textContent = 'פתח';
    openLink.addEventListener('click', () => openFile(row.local_path));
    actionsCell.appendChild(openLink);

    if (ocrStatus === 'done') {
      const claudeLink = document.createElement('a');
      claudeLink.className = 'action-link purple';
      claudeLink.textContent = 'Claude ✦';
      claudeLink.addEventListener('click', () => openClaudePanel(row.local_path, row.filename));
      actionsCell.appendChild(claudeLink);
    } else {
      const ocrLink = document.createElement('a');
      ocrLink.className = 'action-link';
      ocrLink.style.color = 'var(--dim)';
      ocrLink.textContent = 'הפעל OCR';
      ocrLink.addEventListener('click', () => runOcr(row.local_path, ocrLink));
      actionsCell.appendChild(ocrLink);
    }

    tbody.appendChild(tr);
  });
}

function debounceLibSearch() {
  clearTimeout(libSearchTimer);
  libSearchTimer = setTimeout(() => {
    loadLibrary(document.getElementById('lib-search').value);
  }, 350);
}

function openFile(path) {
  fetch('/api/open', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  }).catch(() => {});
}

async function runOcr(path, linkEl) {
  linkEl.textContent = 'מעבד...';
  linkEl.style.color = 'var(--amber)';
  try {
    await apiFetch('/api/ocr', { method: 'POST', body: JSON.stringify({ path }) });
    loadLibrary(document.getElementById('lib-search').value);
  } catch (e) {
    alert('שגיאת OCR: ' + e.message);
    linkEl.textContent = 'הפעל OCR';
    linkEl.style.color = '';
  }
}

// ─── Claude panel ─────────────────────────────────────────────────────────────
function openClaudePanel(path, filename) {
  activePdfPath = path;
  document.getElementById('claude-filename').textContent = filename;
  document.getElementById('claude-response').textContent = '';
  document.getElementById('claude-input').value = '';
  document.getElementById('claude-panel').classList.remove('hidden');
  document.getElementById('claude-panel').scrollIntoView({ behavior: 'smooth' });
}

function sendPrompt(prompt) {
  if (!activePdfPath) return;
  streamAnalysis(activePdfPath, prompt);
}

function sendCustomPrompt() {
  const prompt = document.getElementById('claude-input').value.trim();
  if (!prompt || !activePdfPath) return;
  streamAnalysis(activePdfPath, prompt);
}

async function streamAnalysis(path, prompt) {
  const responseEl = document.getElementById('claude-response');
  responseEl.textContent = '';

  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, prompt }),
  });

  if (!res.ok) {
    const err = await res.json();
    responseEl.textContent = 'שגיאה: ' + (err.error || 'unknown');
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const payload = line.slice(6).trim();
      if (payload === '[DONE]') return;
      try {
        const msg = JSON.parse(payload);
        if (msg.chunk) responseEl.textContent += msg.chunk;
      } catch {}
    }
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
async function apiFetch(url, opts = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
boot();
