
const vscode = acquireVsCodeApi();
let es = null;           // active fetch reader (or null)
let streamActive = false;
let currentStreamUrl = null;
let mutantResults = [];
let lastSummary = null;
let startInfo = {};
let suggestedTests = [];
let scoreBeforeHeal = null;

// ── Message listener ────────────────────────────────────────────────────────
window.addEventListener('message', e => {
  const msg = e.data;
  if (msg.type === 'job_started') {
    // Ignore duplicate deliveries for the same job
    if (msg.stream_url === currentStreamUrl) return;
    currentStreamUrl = msg.stream_url;
    vscode.postMessage({ type: 'job_received' }); // stop retry timer + polling response
    appendLog('job_started received ✓ — starting analysis', 'ok');
    try {
      mutantResults = [];
      lastSummary = null;
      startInfo = {};
      suggestedTests = [];
      scoreBeforeHeal = null;
      const runFile = document.getElementById('run-file');
      if (runFile) runFile.textContent = msg.file || '';
      const chip = document.getElementById('term-file');
      const isTestFile = msg.file && /^test_|_test\\.py$/i.test(msg.file);
      if (chip) {
        chip.textContent = (isTestFile ? '⚠ TEST FILE: ' : '▶ ') + (msg.file || 'unknown');
        chip.className = 'term-file-chip' + (isTestFile ? ' warn' : '');
      }
      const prog = document.getElementById('progress-label');
      if (prog) prog.textContent = 'Connecting to stream…';
      const barEl = document.getElementById('bar');
      if (barEl) { barEl.style.width = '4%'; barEl.classList.add('running'); }
      clearFeed();
      addStatus('▶ ' + (msg.file || '') + '  ·  LLM: ' + (msg.llm_provider || 'none').toUpperCase());
      appendLog('▶ File: ' + (msg.file || 'unknown') + (isTestFile ? '  ⚠ This is a test file — consider selecting the source file instead' : ''), isTestFile ? 'warn' : 'ok');
      appendLog('LLM: ' + (msg.llm_provider || 'none').toUpperCase() + '  |  Stream: ' + msg.stream_url, 'info');
      connectStream(msg.stream_url);
    } catch(err) {
      const feed = document.getElementById('feed');
      if (feed) feed.innerHTML = '<div style="color:#f48771;padding:8px">Dashboard error: ' + String(err) + '</div>';
    }
  }
  if (msg.type === 'backend_log') {
    appendLog(msg.text, msg.level || 'info');
  }
  if (msg.type === 'run_error') {
    addStatus('Error: ' + msg.message);
    appendLog('Error: ' + msg.message, 'error');
  }
  if (msg.type === 'set_file') {
    const lbl = document.getElementById('run-file');
    if (lbl) lbl.textContent = msg.file || '';
  }
  if (msg.type === 'sync_settings') {
    const llmSel  = document.getElementById('llm-select-mini');
    const modeSel = document.getElementById('mode-select');
    if (llmSel  && msg.provider) llmSel.value  = msg.provider;
    if (modeSel && msg.mode)     modeSel.value = msg.mode;
    updateBadge(msg.provider || 'inhouse');
  }
  if (msg.type === 'ai_response') {
    const area = document.getElementById('chat-response');
    area.innerHTML = '<span class="chat-answer"><strong>QAMill:</strong> ' + esc(msg.answer) + '</span>';
    document.getElementById('send-btn').disabled = false;
  }
});

// ── Settings (auto-apply on change) ─────────────────────────────────────────
function updateBadge(p) {
  const badge = document.getElementById('provider-badge');
  if (!badge) return;
  const labels = {none:'NONE', claude:'CLAUDE', gpt:'GPT-4o', grok:'GROK', inhouse:'OLLAMA'};
  const cls    = {none:'pb-none', claude:'pb-claude', gpt:'pb-gpt', grok:'pb-grok', inhouse:'pb-inhouse'};
  badge.textContent = labels[p] || p.toUpperCase();
  badge.className   = 'provider-badge ' + (cls[p] || 'pb-none');
}

function autoApplySettings() {
  const provider  = document.getElementById('llm-select-mini').value;
  const mode      = document.getElementById('mode-select').value;
  const autoHeal  = mode === 'auto_heal' || mode === 'both';
  const aiMutants = mode === 'ai_mutants' || mode === 'both';
  updateBadge(provider);
  vscode.postMessage({ type: 'save_llm_settings', provider, auto_heal: autoHeal, ai_mutants: aiMutants });
}

