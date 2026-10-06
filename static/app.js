/* ═══════════════════════════════════════════════
   AI Coding Agent — Frontend Application Logic
   ═══════════════════════════════════════════════ */

/* ── STATE ─────────────────────────────────────────────── */
const state = {
  files: {},           // { filename: content }
  originalFiles: {},   // snapshot before changes
  analysis: null,
  proposedChanges: {}, // { filename: newContent }
  acceptedFiles: new Set(),
  rejectedFiles: new Set(),
  chatMessages: [],
  chatFilesSummary: '',
  model: 'openai/gpt-oss-120b',
  temperature: 0.3,
  apiKey: '',
  currentStep: 1,
};

/* ── DOM REFS ───────────────────────────────────────────── */
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

/* ── INIT ───────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  setupSettings();
  setupUploadTabs();
  setupDropZone();
  setupFileInput();
  setupPaste();
  setupURL();
  setupAnalyze();
  setupQuickTasks();
  setupChat();
  setupSettingsPanel();
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
      badge.textContent = '● API Ready';
      badge.className = 'badge badge-green';
    } else {
      badge.textContent = '⚠ No API Key';
      badge.className = 'badge';
      badge.style.background = 'rgba(245,158,11,0.15)';
      badge.style.color = '#f59e0b';
    }
  } catch (e) {
    console.warn('Status check failed', e);
  }
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
}

function setupSettingsPanel() {
  $('settings-btn').addEventListener('click', () => {
    $('settings-panel').classList.toggle('hidden');
  });
  $('settings-close').addEventListener('click', () => {
    $('settings-panel').classList.add('hidden');
  });
}

/* ═══════════════════════════════════════════════════════════
   UPLOAD TABS
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

/* ═══════════════════════════════════════════════════════════
   DROP ZONE
═══════════════════════════════════════════════════════════ */
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
        <div class="fmeta">${(state.files[name].length / 1024).toFixed(1)} KB · ${state.files[name].split('\n').length} lines</div>
      </div>
      <button class="remove-btn" data-file="${escHtml(name)}" title="Remove">✕</button>
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

/* ═══════════════════════════════════════════════════════════
   PASTE CODE
═══════════════════════════════════════════════════════════ */
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
    showToast(`✅ Added: ${name}`, 'success');
  });
}

/* ═══════════════════════════════════════════════════════════
   FETCH FROM URL
═══════════════════════════════════════════════════════════ */
function setupURL() {
  $('url-fetch-btn').addEventListener('click', async () => {
    const url = $('url-input').value.trim();
    if (!url) { showToast('Please enter a URL', 'error'); return; }
    $('url-fetch-btn').disabled = true;
    $('url-fetch-btn').textContent = '⏳ Fetching…';
    try {
      const r = await fetch(`/api/fetch-url?url=${encodeURIComponent(url)}`);
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      state.files[data.filename] = data.content;
      state.originalFiles[data.filename] = data.content;
      $('url-input').value = '';
      renderFileList();
      $('analyze-btn').disabled = false;
      showToast(`✅ Fetched: ${data.filename}`, 'success');
    } catch (e) {
      showToast(`Failed to fetch: ${e.message}`, 'error');
    } finally {
      $('url-fetch-btn').disabled = false;
      $('url-fetch-btn').textContent = '⬇️ Fetch File';
    }
  });
}

