/* ═══════════════════════════════════════════════
   AI Coding Agent: Application Logic (v2.0)
   IntegrationWings Assignment
   ═══════════════════════════════════════════════ */

/* ── STATE ─────────────────────────────────────────────── */
const state = {
  files: {},             // { filename: content }
  originalFiles: {},     // snapshot before changes
  analysis: null,
  proposedChanges: {},   // { filename: newContent }
  acceptedFiles: new Set(),
  rejectedFiles: new Set(),
  syntaxValidation: null,
  taskHistory: [],
  chatMessages: [],
  chatFilesSummary: '',
  model: 'llama-3.3-70b-versatile',
  temperature: 0.3,
  apiKey: '',
  activeNav: 'task',
  editingFile: null,
  diffFormat: 'unified',
};

/* ── DOM REFS ───────────────────────────────────────────── */
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

/* ── HELPER: SAFE ERROR PARSER ───────────────────────────── */
async function parseResponseError(res, defaultMsg = 'Request failed') {
  try {
    const errObj = await res.json();
    return errObj.detail || errObj.message || defaultMsg;
  } catch (e) {
    try {
      const text = await res.text();
      return text || defaultMsg;
    } catch {
      return defaultMsg;
    }
  }
}

/* ── INIT ───────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setupSettings();
  setupUploadTabs();
  setupDropZone();
  setupFileInput();
  setupPaste();
  setupURL();
  setupAnalyze();
  setupQuickTasks();
  setupDemoProjects();
  setupEditCodeModal();
  setupSecurityAudit();
  setupTestSandbox();
  setupHistory();
  setupChat();
  await checkAPIStatus();
});

/* ═══════════════════════════════════════════════════════════
   API STATUS
═══════════════════════════════════════════════════════════ */
async function checkAPIStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const badge = $('api-status-badge');
    if (data.api_key_configured) {
      badge.innerHTML = '<i class="fa-solid fa-circle"></i> API Ready';
      badge.className = 'badge badge-green';
    } else {
      badge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> API Key Missing';
      badge.className = 'badge badge-amber';
    }
  } catch (e) {
    console.warn('Status check failed', e);
  }
}

/* ═══════════════════════════════════════════════════════════
   WORKSPACE NAVIGATION TABS
═══════════════════════════════════════════════════════════ */
function setupNavigation() {
  $$('.nav-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetNav = btn.dataset.nav;
      switchNavTab(targetNav);
    });
  });

  document.querySelectorAll('input[name="explorer_source"]').forEach(radio => {
    radio.addEventListener('change', renderCodeExplorer);
  });

  $('diff-unified-btn')?.addEventListener('click', () => {
    state.diffFormat = 'unified';
    $('diff-unified-btn').classList.add('active');
    $('diff-sidebyside-btn').classList.remove('active');
    renderDedicatedDiff();
  });
  $('diff-sidebyside-btn')?.addEventListener('click', () => {
    state.diffFormat = 'sidebyside';
    $('diff-sidebyside-btn').classList.add('active');
    $('diff-unified-btn').classList.remove('active');
    renderDedicatedDiff();
  });

  $('copy-code-btn')?.addEventListener('click', () => {
    const code = $('explorer-code-block').textContent;
    navigator.clipboard.writeText(code);
    showToast('Code copied to clipboard!', 'success');
  });
}

function switchNavTab(navName) {
  state.activeNav = navName;
  $$('.nav-tab').forEach(b => b.classList.remove('active'));
  $$('.tab-view').forEach(v => v.classList.add('hidden'));

  const activeBtn = document.querySelector(`.nav-tab[data-nav="${navName}"]`);
  if (activeBtn) activeBtn.classList.add('active');

  const viewEl = $(`tab-view-${navName}`);
  if (viewEl) viewEl.classList.remove('hidden');

  if (navName === 'explorer') renderCodeExplorer();
  if (navName === 'diff') renderDedicatedDiff();
  if (navName === 'history') renderHistory();
}

/* ═══════════════════════════════════════════════════════════
   SETTINGS PANEL
═══════════════════════════════════════════════════════════ */
function setupSettings() {
  $('temp-range').addEventListener('input', e => {
    state.temperature = parseFloat(e.target.value);
    $('temp-val').textContent = state.temperature.toFixed(2);
  });
  $('model-select').addEventListener('change', e => {
    state.model = e.target.value;
  });
  $('api-key-input').addEventListener('input', e => {
    state.apiKey = e.target.value.trim();
  });
  $('settings-btn').addEventListener('click', () => {
    $('settings-panel').classList.toggle('hidden');
  });
  $('settings-close').addEventListener('click', () => {
    $('settings-panel').classList.add('hidden');
  });
}

/* ═══════════════════════════════════════════════════════════
   UPLOAD TABS & DROP ZONE
═══════════════════════════════════════════════════════════ */
function setupUploadTabs() {
  $$('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      $$('.tab-btn').forEach(b => b.classList.remove('active'));
      $$('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      $(`tab-${tab}`).classList.add('active');
    });
  });
}

function setupDropZone() {
  const zone = $('drop-zone');
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    handleFiles(Array.from(e.dataTransfer.files));
  });
  zone.addEventListener('click', () => $('file-input').click());
}

function setupFileInput() {
  $('file-input').addEventListener('change', e => {
    handleFiles(Array.from(e.target.files));
    e.target.value = '';
  });
}

