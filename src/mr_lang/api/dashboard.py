"""Inline HTML dashboard for observability — no build step required."""

DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mr-lang Dashboard</title>
<style>
  :root { --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #c9d1d9;
          --muted: #8b949e; --accent: #58a6ff; --green: #3fb950; --yellow: #d29922;
          --red: #f85149; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: var(--bg); color: var(--text); padding: 24px; }
  h1 { color: var(--accent); margin-bottom: 24px; font-size: 1.5rem; }
  h2 { color: var(--text); margin: 24px 0 12px; font-size: 1.1rem; }
  .stats { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
  .stat { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
          padding: 16px 20px; min-width: 140px; }
  .stat-value { font-size: 1.8rem; font-weight: bold; color: var(--accent); }
  .stat-label { color: var(--muted); font-size: 0.85rem; margin-top: 4px; }
  table { width: 100%; border-collapse: collapse; background: var(--card);
          border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
  th { background: #1c2128; text-align: left; padding: 10px 14px; color: var(--muted);
       font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; }
  td { padding: 10px 14px; border-top: 1px solid var(--border); font-size: 0.9rem; }
  tr:hover td { background: #1c2128; }
  .clickable { cursor: pointer; color: var(--accent); }
  .clickable:hover { text-decoration: underline; }
  .badge { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
  .badge-start { background: #0d419d; color: #58a6ff; }
  .badge-end { background: #0c3214; color: #3fb950; }
  .badge-error { background: #490202; color: #f85149; }
  .badge-tool { background: #3d2004; color: #d29922; }
  .badge-model { background: #272048; color: #bc8cff; }
  #detail { display: none; }
  .back { color: var(--accent); cursor: pointer; margin-bottom: 12px; display: inline-block; }
  .back:hover { text-decoration: underline; }
  .loading { color: var(--muted); padding: 40px; text-align: center; }
  .refresh { float: right; background: var(--card); border: 1px solid var(--border);
             color: var(--accent); padding: 6px 14px; border-radius: 6px; cursor: pointer; }
  .refresh:hover { background: #1c2128; }
</style>
</head>
<body>
<h1>mr-lang Dashboard <button class="refresh" onclick="loadSessions()">Refresh</button></h1>

<div id="overview">
  <div class="stats" id="global-stats"></div>
  <table>
    <thead><tr><th>Session ID</th><th>Events</th><th>First</th><th>Last</th></tr></thead>
    <tbody id="sessions-body"><tr><td colspan="4" class="loading">Loading...</td></tr></tbody>
  </table>
</div>

<div id="detail">
  <span class="back" onclick="showOverview()">&larr; Back to sessions</span>
  <h2 id="detail-title"></h2>
  <div class="stats" id="detail-stats"></div>
  <table>
    <thead><tr><th>Timestamp</th><th>Type</th><th>Data</th></tr></thead>
    <tbody id="events-body"></tbody>
  </table>
</div>

<script>
const API = '';

function badgeClass(type) {
  if (type.includes('start')) return 'badge-start';
  if (type.includes('end')) return 'badge-end';
  if (type.includes('error')) return 'badge-error';
  if (type.includes('tool')) return 'badge-tool';
  return 'badge-model';
}

async function loadSessions() {
  const resp = await fetch(API + '/api/sessions');
  const data = await resp.json();
  const sessions = data.sessions || [];
  const tbody = document.getElementById('sessions-body');

  if (!sessions.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="loading">No sessions recorded yet.</td></tr>';
    document.getElementById('global-stats').innerHTML = '';
    return;
  }

  const totalEvents = sessions.reduce((s, x) => s + x.event_count, 0);
  document.getElementById('global-stats').innerHTML =
    stat(sessions.length, 'Sessions') + stat(totalEvents, 'Total Events');

  tbody.innerHTML = sessions.map(s =>
    `<tr>
      <td class="clickable" onclick="loadSession('${s.session_id}')">${s.session_id}</td>
      <td>${s.event_count}</td>
      <td>${fmtTime(s.first_event)}</td>
      <td>${fmtTime(s.last_event)}</td>
    </tr>`
  ).join('');
}

async function loadSession(id) {
  document.getElementById('overview').style.display = 'none';
  document.getElementById('detail').style.display = 'block';
  document.getElementById('detail-title').textContent = 'Session: ' + id;
  document.getElementById('events-body').innerHTML =
    '<tr><td colspan="3" class="loading">Loading...</td></tr>';

  const resp = await fetch(API + '/api/sessions/' + id);
  const data = await resp.json();
  const st = data.stats;

  document.getElementById('detail-stats').innerHTML =
    stat(st.model_calls_count, 'Model Calls') +
    stat(st.tool_calls_count, 'Tool Calls') +
    stat(st.total_tokens, 'Tokens') +
    stat(st.total_duration_ms.toFixed(0) + 'ms', 'Duration') +
    stat(st.errors_count, 'Errors');

  document.getElementById('events-body').innerHTML = data.events.map(e =>
    `<tr>
      <td>${fmtTime(e.timestamp)}</td>
      <td><span class="badge ${badgeClass(e.event_type)}">${e.event_type}</span></td>
      <td>${JSON.stringify(e.data).substring(0, 120)}</td>
    </tr>`
  ).join('');
}

function showOverview() {
  document.getElementById('detail').style.display = 'none';
  document.getElementById('overview').style.display = 'block';
}

function stat(value, label) {
  return `<div class="stat"><div class="stat-value">${value}</div>` +
         `<div class="stat-label">${label}</div></div>`;
}

function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString();
}

loadSessions();
</script>
</body>
</html>
"""