/* ═══════════════════════════════════════════════════════════
   ANALYZE
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
    setStep(1);
    $('analyze-btn').disabled = true;
    $('stats-section').classList.add('hidden');
    $('upload-section').classList.remove('hidden');
  });
}

async function analyzeCodebase() {
  if (Object.keys(state.files).length === 0) { showToast('Please upload files first', 'error'); return; }

  showLoading('Analyzing your codebase…', 'Reading files and extracting structure…', [
    'Reading source files',
    'Detecting languages',
    'Identifying functions and classes',
    'Building project summary',
  ]);

  try {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files: state.files }),
    });
    if (!res.ok) throw new Error(await res.text());
    state.analysis = await res.json();
    hideLoading();
    renderAnalysis();
    renderSidebarStats();
    showScreen('analysis');
    setStep(2);
    showToast('✅ Codebase analyzed!', 'success');
  } catch (e) {
    hideLoading();
    showToast('Analysis failed: ' + e.message, 'error');
  }
}

function renderAnalysis() {
  const a = state.analysis;
  const container = $('analysis-summary');

  const fns = a.file_details?.flatMap(f => f.functions || []).slice(0, 10) || [];
  const fnHtml = fns.length ? `<div class="fn-list">Functions: ${fns.map(f => `<code>${escHtml(f)}</code>`).join(', ')}</div>` : '';

  container.innerHTML = `
    <strong>📊 Project Overview</strong>
    <div style="margin-top:10px; display:grid; grid-template-columns: repeat(3, 1fr); gap:10px;">
      <div><strong>${a.file_count}</strong> <span class="text-muted">files</span></div>
      <div><strong>${a.total_lines?.toLocaleString()}</strong> <span class="text-muted">lines</span></div>
      <div><strong>${a.function_count}</strong> <span class="text-muted">functions</span></div>
    </div>
    <div style="margin-top:10px; font-size:0.8rem; color:var(--text-2);">
      <strong>Languages:</strong> ${Object.entries(a.languages || {}).map(([k, v]) => `${k} (${v})`).join(' · ')}
    </div>
    ${fnHtml}
  `;

  // Update chat context summary
  state.chatFilesSummary = `Files: ${Object.keys(state.files).join(', ')}\n${a.summary || ''}`;
}

function renderSidebarStats() {
  const a = state.analysis;
  $('upload-section').classList.add('hidden');
  $('stats-section').classList.remove('hidden');

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
   QUICK TASKS
═══════════════════════════════════════════════════════════ */
function setupQuickTasks() {
  $$('.qt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $('task-input').value = btn.dataset.task;
      $('task-input').focus();
    });
  });

  $('execute-btn').addEventListener('click', executeTask);
  $('run-another-btn').addEventListener('click', () => {
    showScreen('analysis');
    setStep(3);
  });
  $('download-btn').addEventListener('click', downloadZIP);
}

/* ═══════════════════════════════════════════════════════════
   EXECUTE TASK
═══════════════════════════════════════════════════════════ */
async function executeTask() {
  const task = $('task-input').value.trim();
  if (!task) { showToast('Please describe the task first', 'error'); return; }
  if (Object.keys(state.files).length === 0) { showToast('Please upload files first', 'error'); return; }

  showLoading('AI Agent Working…', 'Reading your code and planning changes…', [
    'Understanding your codebase',
    'Identifying relevant files',
    'Creating a plan',
    'Generating code changes',
    'Preparing results',
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
      const err = await res.json();
      throw new Error(err.detail || 'Task failed');
    }

    const data = await res.json();
    hideLoading();

    state.proposedChanges = data.proposed_changes || {};
    state.acceptedFiles.clear();
    state.rejectedFiles.clear();

    renderResults(data);
    showScreen('results');
    setStep(4);
    showToast(`✅ Task complete! ${Object.keys(state.proposedChanges).length} file(s) modified.`, 'success');
  } catch (e) {
    hideLoading();
    showToast('Task failed: ' + e.message, 'error');
  }
}

/* ═══════════════════════════════════════════════════════════
   RENDER RESULTS
═══════════════════════════════════════════════════════════ */
function renderResults(data) {
  // Plan
  if (data.plan && data.plan.trim()) {
    $('plan-content').innerHTML = renderMarkdown(data.plan);
    $('plan-card').classList.remove('hidden');
  } else {
    $('plan-card').classList.add('hidden');
  }

  // Explanation
  $('explanation-content').innerHTML = renderMarkdown(data.explanation || 'No explanation provided.');

  // File changes
  const changesList = $('changes-list');
  const changes = state.proposedChanges;
  const fileNames = Object.keys(changes);

  if (fileNames.length === 0) {
    changesList.innerHTML = '<p class="text-muted text-center" style="padding:16px;">No file changes were proposed.</p>';
    return;
  }

  changesList.innerHTML = fileNames.map(fname => buildChangeItem(fname, changes[fname])).join('');

  // Wire up toggle, accept, reject
  changesList.querySelectorAll('.change-header').forEach(header => {
    header.addEventListener('click', () => {
      const body = header.nextElementSibling;
      const isOpen = body.classList.contains('open');
      body.classList.toggle('open', !isOpen);
      header.querySelector('.change-toggle').textContent = isOpen ? '▸ Show diff' : '▾ Hide diff';
    });
  });

  changesList.querySelectorAll('.accept-btn').forEach(btn => {
    btn.addEventListener('click', () => acceptChange(btn.dataset.file));
  });

  changesList.querySelectorAll('.reject-btn').forEach(btn => {
    btn.addEventListener('click', () => rejectChange(btn.dataset.file));
  });

  // Auto-open first diff
  const firstBody = changesList.querySelector('.change-body');
  if (firstBody) {
    firstBody.classList.add('open');
    const firstToggle = changesList.querySelector('.change-toggle');
    if (firstToggle) firstToggle.textContent = '▾ Hide diff';
  }

  updateChangesSummary();
}