async function handleFiles(fileList) {
  for (const file of fileList) {
    try {
      const text = await file.text();
      state.files[file.name] = text;
      state.originalFiles[file.name] = text;
    } catch (e) {
      showToast(`Could not read ${file.name}`, 'error');
    }
  }
  renderFileList();
  $('analyze-btn').disabled = Object.keys(state.files).length === 0;
}

function renderFileList() {
  const container = $('file-list');
  const names = Object.keys(state.files);
  if (names.length === 0) { container.classList.add('hidden'); return; }
  container.classList.remove('hidden');
  container.innerHTML = names.map(name => `
    <div class="file-item">
      <div>
        <div class="fname">${escHtml(name)}</div>
        <div class="fmeta">${(state.files[name].length / 1024).toFixed(1)} KB | ${state.files[name].split('\n').length} lines</div>
      </div>
      <button class="remove-btn" data-file="${escAttr(name)}" title="Remove"><i class="fa-solid fa-xmark"></i></button>
    </div>
  `).join('');

  container.querySelectorAll('.remove-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const fname = btn.dataset.file;
      delete state.files[fname];
      delete state.originalFiles[fname];
      renderFileList();
      $('analyze-btn').disabled = Object.keys(state.files).length === 0;
    });
  });
}

function setupPaste() {
  $('paste-add-btn').addEventListener('click', () => {
    const name = $('paste-filename').value.trim();
    const code = $('paste-code').value.trim();
    if (!name) { showToast('Please enter a filename', 'error'); return; }
    if (!code)  { showToast('Please paste some code', 'error'); return; }
    state.files[name] = code;
    state.originalFiles[name] = code;
    $('paste-filename').value = '';
    $('paste-code').value = '';
    renderFileList();
    $('analyze-btn').disabled = false;
    showToast(`Added: ${name}`, 'success');
  });
}

function setupURL() {
  $('url-fetch-btn').addEventListener('click', async () => {
    const url = $('url-input').value.trim();
    if (!url) { showToast('Please enter a URL', 'error'); return; }
    $('url-fetch-btn').disabled = true;
    $('url-fetch-btn').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Fetching...';
    try {
      const r = await fetch(`/api/fetch-url?url=${encodeURIComponent(url)}`);
      if (!r.ok) {
        const errMsg = await parseResponseError(r, 'Failed to fetch URL');
        throw new Error(errMsg);
      }
      const data = await r.json();
      state.files[data.filename] = data.content;
      state.originalFiles[data.filename] = data.content;
      $('url-input').value = '';
      renderFileList();
      $('analyze-btn').disabled = false;
      showToast(`Fetched: ${data.filename}`, 'success');
    } catch (e) {
      showToast(`Fetch Error: ${e.message}`, 'error');
    } finally {
      $('url-fetch-btn').disabled = false;
      $('url-fetch-btn').innerHTML = '<i class="fa-solid fa-download"></i> Fetch File';
    }
  });
}

/* ═══════════════════════════════════════════════════════════
   DEMO PROJECTS MODAL & QUICK LOAD
═══════════════════════════════════════════════════════════ */
function setupDemoProjects() {
  const triggerBtn = $('demo-projects-btn');
  const quickTrigger = $('quick-demo-trigger');
  const welcomeDemoBtn = $('welcome-demo-btn');
  const modal = $('demo-modal');
  const closeBtn = $('demo-modal-close');

  const openModal = async () => {
    modal.classList.remove('hidden');
    await loadDemoProjectsList();
  };

  triggerBtn?.addEventListener('click', openModal);
  quickTrigger?.addEventListener('click', openModal);
  closeBtn?.addEventListener('click', () => modal.classList.add('hidden'));

  welcomeDemoBtn?.addEventListener('click', async () => {
    await loadSpecificDemoProject('fastapi-user-api');
  });
}

async function loadDemoProjectsList() {
  const listEl = $('demo-projects-list');
  listEl.innerHTML = '<p class="text-muted text-center"><i class="fa-solid fa-spinner fa-spin"></i> Loading sample projects...</p>';
  try {
    const res = await fetch('/api/sample-projects');
    if (!res.ok) throw new Error(await parseResponseError(res));
    const data = await res.json();
    listEl.innerHTML = data.projects.map(p => `
      <div class="demo-card" data-id="${p.id}">
        <div class="demo-card-title"><i class="fa-solid fa-cube text-indigo"></i> ${escHtml(p.name)}</div>
        <div class="demo-card-desc">${escHtml(p.description)}</div>
        <div class="demo-card-meta">
          <span>Language: <strong>${p.language}</strong></span>
          <span>${p.file_count} file(s)</span>
        </div>
      </div>
    `).join('');

    listEl.querySelectorAll('.demo-card').forEach(card => {
      card.addEventListener('click', () => loadSpecificDemoProject(card.dataset.id));
    });
  } catch (e) {
    listEl.innerHTML = `<p class="text-muted">Error loading sample projects: ${e.message}</p>`;
  }
}

async function loadSpecificDemoProject(projectId) {
  showLoading('Loading Sample Project...', 'Fetching project files...');
  try {
    const res = await fetch(`/api/sample-projects/${projectId}`);
    if (!res.ok) throw new Error(await parseResponseError(res, 'Sample project not found'));
    const project = await res.json();

    state.files = { ...project.files };
    state.originalFiles = { ...project.files };
    state.analysis = null;
    state.proposedChanges = {};
    state.acceptedFiles.clear();
    state.rejectedFiles.clear();

    $('demo-modal').classList.add('hidden');
    renderFileList();
    $('analyze-btn').disabled = false;

    if (project.suggested_task) {
      $('task-input').value = project.suggested_task;
    }

    hideLoading();
    showToast(`Loaded Demo: ${project.name}`, 'success');
    await analyzeCodebase();
  } catch (e) {
    hideLoading();
    showToast('Failed to load demo: ' + e.message, 'error');
  }
}

