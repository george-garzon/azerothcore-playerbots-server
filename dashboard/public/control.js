const $ = id => document.getElementById(id);
const endpoint = path => location.port === '8765' ? '/api/' + path : '/control.php?path=' + encodeURIComponent(path);
let token, initialized = false, busy = false;
async function api(path, body) {
  const response = await fetch(endpoint(path), {cache:'no-store', ...(body ? {method:'POST', headers:{'Content-Type':'application/json','X-Control-Token':token},body:JSON.stringify(body)} : {})});
  const data = await response.json();
  if (!response.ok) { if (response.status === 403) token = null; throw Error(data.error || 'Request failed'); }
  return data;
}
function lock(value) { busy = value; document.querySelectorAll('button').forEach(b => b.disabled = value); }
async function act(action, settings) {
  if (busy) return;
  try {
    lock(true);
    if (!token) token = (await api('session')).token;
    await api('action', {action, countdown:Number($('countdown').value), ...(settings ? {settings} : {})});
    $('notice').textContent = 'Operation accepted. Follow its progress below.';
  } catch (error) { $('notice').textContent = error.message; lock(false); }
}
document.querySelectorAll('[data-action]').forEach(b => b.onclick = () => act(b.dataset.action));
$('settings').onsubmit = event => {
  event.preventDefault();
  if ($('settings').reportValidity()) act(event.submitter.value, Object.fromEntries(new FormData($('settings'))));
};
let sourceLevel = 13;
function showBotRange() {
  const form = $('bot-levels');
  const follow = form.elements.BOT_LEVEL_MODE.value === 'follow';
  const low = form.elements.BOT_LEVEL_MIN;
  const high = form.elements.BOT_LEVEL_MAX;
  low.readOnly = high.readOnly = follow;
  high.setCustomValidity(!follow && Number(low.value) > Number(high.value) ? 'Maximum must be at least the minimum.' : '');
  $('bot-level-summary').textContent = follow
    ? `Daily range: 1–${Math.min(80, sourceLevel + 10)}. Last checked Magic level: ${sourceLevel}. Manual fields are unused in this mode.`
    : `Manual range: ${low.value}–${high.value}. Daily following is paused while manual mode is saved.`;
}
$('bot-levels').oninput = showBotRange;
$('bot-levels').onsubmit = event => {
  event.preventDefault();
  showBotRange();
  if ($('bot-levels').reportValidity()) act(event.submitter.value, Object.fromEntries(new FormData($('bot-levels'))));
};
async function refresh() {
  try {
    const data = await api('status');
    if (!token) token = (await api('session')).token;
    if (!initialized) {
      for (const [key,value] of Object.entries(data.settings)) $('settings').elements.namedItem(key).value = value;
      for (const [key,value] of Object.entries(data.bot_levels || {})) $('bot-levels').elements.namedItem(key).value = value;
      initialized = true;
    }
    sourceLevel = Number(data.bot_level_source || 13);
    showBotRange();
    $('realm').textContent = data.realm || 'Unknown';
    $('address').textContent = data.realm_address || 'Database unavailable';
    $('population').textContent = data.online == null ? 'Unknown' : `${data.online} online · ${data.bots} bots`;
    const models = data.ollama?.models || [];
    const bytes = models.reduce((sum,m) => sum + m.vram, 0);
    $('gpu').textContent = data.ollama?.online ? (data.gpu_utilization == null ? 'GPU load unavailable' : data.gpu_utilization + '% engine load') : 'Ollama stopped';
    $('vram').textContent = models.length ? `${(bytes/1073741824).toFixed(2)} GB model VRAM · ${models.map(m=>m.name).join(', ')}` : 'No model loaded';
    $('latency').textContent = data.probe ? `${data.probe.seconds}s / ${data.probe.tokens} tokens` : 'Not measured';
    $('api-latency').textContent = `API ping: ${data.ollama?.api_ms ?? '—'} ms · last test reply, not all chat`;
    const job = data.job;
    lock(job?.status === 'running');
    $('job').textContent = job ? `${job.action}: ${job.status} — ${job.message}${job.remaining != null ? ' (' + job.remaining + 's)' : ''}` : 'No operation running.';
    $('notice').textContent = busy ? 'Operation in progress; other controls are locked.' : 'Local controller connected.';
    $('services').textContent = (data.services || []).map(s=>`${s.name}: ${s.state}`).join(' · ');
    $('errors').textContent = [...(data.errors || []), ...(data.recent_errors || [])].join('\n') || 'No errors in the current sample / recent log window.';
    $('events').replaceChildren(...[...(data.events || [])].reverse().map(e => { const p=document.createElement('div'); p.textContent=`${e.time} ${e.message}`; return p; }));
    $('updated').textContent = data.sampled_at ? `Last sample: ${new Date(data.sampled_at*1000).toLocaleTimeString()} · bot count uses Playerbots account classifications (personal alt bots may count as other characters).` : 'First sample pending';
  } catch (error) { $('notice').textContent = error.message + ' · Standalone controls: http://127.0.0.1:8765'; lock(true); }
}
async function refreshLogs() {
  if ($('pause-logs').checked) return;
  try { $('logs').textContent = (await api('logs/' + $('log-source').value)).text; $('logs').scrollTop = $('logs').scrollHeight; }
  catch (error) { $('logs').textContent = error.message; }
}
$('log-source').onchange=refreshLogs;
refresh(); refreshLogs();
setInterval(refresh, 2000); setInterval(refreshLogs, 5000);
