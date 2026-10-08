const API = 'http://127.0.0.1:8766';
const CHATGPT_ORIGIN = 'https://chatgpt.com';

async function sendToApi(path, options = {}) {
  const {token = ''} = await chrome.storage.session.get('token');
  const response = await fetch(`${API}${path}`, {
    ...options,
    signal: AbortSignal.timeout(10_000),
    headers: {'Content-Type': 'application/json', ...(token ? {Authorization: `Bearer ${token}`} : {}), ...options.headers}
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`HTTP ${response.status}${data.detail ? `: ${data.detail}` : ''}`);
  return data;
}

async function status() {
  const config = await chrome.storage.local.get(['enabled', 'lastCaptures', 'captureDiagnostics']);
  const {token = ''} = await chrome.storage.session.get('token');
  return {enabled: config.enabled === true, configured: Boolean(token), lastCaptures: config.lastCaptures || [],
    captureDiagnostics: config.captureDiagnostics || []};
}

async function recordDiagnostic(stage, details = {}) {
  const {captureDiagnostics = []} = await chrome.storage.local.get('captureDiagnostics');
  captureDiagnostics.push({stage, at: new Date().toISOString(), ...details});
  await chrome.storage.local.set({captureDiagnostics: captureDiagnostics.slice(-30)});
}

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  (async () => {
    const popup = sender.url === chrome.runtime.getURL('src/popup/popup.html');
    const page = sender.tab && sender.frameId === 0 && (() => {
      try { return new URL(sender.url).origin === CHATGPT_ORIGIN; } catch { return false; }
    })();

    if (popup && message.type === 'status') return status();
    if (popup && message.type === 'save') {
      if (typeof message.token !== 'string') throw new Error('Token inválido.');
      const suppliedToken = message.token.trim();
      const {token: currentToken = ''} = await chrome.storage.session.get('token');
      if (suppliedToken && suppliedToken.length < 24) throw new Error('O token precisa ter pelo menos 24 caracteres.');
      if (message.enabled === true && !suppliedToken && !currentToken)
        throw new Error('Informe o LAB_API_TOKEN do arquivo .env (mínimo de 24 caracteres).');
      if (suppliedToken) await chrome.storage.session.set({token: suppliedToken});
      await chrome.storage.local.set({enabled: message.enabled === true});
      return {saved: true};
    }
    if (popup && message.type === 'health') return sendToApi('/health');

    if (page && message.type === 'stream_capture') {
      const item = message.payload;
      await recordDiagnostic('capture_received', {capture_status: item?.capture_status || 'invalid',
        frames: item?.frames ?? null, bytes: item?.bytes ?? null});
      const config = await chrome.storage.local.get('enabled');
      if (config.enabled !== true) throw new Error('Captura pausada na extensão.');
      if (!item || typeof item.capture_id !== 'string' || typeof item.response_text !== 'string' ||
          item.response_text.length > 100_000 || !['complete', 'incomplete'].includes(item.capture_status) ||
          typeof item.protocol_done !== 'boolean' || typeof item.reader_done !== 'boolean' ||
          typeof item.truncated !== 'boolean' ||
          (item.capture_status === 'complete' && (!item.protocol_done || item.truncated)) ||
          (item.capture_status === 'incomplete' && item.protocol_done))
        throw new Error('Snapshot de stream inválido.');
      let saved;
      try {
        saved = await sendToApi('/v1/stream-captures', {method: 'POST', body: JSON.stringify(item)});
      } catch (error) {
        await recordDiagnostic('api_rejected', {error: String(error?.message || 'Falha na API').slice(0, 180)});
        throw error;
      }
      const {lastCaptures = []} = await chrome.storage.local.get('lastCaptures');
      lastCaptures.push({capture_id: item.capture_id, status: saved.status, frames: item.frames, bytes: item.bytes,
        observed_at: item.observed_at});
      await chrome.storage.local.set({lastCaptures: lastCaptures.slice(-20)});
      await recordDiagnostic('sqlite_stored', {capture_status: item.capture_status, frames: item.frames, bytes: item.bytes});
      return saved;
    }
    if (page && message.type === 'probe_event') {
      const item = message.payload;
      const phases = new Set(['start', 'end', 'stream_summary', 'stream_error']);
      if (!item || !phases.has(item.phase) || item.path !== '/backend-api/f/conversation')
        throw new Error('Diagnóstico de sonda inválido.');
      const numbers = ['status', 'bytes', 'chunks', 'frames', 'done_markers', 'stream_elapsed_ms',
        'assistant_messages', 'text_part_snapshots', 'text_chars', 'delta_chars', 'patch_chars'];
      const details = Object.fromEntries(numbers.filter(key => Number.isSafeInteger(item[key]) && item[key] >= 0)
        .map(key => [key, item[key]]));
      details.method = item.method === 'POST' ? 'POST' : 'other';
      details.content_kind = ['event_stream', 'json', 'other', 'none'].includes(item.content_kind)
        ? item.content_kind : 'unknown';
      details.has_body = item.has_body === true;
      details.event_types = Array.isArray(item.event_types) ? item.event_types.slice(0, 8) : [];
      details.event_shapes = Array.isArray(item.event_shapes) ? item.event_shapes.slice(0, 8) : [];
      details.event_keys = Array.isArray(item.event_keys) ? item.event_keys.slice(0, 8) : [];
      details.patch_shapes = Array.isArray(item.patch_shapes) ? item.patch_shapes.slice(0, 8) : [];
      details.delta_shapes = Array.isArray(item.delta_shapes) ? item.delta_shapes.slice(0, 8) : [];
      if (item.error_kind) details.error_kind = String(item.error_kind).slice(0, 40);
      await recordDiagnostic(`network_${item.phase}`, details);
      return {logged: true};
    }
    throw new Error('Origem ou operação inválida.');
  })().then(data => reply({ok: true, data})).catch(error =>
    reply({ok: false, error: String(error?.message || 'Falha na POC').slice(0, 240)}));
  return true;
});