/* ═══════════════════════════════════════════════════════════
   ANALYZE CODEBASE
═══════════════════════════════════════════════════════════ */
function setupAnalyze() {
  $('analyze-btn').addEventListener('click', analyzeCodebase);
  $('reset-btn').addEventListener('click', () => {
    state.files = {};
    state.originalFiles = {};
    state.analysis = null;
    state.proposedChanges = {};
    state.acceptedFiles.clear();
    state.rejectedFiles.clear();
    renderFileList();
    showScreen('welcome');
    $('analyze-btn').disabled = true;
    $('stats-section').classList.add('hidden');
    $('upload-section').classList.remove('hidden');
    updateDiffBadge();
  });
}

async function analyzeCodebase() {
  if (Object.keys(state.files).length === 0) { showToast('Please upload files first', 'error'); return; }

  showLoading('Analyzing Codebase Architecture...', 'Extracting functions, classes, and language metrics...', [
    'Reading source files',
    'Detecting languages',
    'Parsing functions and classes',
    'Validating syntax integrity',
  ]);

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files: state.files }),
    });
    if (!res.ok) {
      const errMsg = await parseResponseError(res, 'Codebase analysis failed');
      throw new Error(errMsg);
    }
    state.analysis = await res.json();
    hideLoading();
    renderAnalysis();
    renderSidebarStats();
    showScreen('analysis');
    showToast('Codebase analyzed successfully!', 'success');
  } catch (e) {
    hideLoading();
    showToast('Analysis failed: ' + e.message, 'error');
  }
}

function renderAnalysis() {
  const a = state.analysis;
  const container = $('analysis-summary');

  const fns = a.file_details?.flatMap(f => f.functions || []).slice(0, 10) || [];
  const fnHtml = fns.length ? `<div class="fn-list">Parsed Functions: ${fns.map(f => `<code>${escHtml(f)}</code>`).join(', ')}</div>` : '';

  container.innerHTML = `
    <strong>Project Structure Overview</strong>
    <div style="margin-top:10px; display:grid; grid-template-columns: repeat(3, 1fr); gap:10px;">
      <div><strong>${a.file_count}</strong> <span class="text-muted">files</span></div>
      <div><strong>${a.total_lines?.toLocaleString()}</strong> <span class="text-muted">lines</span></div>
      <div><strong>${a.function_count}</strong> <span class="text-muted">functions</span></div>
    </div>
    <div style="margin-top:10px; font-size:0.8rem; color:var(--text-2);">
      <strong>Languages:</strong> ${Object.entries(a.languages || {}).map(([k, v]) => `${k} (${v})`).join(' | ')}
    </div>
    ${fnHtml}
  `;

  state.chatFilesSummary = `Files: ${Object.keys(state.files).join(', ')}\n${a.summary || ''}`;
}

function renderSidebarStats() {
  const a = state.analysis;
  $('upload-section').classList.add('hidden');
  $('stats-section').classList.remove('hidden');

  const syntaxPill = $('syntax-status-pill');
  if (a.syntax_validation && a.syntax_validation.all_valid) {
    syntaxPill.className = 'syntax-pill syntax-valid mb-12';
    syntaxPill.innerHTML = '<span class="pill-icon"><i class="fa-solid fa-check"></i></span> AST Syntax Validated';
  } else {
    syntaxPill.className = 'syntax-pill syntax-invalid mb-12';
    syntaxPill.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Syntax Errors Detected';
  }

  $('stats-grid').innerHTML = [
    { val: a.file_count, lbl: 'Files' },
    { val: a.total_lines?.toLocaleString(), lbl: 'Lines' },
    { val: a.function_count, lbl: 'Functions' },
    { val: a.class_count, lbl: 'Classes' },
  ].map(s => `<div class="stat-card"><div class="stat-val">${s.val ?? 0}</div><div class="stat-lbl">${s.lbl}</div></div>`).join('');

  const langs = Object.entries(a.languages || {});
  const total = langs.reduce((s, [, v]) => s + v, 0) || 1;
  $('lang-breakdown').innerHTML = langs.map(([lang, cnt]) => `
    <div class="lang-item">
      <span class="lang-name">${escHtml(lang)}</span>
      <div class="lang-bar-wrap"><div class="lang-bar" style="width:${Math.round(cnt/total*100)}%"></div></div>
      <span class="lang-pct">${cnt}</span>
    </div>
  `).join('');
}

/* ═══════════════════════════════════════════════════════════
   EXECUTE TASK
═══════════════════════════════════════════════════════════ */
function setupQuickTasks() {
  $$('.qt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $('task-input').value = btn.dataset.task;
      $('task-input').focus();
    });
  });

  $('execute-btn').addEventListener('click', executeTask);
  $('run-another-btn').addEventListener('click', () => showScreen('analysis'));
  $('download-btn').addEventListener('click', downloadZIP);
}

