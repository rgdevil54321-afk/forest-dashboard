/* ── Tab Navigation ───────────────────────────────────── */
const TAB_TITLES = {
  dash:        'Dashboard',
  control:     'Control Panel',
  console_tab: 'Console',
  ai:          'AI Assistant',
};

function showTab(id, btn) {
  document.querySelectorAll('.tab').forEach(t => {
    t.classList.remove('active-tab');
    t.style.display = 'none';
  });
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

  const tab = document.getElementById(id);
  tab.style.display = 'block';
  setTimeout(() => tab.classList.add('active-tab'), 10);

  if (btn) btn.classList.add('active');
  document.getElementById('pageTitle').textContent = TAB_TITLES[id] || id;
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

/* ── Auth: load user info on page load ───────────────── */
async function loadMe() {
  try {
    const res  = await fetch('/auth/me');
    if (res.status === 401) { window.location.href = '/login'; return; }
    const data = await res.json();
    document.getElementById('topbarUsername').textContent = data.display || data.username;
    const roleEl = document.getElementById('topbarRole');
    if (data.role && data.role !== 'member') {
      roleEl.textContent = data.role;
      roleEl.style.display = 'inline';
    }
  } catch (e) {
    console.error('loadMe:', e);
  }
}

async function doLogout() {
  try {
    await fetch('/auth/logout', { method: 'POST' });
  } finally {
    window.location.href = '/login';
  }
}

/* ── Clock ────────────────────────────────────────────── */
function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleTimeString('en-US', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

/* ── API / Dashboard ──────────────────────────────────── */
let lastStatus = null;
const activityLog = [];

function pushActivity(msg, color = '#00e5a0') {
  const now = new Date().toLocaleTimeString('en-US', { hour12: false });
  activityLog.unshift({ msg, color, time: now });
  if (activityLog.length > 8) activityLog.pop();
  renderActivity();
}

function renderActivity() {
  const el = document.getElementById('activityFeed');
  if (!activityLog.length) {
    el.innerHTML = '<div class="activity-item"><span class="activity-dot"></span><span>Waiting for activity...</span></div>';
    return;
  }
  el.innerHTML = activityLog.map(a =>
    `<div class="activity-item">
      <span class="activity-dot" style="background:${a.color}"></span>
      <span style="flex:1">${a.msg}</span>
      <span style="font-size:11px;opacity:.5;font-family:'JetBrains Mono',monospace">${a.time}</span>
    </div>`
  ).join('');
}

async function loadData() {
  try {
    const res = await fetch('/api');
    if (res.status === 401) { window.location.href = '/login'; return; }
    const data = await res.json();

    document.getElementById('status').textContent     = data.status;
    document.getElementById('players').textContent    = data.players;
    document.getElementById('maxPlayers').textContent = data.maxPlayers;
    document.getElementById('serverIp').textContent   = data.ip;
    document.getElementById('uptime').textContent     = data.uptime;
    document.getElementById('memory').textContent     = data.memory;
    document.getElementById('cpu').textContent        = data.cpu;

    document.getElementById('version').textContent       = data.version;
    document.getElementById('ipDetail').textContent      = data.ip;
    document.getElementById('statusDetail').textContent  = data.status;
    document.getElementById('playersDetail').textContent = `${data.players} / ${data.maxPlayers}`;

    const mpInput = document.getElementById('maxPlayersInput');
    if (mpInput && !mpInput.dataset.userEdited) mpInput.value = data.maxPlayers;

    const dot  = document.querySelector('.badge-dot');
    const btxt = document.querySelector('.badge-text');
    const isOnline = data.status.toLowerCase().includes('online');
    dot.className    = `badge-dot ${isOnline ? 'online' : 'offline'}`;
    btxt.textContent = data.status;

    if (lastStatus && lastStatus !== data.status) {
      pushActivity(`Status → <strong>${data.status}</strong>`, isOnline ? '#00e5a0' : '#f87171');
    }
    lastStatus = data.status;

  } catch (e) {
    document.getElementById('status').textContent = 'Error';
  }
}

/* ── Control Actions ──────────────────────────────────── */
const actionIcons  = { start: '▶', stop: '⏹', restart: '↺' };
const actionLabels = { start: 'Server Started', stop: 'Server Stopped', restart: 'Server Restarting' };
const actionColors = { start: '#00e5a0', stop: '#f87171', restart: '#a78bfa' };

async function sendAction(action) {
  const feedback = document.getElementById('actionFeedback');
  const tag      = document.getElementById('controlStatus');
  const lastEl   = document.getElementById('lastAction');
  const now      = new Date().toLocaleTimeString('en-US', { hour12: false });

  feedback.textContent = `⏳ Executing ${action}...`;
  tag.textContent = 'Processing';

  try {
    const res  = await fetch('/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    });
    if (res.status === 401) { window.location.href = '/login'; return; }
    const data = await res.json();

    if (data.ok) {
      const label = actionLabels[action] || action;
      const color = actionColors[action] || '#00e5a0';
      feedback.innerHTML = `<span style="color:${color}">✓ ${label}</span>`;
      tag.textContent    = 'Done';
      lastEl.innerHTML   = `
        <div class="la-icon">${actionIcons[action] || '•'}</div>
        <div class="la-text" style="color:${color}">${label}</div>
        <div class="la-time">${now}</div>
      `;
      pushActivity(`Action: <strong>${action.toUpperCase()}</strong>`, color);
      setTimeout(loadData, 800);
    }
  } catch (e) {
    feedback.innerHTML = `<span style="color:#f87171">✗ Failed</span>`;
  }

  setTimeout(() => { feedback.textContent = ''; tag.textContent = 'Idle'; }, 4000);
}

/* ── IP Save ──────────────────────────────────────────── */
async function saveIP() {
  const ip  = document.getElementById('ipInput').value.trim();
  const msg = document.getElementById('ipSaveMsg');
  if (!ip) { msg.innerHTML = '<span style="color:#f87171">Enter an IP address.</span>'; return; }
  try {
    await fetch('/set_ip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip }),
    });
    msg.innerHTML = `<span style="color:#00e5a0">✓ IP saved: ${ip}</span>`;
    pushActivity(`IP updated → <strong>${ip}</strong>`, '#4d9fff');
    loadData();
    setTimeout(() => { msg.textContent = ''; }, 4000);
  } catch (e) {
    msg.innerHTML = '<span style="color:#f87171">✗ Failed.</span>';
  }
}

/* ── Max Players Save ─────────────────────────────────── */
async function saveMaxPlayers() {
  const input = document.getElementById('maxPlayersInput');
  const msg   = document.getElementById('maxPlayersSaveMsg');
  const val   = parseInt(input.value.trim(), 10);
  if (!val || val < 1) { msg.innerHTML = '<span style="color:#f87171">Enter a valid number.</span>'; return; }
  try {
    await fetch('/set_max_players', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_players: val }),
    });
    msg.innerHTML = `<span style="color:#00e5a0">✓ Max players set to ${val}</span>`;
    delete input.dataset.userEdited;
    pushActivity(`Max players → <strong>${val}</strong>`, '#22d3ee');
    loadData();
    setTimeout(() => { msg.textContent = ''; }, 4000);
  } catch (e) {
    msg.innerHTML = '<span style="color:#f87171">✗ Failed.</span>';
  }
}