// ── AI Chat panel ────────────────────────────────────────────────────────────
function buildContext() {
  if (!lastSummary) return 'No analysis has been run yet. Ask the developer to run an analysis first.';
  const survived = mutantResults.filter(m => m.status === 'survived');
  let ctx =
    'ANALYSIS RESULTS (use only these numbers):\n' +
    '  Total mutants   : ' + lastSummary.total + '\n' +
    '  Killed          : ' + lastSummary.killed + '\n' +
    '  Survived        : ' + lastSummary.survived + '\n' +
    '  Equivalent      : ' + lastSummary.equivalent + '\n' +
    '  True score      : ' + lastSummary.true_score + '%\n' +
    '  Raw score       : ' + lastSummary.raw_score + '%\n';

  if (survived.length === 0) {
    ctx += '  Survived mutants: NONE — all non-equivalent mutants were killed by the test suite.\n';
  } else {
    ctx += '  Survived mutants (' + survived.length + ' total):\n';
    survived.slice(0, 10).forEach(m => {
      ctx += '    - ' + m.mutant_id + ' in ' + m.function + '() line ' + m.line +
             ': ' + m.description +
             (m.difficulty ? ' [difficulty: ' + m.difficulty + ']' : '') + '\n';
    });
    if (survived.length > 10) ctx += '    ...and ' + (survived.length - 10) + ' more.\n';
  }
  return ctx;
}

function sendQuick(prompt) {
  document.getElementById('chat-input').value = prompt;
  sendChat();
}

function sendChat() {
  const input = document.getElementById('chat-input');
  const prompt = input.value.trim();
  if (!prompt) return;
  input.value = '';
  document.getElementById('send-btn').disabled = true;
  document.getElementById('chat-response').innerHTML =
    '<span class="chat-thinking">QAMill is thinking...</span>';
  vscode.postMessage({
    type: 'ai_query',
    prompt: prompt,
    context: buildContext(),
  });
}

// ── Terminal log helper ───────────────────────────────────────────────────────
function appendLog(text, level) {
  const body = document.getElementById('term-body');
  if (!body) return;
  const d = document.createElement('div');
  d.className = 'tl tl-' + (level || 'info');
  const ts = new Date().toTimeString().slice(0, 8);
  d.textContent = '[' + ts + '] ' + text;
  body.appendChild(d);
  body.scrollTop = body.scrollHeight;
}

// ── Stream handling (fetch-based — EventSource is unreliable in VS Code webviews) ──
async function connectStream(url) {
  if (streamActive && es) { try { es.cancel(); } catch(e) {} }
  streamActive = true; es = null;
  appendLog('Connecting → ' + url, 'info');
  try {
    const resp = await fetch(url);
    if (!resp.ok) {
      const msg = 'HTTP ' + resp.status + ' from stream endpoint';
      addStatus('Stream error: ' + msg);
      appendLog('Stream error: ' + msg, 'error');
      streamActive = false; return;
    }
    appendLog('Stream connected ✓', 'ok');
    const reader = resp.body.getReader();
    es = reader;
    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\\n');
      buf = lines.pop() || '';
      for (const line of lines) {
        const trim = line.trim();
        if (trim.startsWith('data:')) {
          try { handleEvent(JSON.parse(trim.slice(5).trim())); } catch(e) {}
        }
      }
    }
    appendLog('Stream closed', 'info');
  } catch (err) {
    const msg = String(err);
    addStatus('Stream error: ' + msg);
    appendLog('Stream exception: ' + msg, 'error');
  }
  streamActive = false; es = null;
}