async function executeTask() {
  const task = $('task-input').value.trim();
  if (!task) { showToast('Please describe the task first', 'error'); return; }
  if (Object.keys(state.files).length === 0) { showToast('Please upload files first', 'error'); return; }

  showLoading('AI Agent Working...', 'Formulating plan and generating code changes...', [
    'Reading codebase context',
    'Identifying target files',
    'Formulating modification plan',
    'Generating complete code changes',
    'Verifying syntax integrity',
  ], true);

  try {
    const res = await fetch('/api/execute-task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        files: state.files,
        analysis: state.analysis,
        task,
        model: state.model,
        temperature: state.temperature,
        max_tokens: 8192,
        api_key: state.apiKey || null,
      }),
    });

    if (!res.ok) {
      const errMsg = await parseResponseError(res, 'Task execution failed');
      throw new Error(errMsg);
    }

    const data = await res.json();
    hideLoading();

    state.proposedChanges = data.proposed_changes || {};
    state.syntaxValidation = data.syntax_validation || null;
    state.acceptedFiles.clear();
    state.rejectedFiles.clear();

    state.taskHistory.unshift({
      task,
      timestamp: new Date().toLocaleTimeString(),
      changesCount: Object.keys(state.proposedChanges).length,
      explanation: data.explanation || '',
      model: state.model,
    });

    renderResults(data);
    showScreen('results');
    updateDiffBadge();
    showToast(`Task complete! ${Object.keys(state.proposedChanges).length} file(s) modified.`, 'success');
  } catch (e) {
    hideLoading();
    showToast('Task failed: ' + e.message, 'error');
  }
}

/* ═══════════════════════════════════════════════════════════
   RENDER RESULTS
═══════════════════════════════════════════════════════════ */
function renderResults(data) {
  if (data.plan && data.plan.trim()) {
    $('plan-content').innerHTML = renderMarkdown(data.plan);
    $('plan-card').classList.remove('hidden');
  } else {
    $('plan-card').classList.add('hidden');
  }

  $('explanation-content').innerHTML = renderMarkdown(data.explanation || 'No explanation provided.');

  const syntaxBanner = $('result-syntax-banner');
  if (data.syntax_validation && data.syntax_validation.all_valid) {
    syntaxBanner.className = 'alert-banner alert-success mb-16';
    syntaxBanner.innerHTML = '<span><i class="fa-solid fa-circle-check"></i> <strong>Syntax Verification:</strong> All proposed code changes passed AST syntax integrity checks.</span>';
  } else if (data.syntax_validation && !data.syntax_validation.all_valid) {
    syntaxBanner.className = 'alert-banner alert-banner-error mb-16';
    syntaxBanner.innerHTML = '<span><i class="fa-solid fa-triangle-exclamation"></i> <strong>Syntax Warning:</strong> Some proposed changes contain syntax errors. Inspect diffs carefully.</span>';
  }

  const changesList = $('changes-list');
  const changes = state.proposedChanges;
  const fileNames = Object.keys(changes);

  if (fileNames.length === 0) {
    changesList.innerHTML = '<p class="text-muted text-center" style="padding:16px;">No file changes were proposed for this task.</p>';
    return;
  }

  changesList.innerHTML = fileNames.map(fname => buildChangeItem(fname, changes[fname])).join('');

  changesList.querySelectorAll('.change-header').forEach(header => {
    header.addEventListener('click', e => {
      if (e.target.closest('.edit-btn')) return;
      const body = header.nextElementSibling;
      const isOpen = body.classList.contains('open');
      body.classList.toggle('open', !isOpen);
      header.querySelector('.change-toggle').innerHTML = isOpen ? '<i class="fa-solid fa-chevron-right"></i> Show diff' : '<i class="fa-solid fa-chevron-down"></i> Hide diff';
    });
  });

  changesList.querySelectorAll('.accept-btn').forEach(btn => {
    btn.addEventListener('click', () => acceptChange(btn.dataset.file));
  });

  changesList.querySelectorAll('.reject-btn').forEach(btn => {
    btn.addEventListener('click', () => rejectChange(btn.dataset.file));
  });

  changesList.querySelectorAll('.edit-btn').forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      openEditModal(btn.dataset.file);
    });
  });

  const firstBody = changesList.querySelector('.change-body');
  if (firstBody) {
    firstBody.classList.add('open');
    const firstToggle = changesList.querySelector('.change-toggle');
    if (firstToggle) firstToggle.innerHTML = '<i class="fa-solid fa-chevron-down"></i> Hide diff';
    const diffContainer = firstBody.querySelector('.diff-container');
    if (diffContainer && diffContainer.dataset.diff) {
      renderDiff(diffContainer.id, diffContainer.dataset.diff);
    }
  }

  updateChangesSummary();
}

function buildChangeItem(fname, newContent) {
  const original = state.originalFiles[fname] || '';
  const isNew = !state.originalFiles[fname];

  const diffText = computeUnifiedDiff(fname, original, newContent);
  const addedLines = (diffText.match(/^\+[^+]/mg) || []).length;
  const removedLines = (diffText.match(/^-[^-]/mg) || []).length;

  const accepted = state.acceptedFiles.has(fname);
  const rejected = state.rejectedFiles.has(fname);

  const statusBadge = accepted
    ? '<span class="badge badge-green" style="margin-left:4px"><i class="fa-solid fa-check"></i> Accepted</span>'
    : rejected
      ? '<span class="badge badge-red" style="margin-left:4px"><i class="fa-solid fa-xmark"></i> Rejected</span>'
      : '';

  return `
    <div class="change-item" id="change-${sanitizeId(fname)}">
      <div class="change-header">
        <i class="fa-solid fa-file-code text-indigo"></i>
        <span class="change-filename">${escHtml(fname)}</span>
        ${isNew ? '<span class="change-new-badge">NEW FILE</span>' : ''}
        ${statusBadge}
        <span class="change-stats">
          <span class="stat-add">+${addedLines}</span>
          <span class="stat-del">-${removedLines}</span>
        </span>
        <button class="btn btn-ghost btn-sm edit-btn" data-file="${escAttr(fname)}" title="Edit code manually"><i class="fa-solid fa-pen"></i> Edit</button>
        <span class="change-toggle"><i class="fa-solid fa-chevron-right"></i> Show diff</span>
      </div>
      <div class="change-body">
        <div class="diff-container" id="diff-${sanitizeId(fname)}" data-diff="${escAttr(diffText)}"></div>
        <div class="change-actions">
          <button class="btn btn-success accept-btn" data-file="${escAttr(fname)}" ${accepted ? 'disabled' : ''}>
            <i class="fa-solid fa-check"></i> Accept Changes
          </button>
          <button class="btn btn-danger reject-btn" data-file="${escAttr(fname)}" ${rejected ? 'disabled' : ''}>
            <i class="fa-solid fa-xmark"></i> Reject
          </button>
        </div>
      </div>
    </div>
  `;
}

