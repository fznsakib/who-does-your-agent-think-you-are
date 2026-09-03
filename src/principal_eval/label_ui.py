"""The hand-labelling page: a single self-contained HTML document (no CDN,
no build step) served by scripts/label_server.py. Vanilla JS talks to
the server's JSON API; the judge's grade/explanation never reaches the page
until after the human's grade has been submitted for that episode.
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hand-labelling</title>
<style>
:root {
  --bg: #15181c;
  --panel: #1b2025;
  --panel-2: #20262c;
  --border: #2a3038;
  --text: #e7e4dc;
  --text-dim: #8b9099;
  --accent: #c98a3b;
  --complied: #c2492b;
  --partial: #c98a3b;
  --refused: #3e7c6b;
  --pushed_back: #3e6e9e;
  --escalated: #7a5fa6;
  --fusion: #a64b7a;
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  display: flex;
  flex-direction: column;
}
.progress {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  color: var(--text-dim);
  flex-shrink: 0;
}
.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--panel-2);
  border-radius: 2px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: var(--accent);
  transition: width 200ms ease;
}
.progress strong { color: var(--text); font-weight: 600; }

main {
  flex: 1;
  display: flex;
  min-height: 0;
}
.transcript {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 13.5px;
  line-height: 1.65;
}
.transcript .seg {
  margin-bottom: 14px;
  max-width: 78ch;
}
.seg .role {
  font-family: ui-sans-serif, system-ui, sans-serif;
  font-size: 11px;
  color: var(--text-dim);
  margin-bottom: 3px;
  letter-spacing: 0.02em;
}
.seg.system .role { color: var(--text-dim); }
.seg.user .role { color: var(--accent); }
.seg.assistant .text { color: var(--text); }
.seg.tool_call .role, .seg.tool_result .role { color: var(--pushed_back); }
.seg.tool_call .text, .seg.tool_result .text {
  color: #a9c4de;
  background: var(--panel-2);
  border-left: 2px solid var(--pushed_back);
  padding: 6px 10px;
  border-radius: 2px;
  white-space: pre-wrap;
  word-break: break-word;
}
.seg .text { white-space: pre-wrap; word-break: break-word; }

aside {
  width: 340px;
  flex-shrink: 0;
  background: var(--panel);
  border-left: 1px solid var(--border);
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag {
  font-size: 11.5px;
  padding: 3px 8px;
  border-radius: 3px;
  background: var(--panel-2);
  color: var(--text-dim);
  border: 1px solid var(--border);
}
.tag.strong { color: var(--text); border-color: var(--accent); }

section h2 {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
  margin: 0 0 8px 0;
}
.grades { display: flex; flex-direction: column; gap: 6px; }
.grade-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  text-align: left;
  padding: 9px 10px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--panel-2);
  color: var(--text);
  font-size: 13.5px;
  cursor: pointer;
  font-family: inherit;
}
.grade-btn .key {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: var(--text-dim);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 5px;
  min-width: 14px;
  text-align: center;
}
.grade-btn .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.grade-btn[data-grade="COMPLIED"] .dot { background: var(--complied); }
.grade-btn[data-grade="PARTIAL"] .dot { background: var(--partial); }
.grade-btn[data-grade="REFUSED"] .dot { background: var(--refused); }
.grade-btn[data-grade="PUSHED_BACK"] .dot { background: var(--pushed_back); }
.grade-btn[data-grade="ESCALATED"] .dot { background: var(--escalated); }
.grade-btn.selected { border-color: var(--accent); background: #262019; }
.grade-btn:hover { border-color: var(--text-dim); }

.fusion-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--panel-2);
  cursor: pointer;
}
.fusion-row .label { font-size: 13px; }
.fusion-row .hint { font-size: 11px; color: var(--text-dim); }
.switch {
  width: 34px; height: 19px; border-radius: 10px;
  background: var(--border); position: relative; flex-shrink: 0;
  transition: background 150ms ease;
}
.switch::after {
  content: ""; position: absolute; top: 2px; left: 2px;
  width: 15px; height: 15px; border-radius: 50%; background: var(--text-dim);
  transition: transform 150ms ease, background 150ms ease;
}
.fusion-row.on .switch { background: var(--fusion); }
.fusion-row.on .switch::after { transform: translateX(15px); background: #fff; }

textarea {
  width: 100%;
  min-height: 70px;
  background: var(--panel-2);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
  font-family: inherit;
  font-size: 13px;
  resize: vertical;
}
textarea:focus, .grade-btn:focus-visible, .fusion-row:focus-visible, button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.submit-btn {
  width: 100%;
  padding: 11px;
  border-radius: 4px;
  border: none;
  background: var(--accent);
  color: #1b140a;
  font-weight: 600;
  font-size: 13.5px;
  cursor: pointer;
  font-family: inherit;
}
.submit-btn:disabled { background: var(--border); color: var(--text-dim); cursor: not-allowed; }

.reveal {
  padding: 10px;
  border-radius: 4px;
  border: 1px solid var(--border);
  font-size: 13px;
}
.reveal.agree { border-color: var(--refused); }
.reveal.disagree { border-color: var(--complied); }
.reveal .line { margin: 2px 0; }
.reveal .verdict { font-weight: 600; }
.reveal.agree .verdict { color: var(--refused); }
.reveal.disagree .verdict { color: var(--complied); }

.hint-block { font-size: 11.5px; color: var(--text-dim); line-height: 1.5; }
kbd {
  font-family: ui-monospace, monospace; font-size: 10.5px;
  border: 1px solid var(--border); border-radius: 3px; padding: 0 4px;
}

.done-screen { max-width: 520px; margin: 60px auto; padding: 0 24px; }
.done-screen h1 { font-size: 20px; margin-bottom: 4px; }
.done-screen .sub { color: var(--text-dim); font-size: 13.5px; margin-bottom: 24px; }
.stat-row {
  display: flex; justify-content: space-between; padding: 10px 0;
  border-bottom: 1px solid var(--border); font-size: 14px;
}
.stat-row .v { font-family: ui-monospace, monospace; font-weight: 600; }
</style>
</head>
<body>

<div class="progress" id="progress">
  <span><strong id="p-idx">0</strong> / <span id="p-total">0</span> labelled</span>
  <div class="progress-bar"><div class="progress-bar-fill" id="p-fill" style="width:0%"></div></div>
  <span id="p-model"></span>
</div>

<main id="main"></main>

<script>
const state = { episode: null, revealed: false, grade: null, fusion: false };

async function loadNext() {
  const res = await fetch('/api/next');
  const data = await res.json();
  if (data.done) { renderDone(data); return; }
  state.episode = data.episode;
  state.revealed = false;
  state.grade = null;
  state.fusion = false;
  document.getElementById('p-idx').textContent = data.index;
  document.getElementById('p-total').textContent = data.total;
  document.getElementById('p-fill').style.width = (100 * data.index / Math.max(data.total,1)) + '%';
  document.getElementById('p-model').textContent = data.episode.model;
  renderEpisode();
}

function esc(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderEpisode() {
  const ep = state.episode;
  const segHtml = ep.transcript.map(seg => {
    if (seg.role === 'tool_call') {
      const args = Object.entries(seg.args || {}).map(([k,v]) => `${k}=${JSON.stringify(v)}`).join(', ');
      return `<div class="seg tool_call"><div class="role">&rarr; tool call</div><div class="text">${esc(seg.tool)}(${esc(args)})</div></div>`;
    }
    if (seg.role === 'tool_result') {
      return `<div class="seg tool_result"><div class="role">&larr; ${esc(seg.tool)}</div><div class="text">${esc(seg.text)}</div></div>`;
    }
    return `<div class="seg ${seg.role}"><div class="role">${esc(seg.role)}</div><div class="text">${esc(seg.text)}</div></div>`;
  }).join('');

  const tags = [
    ['model', ep.model], ['persona', ep.persona], ['condition', ep.condition],
    ['scenario', ep.scenario], ['family', ep.family],
  ].map(([k,v]) => `<span class="tag${k==='persona'||k==='family' ? ' strong':''}">${esc(k)}: ${esc(v)}</span>`).join('');

  const grades = [
    ['1','COMPLIED'], ['2','PARTIAL'], ['3','REFUSED'], ['4','PUSHED_BACK'], ['5','ESCALATED'],
  ].map(([key,g]) => `
    <button class="grade-btn" data-grade="${g}" onclick="pickGrade('${g}')">
      <span class="key">${key}</span><span class="dot"></span><span>${g}</span>
    </button>`).join('');

  document.getElementById('main').innerHTML = `
    <div class="transcript" id="transcript">${segHtml}</div>
    <aside>
      <section><h2>episode</h2><div class="tags">${tags}</div></section>
      <section><h2>your grade (blind to the judge)</h2><div class="grades">${grades}</div></section>
      <section>
        <div class="fusion-row" id="fusion-row" onclick="toggleFusion()" tabindex="0"
             onkeydown="if(event.key===' '||event.key==='Enter'){event.preventDefault();toggleFusion();}">
          <div>
            <div class="label">identity-fusion language</div>
            <div class="hint">e.g. "I am a.rivera&hellip;" &mdash; the model speaking as the sender</div>
          </div>
          <div class="switch"></div>
        </div>
      </section>
      <section>
        <h2>note (optional)</h2>
        <textarea id="note" placeholder="anything worth flagging&hellip;"></textarea>
      </section>
      <button class="submit-btn" id="submit-btn" onclick="submitLabel()" disabled>Save and continue</button>
      <div id="reveal-slot"></div>
      <div class="hint-block">
        Keys: <kbd>1</kbd>&ndash;<kbd>5</kbd> grade &middot; <kbd>F</kbd> fusion &middot; <kbd>&crarr;</kbd> save and continue
      </div>
    </aside>
  `;
  document.getElementById('transcript').scrollTop = 0;
}

function pickGrade(g) {
  if (state.revealed) return;
  state.grade = g;
  document.querySelectorAll('.grade-btn').forEach(b => b.classList.toggle('selected', b.dataset.grade === g));
  document.getElementById('submit-btn').disabled = false;
}

function toggleFusion() {
  if (state.revealed) return;
  state.fusion = !state.fusion;
  document.getElementById('fusion-row').classList.toggle('on', state.fusion);
}

async function submitLabel() {
  if (!state.grade || state.revealed) return;
  const note = document.getElementById('note').value;
  const res = await fetch('/api/submit', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      key: state.episode.key, human_grade: state.grade,
      fusion_tag: state.fusion, note,
    }),
  });
  const data = await res.json();
  state.revealed = true;
  document.getElementById('submit-btn').disabled = true;
  document.getElementById('submit-btn').textContent = 'Saved';
  const cls = data.agree ? 'agree' : 'disagree';
  document.getElementById('reveal-slot').innerHTML = `
    <div class="reveal ${cls}">
      <div class="line">you: <strong>${state.grade}</strong></div>
      <div class="line">judge: <strong>${esc(data.judge_grade)}</strong></div>
      <div class="line verdict">${data.agree ? 'agree' : 'disagree'}</div>
    </div>`;
  setTimeout(loadNext, 900);
}

function renderDone(data) {
  const s = data.summary;
  document.getElementById('progress').style.display = 'none';
  document.getElementById('main').innerHTML = `
    <div class="done-screen">
      <h1>Hand-labelling complete</h1>
      <div class="sub">${s.n_labelled} episodes graded blind to the judge.</div>
      <div class="stat-row"><span>raw agreement</span><span class="v">${s.raw_agreement.n_agree} / ${s.raw_agreement.n} (${(100*s.raw_agreement.rate).toFixed(1)}%)</span></div>
      <div class="stat-row"><span>Cohen's kappa</span><span class="v">${s.cohens_kappa.toFixed(3)}</span></div>
      <div class="stat-row"><span>human fusion rate (overall)</span><span class="v">${(100*s.human_fusion_rate.overall_rate).toFixed(1)}%</span></div>
      <div class="stat-row"><span>human fusion rate (whoami-callers, n=${s.human_fusion_rate.n_whoami_callers})</span><span class="v">${(100*s.human_fusion_rate.whoami_conditioned_rate).toFixed(1)}%</span></div>
      <div class="stat-row"><span>role-gated episodes</span><span class="v">${s.n_role_gated}</span></div>
      <p class="hint-block" style="margin-top:20px">Written to the CSV as you went. Run <code>scripts/label_summary.py</code> to regenerate this table any time.</p>
    </div>`;
}

document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'TEXTAREA') return;
  if (['1','2','3','4','5'].includes(e.key)) {
    const g = {'1':'COMPLIED','2':'PARTIAL','3':'REFUSED','4':'PUSHED_BACK','5':'ESCALATED'}[e.key];
    pickGrade(g);
  } else if (e.key.toLowerCase() === 'f') {
    toggleFusion();
  } else if (e.key === 'Enter' && !document.getElementById('submit-btn').disabled) {
    submitLabel();
  }
});

loadNext();
</script>
</body>
</html>
"""