function handleEvent(e) {
  if (e.type === 'ping') return;
  if (e.type === 'status' || e.type === 'healing') {
    addStatus(e.message);
    appendLog(e.message, 'info');
    return;
  }
  if (e.type === 'start') {
    startInfo = e;
    const aiPart = e.ai_mutant_count ? ' + ' + e.ai_mutant_count + ' AI' : '';
    document.getElementById('progress-label').textContent =
      'Analyzing ' + e.total + ' mutants (' + e.ast_mutant_count + ' AST' + aiPart + ')...';
    appendLog('Found ' + e.total + ' mutants  (' + e.ast_mutant_count + ' AST' + aiPart + ')', 'ok');
    return;
  }
  if (e.type === 'mutant_result') {
    mutantResults.push(e);
    if (e.status === 'survived' && scoreBeforeHeal === null) scoreBeforeHeal = e.true_score;
    if (e.suggested_test) addSuggestedTest(e);
    updateScores(e);
    updateBar(e.index, e.total);
    addMutantRow(e);
    return;
  }
  if (e.type === 'complete') {
    lastSummary = e;
    updateScores(e);
    document.getElementById('progress-label').textContent =
      'Complete — ' + e.total + ' mutants analysed';
    const doneBar = document.getElementById('bar');
    if (doneBar) { doneBar.style.width = '100%'; doneBar.classList.remove('running'); }
    addStatus('✔ Done · True score: ' + e.true_score + '% · Raw: ' + e.raw_score + '%');
    appendLog('Done ✓  killed=' + e.killed + '  survived=' + e.survived + '  equiv=' + e.equivalent + '  score=' + e.true_score + '%', 'ok');
    showSummary(e);
    vscode.postMessage({ type: 'analysis_complete', true_score: e.true_score });
    currentStreamUrl = null;
    if (es) { try { es.cancel(); } catch(err) {} es = null; }
    return;
  }
  if (e.type === 'error') {
    addStatus('Error: ' + e.message);
    appendLog('Backend error: ' + e.message, 'error');
  }
}

function updateScores(e) {
  if (e.true_score !== undefined) document.getElementById('true-score').textContent = e.true_score + '%';
  if (e.raw_score  !== undefined) document.getElementById('raw-score').textContent  = e.raw_score  + '%';
  if (e.killed     !== undefined) document.getElementById('killed-count').textContent   = e.killed;
  if (e.survived   !== undefined) document.getElementById('survived-count').textContent = e.survived;
  if (e.equivalent !== undefined) document.getElementById('equiv-count').textContent    = e.equivalent;
}

function updateBar(index, total) {
  const pct = Math.round(index / total * 100);
  const bar = document.getElementById('bar');
  if (bar) bar.style.width = pct + '%';
  const killed   = parseInt(document.getElementById('killed-count').textContent   || '0', 10);
  const survived = parseInt(document.getElementById('survived-count').textContent || '0', 10);
  document.getElementById('progress-label').textContent =
    index + ' / ' + total + '  ·  ✓ ' + killed + ' killed  ·  ✗ ' + survived + ' survived  (' + pct + '%)';
}

function addMutantRow(e) {
  const feed = document.getElementById('feed');
  const div = document.createElement('div');
  div.className = 'event';

  const badgeClass = {killed:'b-killed', survived:'b-survived', equivalent:'b-equivalent', error:'b-error'}[e.status] || 'b-info';
  const icon = {killed:'✓', survived:'✗', equivalent:'≡', error:'!'}[e.status] || '·';

  const isCross = e.operator && e.operator.startsWith('CMR');
  const isAI    = e.operator === 'AI';

  let tags = '';
  if (e.difficulty) {
    const dc = {low:'b-diff-low', medium:'b-diff-medium', high:'b-diff-high'}[e.difficulty] || 'b-info';
    tags += '<span class="mini-tag ' + dc + '">' + e.difficulty[0].toUpperCase() + '</span>';
  }
  if (isCross) tags += '<span class="mini-tag b-cross" title="Cross-method">X</span>';
  if (isAI)    tags += '<span class="mini-tag b-ai-mutant" title="AI mutant">AI</span>';

  div.innerHTML =
    '<span class="badge ' + badgeClass + '">' + icon + ' ' + e.status.toUpperCase() + '</span>' +
    '<span class="mut-line" title="' + esc(e.description) + (e.difficulty_reason ? ' — ' + esc(e.difficulty_reason) : '') + '">' +
      '<span class="mut-id">' + esc(e.mutant_id) + '</span>' +
      '<span class="mut-sep"> · </span>' +
      '<span class="mut-fn">' + esc(e.function) + ':' + e.line + '</span>' +
      '<span class="mut-sep"> · </span>' +
      esc(e.description) +
    '</span>' +
    tags;

  if (isCross && e.status !== 'equivalent') {
    const el = document.getElementById('cross-count');
    if (el) el.textContent = String((parseInt(el.textContent || '0', 10) || 0) + 1);
  }

  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
}

function addStatus(msg) {
  const feed = document.getElementById('feed');
  const d = document.createElement('div');
  d.className = 'status-line';
  d.textContent = msg;
  feed.appendChild(d);
}