function computeUnifiedDiff(fname, original, proposed) {
  const origLines = (original || '').split('\n');
  const propLines = (proposed || '').split('\n');

  const header = `--- a/${fname}\n+++ b/${fname}\n@@ -1,${origLines.length} +1,${propLines.length} @@\n`;
  let body = '';
  const maxLen = Math.max(origLines.length, propLines.length);
  for (let i = 0; i < maxLen; i++) {
    const o = origLines[i];
    const p = propLines[i];
    if (o === undefined)      body += `+${p}\n`;
    else if (p === undefined) body += `-${o}\n`;
    else if (o !== p)         body += `-${o}\n+${p}\n`;
    else                      body += ` ${o}\n`;
  }
  return header + body;
}

function renderDiff(containerId, diffText) {
  const el = document.getElementById(containerId);
  if (!el || !diffText) return;
  try {
    const diff2htmlUi = new Diff2HtmlUI(el, diffText, {
      drawFileList: false,
      matching: 'lines',
      outputFormat: 'line-by-line',
      highlight: true,
    });
    diff2htmlUi.draw();
    diff2htmlUi.highlightCode();
  } catch (e) {
    el.innerHTML = `<pre style="padding:12px;overflow:auto;">${escHtml(diffText)}</pre>`;
  }
}

document.addEventListener('click', e => {
  const header = e.target.closest('.change-header');
  if (!header) return;
  const body = header.nextElementSibling;
  if (!body || !body.classList.contains('open')) return;
  const diffContainer = body.querySelector('.diff-container');
  if (diffContainer && diffContainer.dataset.diff && !diffContainer.dataset.rendered) {
    diffContainer.dataset.rendered = '1';
    renderDiff(diffContainer.id, diffContainer.dataset.diff);
  }
});

function acceptChange(fname) {
  state.files[fname] = state.proposedChanges[fname];
  state.originalFiles[fname] = state.proposedChanges[fname];
  state.acceptedFiles.add(fname);
  state.rejectedFiles.delete(fname);
  refreshChangeItem(fname);
  updateChangesSummary();
  updateDiffBadge();
  showToast(`Accepted changes to ${fname}`, 'success');
}

function rejectChange(fname) {
  state.rejectedFiles.add(fname);
  state.acceptedFiles.delete(fname);
  refreshChangeItem(fname);
  updateChangesSummary();
  updateDiffBadge();
  showToast(`Rejected changes to ${fname}`, 'info');
}

function refreshChangeItem(fname) {
  const item = document.getElementById(`change-${sanitizeId(fname)}`);
  if (!item) return;

  const accepted = state.acceptedFiles.has(fname);
  const rejected = state.rejectedFiles.has(fname);

  const header = item.querySelector('.change-header');
  let existingBadge = header.querySelector('.badge');
  if (existingBadge) existingBadge.remove();

  if (accepted) {
    const badge = document.createElement('span');
    badge.className = 'badge badge-green';
    badge.style.marginLeft = '4px';
    badge.innerHTML = '<i class="fa-solid fa-check"></i> Accepted';
    header.insertBefore(badge, header.querySelector('.change-stats'));
  } else if (rejected) {
    const badge = document.createElement('span');
    badge.className = 'badge badge-red';
    badge.style.marginLeft = '4px';
    badge.innerHTML = '<i class="fa-solid fa-xmark"></i> Rejected';
    header.insertBefore(badge, header.querySelector('.change-stats'));
  }

  item.querySelector('.accept-btn').disabled = accepted;
  item.querySelector('.reject-btn').disabled = rejected;
}

function updateChangesSummary() {
  const total = Object.keys(state.proposedChanges).length;
  const accepted = state.acceptedFiles.size;
  const rejected = state.rejectedFiles.size;
  const pending = total - accepted - rejected;

  const summary = $('changes-summary');
  if (total === 0) { summary.hidden = true; return; }
  summary.hidden = false;
  $('changes-count-text').textContent =
    `${total} file(s) changed | ${accepted} accepted | ${rejected} rejected | ${pending} pending review`;
}