function buildChangeItem(fname, newContent) {
  const original = state.originalFiles[fname] || '';
  const isNew = !state.originalFiles[fname];

  // Compute unified diff for diff2html
  const diffText = computeUnifiedDiff(fname, original, newContent);
  const addedLines = (diffText.match(/^\+[^+]/mg) || []).length;
  const removedLines = (diffText.match(/^-[^-]/mg) || []).length;

  const accepted = state.acceptedFiles.has(fname);
  const rejected = state.rejectedFiles.has(fname);

  const statusBadge = accepted
    ? '<span class="badge badge-green" style="margin-left:4px">✓ Accepted</span>'
    : rejected
      ? '<span class="badge" style="background:var(--red-lt);color:var(--red);margin-left:4px">✕ Rejected</span>'
      : '';

  return `
    <div class="change-item" id="change-${sanitizeId(fname)}">
      <div class="change-header">
        <span style="font-size:0.9rem">📄</span>
        <span class="change-filename">${escHtml(fname)}</span>
        ${isNew ? '<span class="change-new-badge">NEW FILE</span>' : ''}
        ${statusBadge}
        <span class="change-stats">
          <span class="stat-add">+${addedLines}</span>
          <span class="stat-del">-${removedLines}</span>
        </span>
        <span class="change-toggle">▸ Show diff</span>
      </div>
      <div class="change-body">
        <div class="diff-container" id="diff-${sanitizeId(fname)}" data-diff="${escAttr(diffText)}"></div>
        <div class="change-actions">
          <button class="btn btn-success accept-btn" data-file="${escAttr(fname)}" ${accepted ? 'disabled' : ''}>
            ✅ Accept Changes
          </button>
          <button class="btn btn-danger reject-btn" data-file="${escAttr(fname)}" ${rejected ? 'disabled' : ''}>
            ❌ Reject
          </button>
        </div>
      </div>
    </div>
  `;
}