/* ── Console ──────────────────────────────────────────── */
async function loadConsole() {
  try {
    const res  = await fetch('/console');
    if (res.status === 401) return;
    const data = await res.json();
    const el   = document.getElementById('console');
    if (data.logs && data.logs !== el.textContent) {
      el.textContent = data.logs || 'No logs yet.';
      const t = el.parentElement;
      t.scrollTop = t.scrollHeight;
    }
  } catch (e) {}
}

async function clearConsole() {
  try {
    await fetch('/console/clear', { method: 'POST' });
    document.getElementById('console').textContent = 'Console cleared.';
    pushActivity('Console cleared.', '#fb923c');
  } catch (e) {}
}

/* ── AI Chat ──────────────────────────────────────────── */
async function askAI() {
  const input = document.getElementById('ai_input');
  const q     = input.value.trim();
  if (!q) return;

  const win = document.getElementById('chatWindow');
  win.insertAdjacentHTML('beforeend', `
    <div class="chat-msg user">
      <span class="msg-avatar">🧑</span>
      <div class="msg-bubble">${escapeHtml(q)}</div>
    </div>
  `);
  input.value = '';
  win.scrollTop = win.scrollHeight;

  const typingId = 'typing-' + Date.now();
  win.insertAdjacentHTML('beforeend', `
    <div class="chat-msg bot" id="${typingId}">
      <span class="msg-avatar">🤖</span>
      <div class="msg-bubble" style="color:var(--muted)">Thinking...</div>
    </div>
  `);
  win.scrollTop = win.scrollHeight;

  try {
    const res  = await fetch('/ai', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q }),
    });
    const data = await res.json();
    const typing = document.getElementById(typingId);
    if (typing) {
      typing.querySelector('.msg-bubble').innerHTML =
        (data.reply || 'No response.')
          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/\n/g, '<br>');
    }
  } catch (e) {
    const typing = document.getElementById(typingId);
    if (typing) typing.querySelector('.msg-bubble').textContent = 'Error reaching AI.';
  }
  win.scrollTop = win.scrollHeight;
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/* ── Init ─────────────────────────────────────────────── */
loadMe();
loadData();
loadConsole();
setInterval(loadData,    3000);
setInterval(loadConsole, 2000);