function updateDiffBadge() {
  const count = Object.keys(state.proposedChanges).length;
  const badge = $('diff-count-badge');
  if (count > 0) {
    badge.textContent = count;
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

/* ═══════════════════════════════════════════════════════════
   EDIT CODE MODAL
═══════════════════════════════════════════════════════════ */
function setupEditCodeModal() {
  const modal = $('edit-code-modal');
  $('edit-modal-close')?.addEventListener('click', () => modal.classList.add('hidden'));
  $('cancel-edit-btn')?.addEventListener('click', () => modal.classList.add('hidden'));

  $('save-edit-btn')?.addEventListener('click', () => {
    if (!state.editingFile) return;
    const newCode = $('edit-code-textarea').value;
    state.proposedChanges[state.editingFile] = newCode;
    modal.classList.add('hidden');
    showToast(`Saved updates to ${state.editingFile}`, 'success');

    renderResults({
      plan: $('plan-content').innerHTML,
      explanation: $('explanation-content').innerHTML,
      proposed_changes: state.proposedChanges,
    });
  });
}

function openEditModal(fname) {
  state.editingFile = fname;
  const content = state.proposedChanges[fname] || state.files[fname] || '';
  $('edit-filename-title').textContent = fname;
  $('edit-code-textarea').value = content;
  $('edit-code-modal').classList.remove('hidden');
}

/* ═══════════════════════════════════════════════════════════
   CODE EXPLORER TAB
═══════════════════════════════════════════════════════════ */
function renderCodeExplorer() {
  const isProposed = document.querySelector('input[name="explorer_source"][value="proposed"]')?.checked;
  const source = isProposed
    ? { ...state.files, ...state.proposedChanges }
    : state.files;

  const treeEl = $('explorer-file-tree');
  const fileNames = Object.keys(source);

  if (fileNames.length === 0) {
    treeEl.innerHTML = '<p class="text-muted text-center">No files in codebase.</p>';
    $('explorer-filename-label').textContent = 'No file selected';
    $('explorer-code-block').textContent = 'Upload or load a codebase to view files.';
    return;
  }

  treeEl.innerHTML = fileNames.map(fname => `
    <div class="tree-item" data-file="${escAttr(fname)}">
      <span><i class="fa-solid fa-file-code text-indigo"></i> ${escHtml(fname)}</span>
      ${fname in state.proposedChanges ? '<span class="badge badge-amber">Modified</span>' : ''}
    </div>
  `).join('');

  treeEl.querySelectorAll('.tree-item').forEach(item => {
    item.addEventListener('click', () => {
      treeEl.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      displayExplorerFile(item.dataset.file, source[item.dataset.file]);
    });
  });

  const firstItem = treeEl.querySelector('.tree-item');
  if (firstItem) firstItem.click();
}

function displayExplorerFile(fname, content) {
  $('explorer-filename-label').textContent = fname;
  const codeBlock = $('explorer-code-block');
  codeBlock.textContent = content;

  const ext = fname.split('.').pop().toLowerCase();
  codeBlock.className = `language-${ext}`;
  hljs.highlightElement(codeBlock);
}

/* ═══════════════════════════════════════════════════════════
   DEDICATED DIFF INSPECTOR TAB
═══════════════════════════════════════════════════════════ */
function renderDedicatedDiff() {
  const container = $('dedicated-diff-content');
  const changes = state.proposedChanges;
  const fileNames = Object.keys(changes);

  if (fileNames.length === 0) {
    container.innerHTML = '<p class="text-muted text-center" style="padding:40px;">No proposed changes currently staged. Execute a task in the <strong>Agent Task</strong> tab to inspect diffs here.</p>';
    return;
  }

  container.innerHTML = fileNames.map(fname => {
    const original = state.originalFiles[fname] || '';
    const proposed = changes[fname];

    if (state.diffFormat === 'sidebyside') {
      return `
        <div class="result-card">
          <h4><i class="fa-solid fa-file-code text-indigo"></i> ${escHtml(fname)}</h4>
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-top:10px;">
            <div>
              <strong style="font-size:0.78rem; color:var(--text-3);">BEFORE:</strong>
              <pre class="prose"><code class="language-${fname.split('.').pop()}">${escHtml(original)}</code></pre>
            </div>
            <div>
              <strong style="font-size:0.78rem; color:var(--green);">AFTER (PROPOSED):</strong>
              <pre class="prose"><code class="language-${fname.split('.').pop()}">${escHtml(proposed)}</code></pre>
            </div>
          </div>
        </div>
      `;
    }

    const diffText = computeUnifiedDiff(fname, original, proposed);
    return `
      <div class="result-card">
        <h4><i class="fa-solid fa-file-code text-indigo"></i> ${escHtml(fname)}</h4>
        <div class="diff-container" id="ded-diff-${sanitizeId(fname)}" style="max-height:500px; margin-top:10px;"></div>
      </div>
    `;
  }).join('');

  if (state.diffFormat === 'unified') {
    fileNames.forEach(fname => {
      const diffText = computeUnifiedDiff(fname, state.originalFiles[fname] || '', changes[fname]);
      renderDiff(`ded-diff-${sanitizeId(fname)}`, diffText);
    });
  }

  container.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
}

/* ═══════════════════════════════════════════════════════════
   SECURITY AUDIT & TEST RUNNER VIEWS
═══════════════════════════════════════════════════════════ */
function setupSecurityAudit() {
  $('run-audit-btn')?.addEventListener('click', async () => {
    if (Object.keys(state.files).length === 0) {
      showToast('Please upload a codebase first', 'error'); return;
    }

    showLoading('Running Security Audit...', 'Scanning for OWASP vulnerabilities and code quality risks...');
    try {
      const res = await fetch('/api/security-audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: state.files,
          model: state.model,
          api_key: state.apiKey || null,
        }),
      });

      if (!res.ok) {
        const errMsg = await parseResponseError(res, 'Security audit failed');
        throw new Error(errMsg);
      }
      const data = await res.json();
      hideLoading();

      renderSecurityAuditResults(data);
      showToast('Security scan completed!', 'success');
    } catch (e) {
      hideLoading();
      showToast('Audit failed: ' + e.message, 'error');
    }
  });
}