function showSummary(e) {
  const sec = document.getElementById('summary-section');
  sec.style.display = 'block';
  const ast = startInfo.ast_mutant_count || e.total;
  const ai  = startInfo.ai_mutant_count  || 0;
  document.getElementById('summary-counts').innerHTML =
    '<span class="summary-score">' + ast + '</span> AST mutants' +
    (ai > 0 ? ' + <span class="summary-score">' + ai + '</span> AI mutants' : '') +
    ' = <strong>' + e.total + '</strong> total';
  const before = scoreBeforeHeal !== null ? scoreBeforeHeal : e.true_score;
  const improved = e.true_score > before;
  document.getElementById('summary-score').innerHTML =
    'True score: <span class="summary-score">' + e.true_score + '%</span>' +
    (improved ? ' <span style="color:#4ec9a0">(+' + (e.true_score - before).toFixed(1) + '% after healing)</span>' : '');
  const top3 = mutantResults
    .filter(m => m.status === 'survived')
    .sort((a, b) => {
      const rank = {high:0, medium:1, low:2};
      return (rank[a.difficulty] ?? 1) - (rank[b.difficulty] ?? 1);
    })
    .slice(0, 3);
  const topEl = document.getElementById('summary-top');
  if (top3.length === 0) {
    topEl.innerHTML = '<div class="top-mutant" style="color:#4ec9a0">All mutants killed!</div>';
  } else {
    topEl.innerHTML = top3.map(m =>
      '<div class="top-mutant">' +
      esc(m.mutant_id) + ' &middot; ' + esc(m.function) + ':' + m.line +
      ' &middot; ' + esc(m.description) +
      (m.difficulty ? ' <span style="opacity:.6">[' + m.difficulty + ']</span>' : '') +
      '</div>'
    ).join('');
  }
}

function addSuggestedTest(e) {
  suggestedTests.push({ id: e.mutant_id, fn: e.function, code: e.suggested_test });
  const panel = document.getElementById('suggested-panel');
  const count = document.getElementById('suggested-count');
  panel.style.display = 'block';
  count.textContent = String(suggestedTests.length);
  const block = document.getElementById('all-tests-block');
  block.textContent = suggestedTests.map(t =>
    '# --- ' + t.id + ' · ' + t.fn + ' ---\n' + t.code
  ).join('\n\n');
}

function toggleSuggested() {
  const body = document.getElementById('suggested-body');
  body.style.display = body.style.display === 'none' ? 'block' : 'none';
}

function copyAllTests() {
  const text = document.getElementById('all-tests-block').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = '&#10003; Copied!';
    setTimeout(() => { btn.innerHTML = '&#128203; Copy All Tests'; }, 2000);
  });
}

function clearFeed() {
  var g = function(id) { return document.getElementById(id); };
  var feed = g('feed');
  if (feed) feed.innerHTML = '';
  var bar = g('bar');
  if (bar) bar.style.width = '0';
  var ss = g('summary-section');
  if (ss) ss.style.display = 'none';
  var sp = g('suggested-panel');
  if (sp) sp.style.display = 'none';
  var atb = g('all-tests-block');
  if (atb) atb.textContent = '';
  var sc = g('suggested-count');
  if (sc) sc.textContent = '0';
  ['true-score','raw-score','killed-count','survived-count','equiv-count','cross-count']
    .forEach(function(id) {
      var el = g(id);
      if (el) el.textContent = id.indexOf('score') !== -1 ? '—' : '0';
    });
}

function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Wire all event listeners ──────────────────────────────────────────────────
document.getElementById('llm-select-mini').addEventListener('change', autoApplySettings);
document.getElementById('mode-select').addEventListener('change', autoApplySettings);
document.getElementById('term-clear-btn').addEventListener('click', function() {
  const b = document.getElementById('term-body'); if (b) b.innerHTML = '';
});
document.getElementById('suggested-header').addEventListener('click', toggleSuggested);
document.getElementById('copy-btn').addEventListener('click', copyAllTests);
document.getElementById('send-btn').addEventListener('click', sendChat);
document.getElementById('chat-input').addEventListener('keydown', function(ev) {
  if (ev.key === 'Enter') sendChat();
});
document.querySelectorAll('.quick-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    sendQuick(btn.getAttribute('data-prompt'));
  });
});

// Notify extension that the webview is ready — triggers pending job delivery
vscode.postMessage({ type: 'webview_ready' });

// Poll every second: if not streaming, ask extension for any pending job.
// This is the guaranteed delivery path — postMessage after reveal() can be dropped.
setInterval(function() {
  if (!streamActive) { vscode.postMessage({ type: 'request_current_job' }); }
}, 1000);
