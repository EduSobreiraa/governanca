const $ = id => document.getElementById(id);
async function send(message) {
  const result = await chrome.runtime.sendMessage(message);
  if (!result?.ok) throw new Error(result?.error || 'Sem resposta da extensão.');
  return result.data;
}
async function refresh() {
  const config = await send({type: 'status'});
  $('enabled').checked = config.enabled;
  $('captures').textContent = config.lastCaptures.length
    ? config.lastCaptures.slice().reverse().map(item => `${item.observed_at}  ${item.status}  ${item.bytes} B  ${item.frames} frames`).join('\n')
    : 'Nenhuma captura ainda.';
  $('diagnostics').textContent = config.captureDiagnostics.length
    ? config.captureDiagnostics.slice().reverse().map(item => `${item.at}  ${item.stage}  ${JSON.stringify(Object.fromEntries(Object.entries(item).filter(([key]) => !['at', 'stage'].includes(key))))}`).join('\n')
    : 'Sem eventos. Envie uma resposta sintética com a captura ativada.';
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  if (!tab?.id) { $('probe-status').textContent = 'Nenhuma aba ativa.'; return; }
  try {
    const probe = await chrome.tabs.sendMessage(tab.id, {type: 'probe_status'});
    $('probe-status').textContent = probe?.active ? `Ativa (adapter ${probe.adapterVersion}).` : 'Sonda não respondeu.';
  } catch {
    $('probe-status').textContent = 'Sonda não carregada nesta aba. Recarregue a aba do ChatGPT após recarregar a extensão.';
  }
}
$('config').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    await send({type: 'save', token: $('token').value, enabled: $('enabled').checked});
    $('token').value = '';
    $('status').textContent = 'Configuração salva. Recarregue a aba do ChatGPT.';
    await refresh();
  } catch (error) { $('status').textContent = error.message; }
});
$('health').addEventListener('click', async () => {
  try { const data = await send({type: 'health'}); $('status').textContent = `API local acessível (SQLite ${data.sqlite}).`; }
  catch (error) { $('status').textContent = error.message; }
});
refresh().catch(error => { $('status').textContent = error.message; });