function renderSecurityAuditResults(data) {
  const container = $('audit-results-container');
  const rating = data.overall_security_rating || 'B';

  container.innerHTML = `
    <div class="audit-score-card">
      <div class="audit-rating grade-${rating}">${rating}</div>
      <div>
        <h3>Security and Code Quality Rating: Grade ${rating}</h3>
        <p class="text-muted" style="margin-top:2px;">${escHtml(data.summary || 'Security audit scan completed.')}</p>
      </div>
    </div>

    <h4>Vulnerabilities and Anti-Patterns Identified (${data.issues?.length || 0})</h4>
    <div class="mt-12">
      ${(data.issues || []).map(iss => `
        <div class="audit-issue-item">
          <div class="issue-header">
            <span class="issue-title"><i class="fa-solid fa-triangle-exclamation"></i> ${escHtml(iss.issue)}</span>
            <span class="badge badge-${iss.severity === 'HIGH' ? 'red' : iss.severity === 'MEDIUM' ? 'amber' : 'blue'}">${iss.severity}</span>
          </div>
          <div style="font-size:0.78rem; color:var(--text-3); font-family:var(--mono);">File: ${escHtml(iss.file)}</div>
          <div class="issue-rec"><i class="fa-solid fa-lightbulb text-indigo"></i> <strong>Recommendation:</strong> ${escHtml(iss.recommendation)}</div>
        </div>
      `).join('') || '<p class="text-muted">No security vulnerabilities detected.</p>'}
    </div>
  `;
}

function setupTestSandbox() {
  $('run-tests-btn')?.addEventListener('click', async () => {
    const activeFiles = { ...state.files, ...state.proposedChanges };
    if (Object.keys(activeFiles).length === 0) {
      showToast('Please upload a codebase first', 'error'); return;
    }

    showLoading('Running Unit Tests in Sandbox...', 'Provisioning isolated test workspace and executing unittest suite...');
    try {
      const res = await fetch('/api/run-tests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: activeFiles }),
      });

      if (!res.ok) {
        const errMsg = await parseResponseError(res, 'Test execution failed');
        throw new Error(errMsg);
      }
      const data = await res.json();
      hideLoading();

      renderTestSandboxResults(data);
      showToast(data.success ? 'All unit tests passed!' : 'Test execution finished', data.success ? 'success' : 'info');
    } catch (e) {
      hideLoading();
      showToast('Test execution error: ' + e.message, 'error');
    }
  });
}

function renderTestSandboxResults(data) {
  const container = $('tests-results-container');
  const successBadge = data.success
    ? '<span class="badge badge-green"><i class="fa-solid fa-check"></i> PASSED</span>'
    : '<span class="badge badge-red"><i class="fa-solid fa-xmark"></i> FAILED / ERRORS</span>';

  container.innerHTML = `
    <div class="result-card mb-16">
      <div class="result-card-header">
        <span class="result-icon"><i class="fa-solid fa-vial"></i></span>
        <h3>Execution Summary</h3>
        ${successBadge}
      </div>
      <p style="font-weight:600; font-size:0.9rem;">${escHtml(data.summary)}</p>
      ${data.test_files?.length ? `<p class="text-muted mt-8">Test files executed: ${data.test_files.map(f => `<code>${f}</code>`).join(', ')}</p>` : ''}
    </div>

    <h4>Terminal Output Log</h4>
    <div class="terminal-output mt-8">${escHtml(data.stdout + '\n' + data.stderr || 'No output captured.')}</div>
  `;
}

/* ═══════════════════════════════════════════════════════════
   TASK HISTORY
═══════════════════════════════════════════════════════════ */
function setupHistory() {
  $('clear-history-btn')?.addEventListener('click', () => {
    state.taskHistory = [];
    renderHistory();
    showToast('Audit log cleared', 'info');
  });
}

function renderHistory() {
  const container = $('history-list-container');
  if (state.taskHistory.length === 0) {
    container.innerHTML = '<p class="text-muted text-center" style="padding:40px;">No tasks executed yet in this session.</p>';
    return;
  }

  container.innerHTML = state.taskHistory.map((item, idx) => `
    <div class="result-card mb-12">
      <div class="result-card-header">
        <span class="result-icon"><i class="fa-solid fa-clock-rotate-left"></i></span>
        <h3>Task #${state.taskHistory.length - idx}</h3>
        <span class="badge badge-blue">${item.timestamp}</span>
      </div>
      <p><strong>Requirement:</strong> ${escHtml(item.task)}</p>
      <div style="font-size:0.78rem; color:var(--text-3); margin-top:4px;">
        Model: <code>${item.model}</code> | Files Modified: <strong>${item.changesCount}</strong>
      </div>
    </div>
  `).join('');
}

/* ═══════════════════════════════════════════════════════════
   DOWNLOAD ZIP
═══════════════════════════════════════════════════════════ */
async function downloadZIP() {
  const finalFiles = { ...state.files };
  for (const [fname, content] of Object.entries(state.proposedChanges)) {
    if (!state.rejectedFiles.has(fname)) {
      finalFiles[fname] = content;
    }
  }

  try {
    const res = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files: finalFiles }),
    });
    if (!res.ok) throw new Error(await parseResponseError(res, 'Download failed'));
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'codebase_with_changes.zip';
    a.click();
    URL.revokeObjectURL(url);
    showToast('ZIP exported successfully!', 'success');
  } catch (e) {
    showToast('Download error: ' + e.message, 'error');
  }
}