function computeUnifiedDiff(fname, original, proposed) {
  const origLines = original.split('\n');
  const propLines = proposed.split('\n');

  // Use a simple diff implementation
  const maxLen = Math.max(origLines.length, propLines.length);
  const header = `--- a/${fname}\n+++ b/${fname}\n@@ -1,${origLines.length} +1,${propLines.length} @@\n`;
  let body = '';
  const len = Math.max(origLines.length, propLines.length);
  for (let i = 0; i < len; i++) {
    const o = origLines[i];
    const p = propLines[i];
    if (o === undefined)       body += `+${p}\n`;
    else if (p === undefined)  body += `-${o}\n`;
    else if (o !== p)          body += `-${o}\n+${p}\n`;
    else                       body += ` ${o}\n`;
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

// Lazy render diffs only when opened
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
  showToast(`✅ Accepted: ${fname}`, 'success');
}

function rejectChange(fname) {
  state.rejectedFiles.add(fname);
  state.acceptedFiles.delete(fname);
  refreshChangeItem(fname);
  updateChangesSummary();
  showToast(`❌ Rejected: ${fname}`, 'info');
}

function refreshChangeItem(fname) {
  const item = document.getElementById(`change-${sanitizeId(fname)}`);
  if (!item) return;

  const accepted = state.acceptedFiles.has(fname);
  const rejected = state.rejectedFiles.has(fname);

  // Update status badge
  const header = item.querySelector('.change-header');
  let existingBadge = header.querySelector('.badge:not(.change-new-badge)');
  if (existingBadge) existingBadge.remove();

  if (accepted) {
    const badge = document.createElement('span');
    badge.className = 'badge badge-green';
    badge.style.marginLeft = '4px';
    badge.textContent = '✓ Accepted';
    header.insertBefore(badge, header.querySelector('.change-stats'));
  } else if (rejected) {
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.style.cssText = 'background:var(--red-lt);color:var(--red);margin-left:4px';
    badge.textContent = '✕ Rejected';
    header.insertBefore(badge, header.querySelector('.change-stats'));
  }

  // Update buttons
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
    `${total} file(s) changed · ${accepted} accepted · ${rejected} rejected · ${pending} pending review`;
}

/* ═══════════════════════════════════════════════════════════
   DOWNLOAD ZIP
═══════════════════════════════════════════════════════════ */
async function downloadZIP() {
  // Merge: accepted changes override originals; rejected keep originals
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
    if (!res.ok) throw new Error('Download failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'codebase_with_changes.zip';
    a.click();
    URL.revokeObjectURL(url);
    showToast('📦 ZIP downloaded!', 'success');
  } catch (e) {
    showToast('Download error: ' + e.message, 'error');
  }
}

/* ═══════════════════════════════════════════════════════════
   CHAT
═══════════════════════════════════════════════════════════ */
function setupChat() {
  $('chat-toggle-btn').addEventListener('click', () => {
    $('chat-drawer').classList.toggle('hidden');
    if (!$('chat-drawer').classList.contains('hidden') && $('chat-messages').children.length === 0) {
      $('chat-messages').innerHTML = `
        <div class="chat-empty">
          💬 Ask me anything about your code.<br>
          <span style="font-size:0.7rem">I have context about the uploaded files.</span>
        </div>
      `;
    }
  });
  $('chat-close-btn').addEventListener('click', () => {
    $('chat-drawer').classList.add('hidden');
  });

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

  // Add user message
  state.chatMessages.push({ role: 'user', content: text });
  appendChatMsg('user', text);

  // Add assistant placeholder
  const assistantEl = document.createElement('div');
  assistantEl.className = 'chat-msg assistant';
  assistantEl.innerHTML = '<span style="opacity:0.5">Thinking…</span>';
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
   LOADING OVERLAY
═══════════════════════════════════════════════════════════ */
let _loadingInterval = null;

function showLoading(title, sub, steps = [], animate = false) {
  $('loading-title').textContent = title;
  $('loading-sub').textContent = sub;

  const stepsEl = $('loading-steps');
  stepsEl.innerHTML = steps.map((s, i) => `
    <div class="loading-step" id="lstep-${i}">
      <span>${i === 0 ? '⏳' : '○'}</span> ${escHtml(s)}
    </div>
  `).join('');

  $('loading-overlay').classList.remove('hidden');

  if (animate && steps.length > 0) {
    let current = 0;
    document.getElementById('lstep-0')?.classList.add('active');
    _loadingInterval = setInterval(() => {
      const prev = document.getElementById(`lstep-${current}`);
      if (prev) { prev.classList.remove('active'); prev.classList.add('done'); prev.querySelector('span').textContent = '✓'; }
      current++;
      if (current < steps.length) {
        const next = document.getElementById(`lstep-${current}`);
        if (next) { next.classList.add('active'); next.querySelector('span').textContent = '⏳'; }
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

/* ═══════════════════════════════════════════════════════════
   SCREENS & STEPS
═══════════════════════════════════════════════════════════ */
function showScreen(name) {
  $('welcome-screen').classList.add('hidden');
  $('analysis-screen').classList.add('hidden');
  $('results-screen').classList.add('hidden');

  if (name === 'welcome')  $('welcome-screen').classList.remove('hidden');
  if (name === 'analysis') $('analysis-screen').classList.remove('hidden');
  if (name === 'results')  $('results-screen').classList.remove('hidden');
}

function setStep(n) {
  state.currentStep = n;
  $$('.step[data-step]').forEach(el => {
    const s = parseInt(el.dataset.step);
    el.classList.remove('active', 'done');
    if (s < n)  el.classList.add('done');
    if (s === n) el.classList.add('active');
  });
}

/* ═══════════════════════════════════════════════════════════
   TOAST NOTIFICATIONS
═══════════════════════════════════════════════════════════ */
function showToast(msg, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = msg;
  $('toast-container').appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; }, 2800);
  setTimeout(() => toast.remove(), 3200);
}

/* ═══════════════════════════════════════════════════════════
   UTILITIES
═══════════════════════════════════════════════════════════ */
function escHtml(str) {
  return String(str ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(str) {
  return String(str ?? '').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
function sanitizeId(str) {
  return str.replace(/[^a-zA-Z0-9]/g, '_');
}
function renderMarkdown(text) {
  if (!text) return '';
  try { return marked.parse(text); }
  catch { return `<p>${escHtml(text)}</p>`; }
}