/* ═══════════════════════════════════════════════════════════
   CHAT ASSISTANT
═══════════════════════════════════════════════════════════ */
function setupChat() {
  $('chat-toggle-btn').addEventListener('click', () => {
    $('chat-drawer').classList.toggle('hidden');
    if (!$('chat-drawer').classList.contains('hidden') && $('chat-messages').children.length === 0) {
      $('chat-messages').innerHTML = `
        <div class="chat-empty">
          <i class="fa-solid fa-comments text-indigo" style="font-size:1.5rem; margin-bottom:6px; display:block;"></i>
          Ask anything about your code architecture or refactoring.<br>
          <span style="font-size:0.72rem; color:var(--text-3);">The assistant has context of your active codebase.</span>
        </div>
      `;
    }
  });

  $('chat-close-btn').addEventListener('click', () => $('chat-drawer').classList.add('hidden'));
  $('chat-send-btn').addEventListener('click', sendChat);
  $('chat-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  });
}

async function sendChat() {
  const text = $('chat-input').value.trim();
  if (!text) return;

  $('chat-input').value = '';
  const emptyState = $('chat-messages').querySelector('.chat-empty');
  if (emptyState) emptyState.remove();

  state.chatMessages.push({ role: 'user', content: text });
  appendChatMsg('user', text);

  const assistantEl = document.createElement('div');
  assistantEl.className = 'chat-msg assistant';
  assistantEl.innerHTML = '<span style="opacity:0.5"><i class="fa-solid fa-spinner fa-spin"></i> Thinking...</span>';
  $('chat-messages').appendChild(assistantEl);
  $('chat-messages').scrollTop = $('chat-messages').scrollHeight;

  $('chat-send-btn').disabled = true;

  let fullText = '';
  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: state.chatMessages,
        files_summary: state.chatFilesSummary,
        model: state.model,
        temperature: state.temperature,
        max_tokens: 2048,
        api_key: state.apiKey || null,
      }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    assistantEl.innerHTML = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === 'token') {
            fullText += data.content;
            assistantEl.innerHTML = `<div class="prose">${renderMarkdown(fullText)}</div>`;
            $('chat-messages').scrollTop = $('chat-messages').scrollHeight;
          } else if (data.type === 'done') {
            break;
          } else if (data.type === 'error') {
            assistantEl.textContent = 'Error: ' + data.content;
          }
        } catch {}
      }
    }

    state.chatMessages.push({ role: 'assistant', content: fullText });
  } catch (e) {
    assistantEl.textContent = 'Error: ' + e.message;
  } finally {
    $('chat-send-btn').disabled = false;
  }
}

function appendChatMsg(role, text) {
  const el = document.createElement('div');
  el.className = `chat-msg ${role}`;
  el.innerHTML = role === 'assistant'
    ? `<div class="prose">${renderMarkdown(text)}</div>`
    : escHtml(text);
  $('chat-messages').appendChild(el);
  $('chat-messages').scrollTop = $('chat-messages').scrollHeight;
}

/* ═══════════════════════════════════════════════════════════
   LOADING OVERLAY & SCREENS
═══════════════════════════════════════════════════════════ */
let _loadingInterval = null;

function showLoading(title, sub, steps = [], animate = false) {
  $('loading-title').textContent = title;
  $('loading-sub').textContent = sub;

  const stepsEl = $('loading-steps');
  stepsEl.innerHTML = steps.map((s, i) => `
    <div class="loading-step" id="lstep-${i}">
      <span>${i === 0 ? '<i class="fa-solid fa-spinner fa-spin"></i>' : '<i class="fa-regular fa-circle"></i>'}</span> ${escHtml(s)}
    </div>
  `).join('');

  $('loading-overlay').classList.remove('hidden');

  if (animate && steps.length > 0) {
    let current = 0;
    document.getElementById('lstep-0')?.classList.add('active');
    _loadingInterval = setInterval(() => {
      const prev = document.getElementById(`lstep-${current}`);
      if (prev) { prev.classList.remove('active'); prev.classList.add('done'); prev.querySelector('span').innerHTML = '<i class="fa-solid fa-check"></i>'; }
      current++;
      if (current < steps.length) {
        const next = document.getElementById(`lstep-${current}`);
        if (next) { next.classList.add('active'); next.querySelector('span').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>'; }
      } else {
        clearInterval(_loadingInterval);
      }
    }, 1800);
  }
}

function hideLoading() {
  if (_loadingInterval) { clearInterval(_loadingInterval); _loadingInterval = null; }
  $('loading-overlay').classList.add('hidden');
}

function showScreen(name) {
  $('welcome-screen').classList.add('hidden');
  $('analysis-screen').classList.add('hidden');
  $('results-screen').classList.add('hidden');

  if (name === 'welcome')  $('welcome-screen').classList.remove('hidden');
  if (name === 'analysis') $('analysis-screen').classList.remove('hidden');
  if (name === 'results')  $('results-screen').classList.remove('hidden');
}

/* ═══════════════════════════════════════════════════════════
   UTILITIES
═══════════════════════════════════════════════════════════ */
function showToast(msg, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = msg;
  $('toast-container').appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; }, 2800);
  setTimeout(() => toast.remove(), 3200);
}

function escHtml(str) {
  return String(str ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(str) {
  return String(str ?? '').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function sanitizeId(str) {
  return String(str ?? '').replace(/[^a-zA-Z0-9]/g, '_');
}
function renderMarkdown(text) {
  if (!text) return '';
  try { return marked.parse(text); }
  catch { return `<p>${escHtml(text)}</p>`; }
}
