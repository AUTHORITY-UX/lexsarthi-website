/* api.js — single gateway for every backend call.
   Every endpoint call goes through this wrapper so failures are logged
   centrally and never break the UI.
*/

const API = {
  base: '',

  async get(path) {
    const url = this.base + path;
    const t0 = performance.now();
    try {
      const r = await fetch(url, { method: 'GET' });
      const ms = Math.round(performance.now() - t0);
      if (!r.ok) {
        console.warn(`[api] GET ${path} → ${r.status} (${ms}ms)`);
        return { ok: false, status: r.status, error: `HTTP ${r.status}`, ms };
      }
      const data = await r.json();
      console.log(`[api] GET ${path} → 200 (${ms}ms)`);
      return { ok: true, data, ms };
    } catch (e) {
      console.warn(`[api] GET ${path} → ${e.message}`);
      return { ok: false, error: e.message };
    }
  },

  async post(path, body) {
    const url = this.base + path;
    const t0 = performance.now();
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const ms = Math.round(performance.now() - t0);
      if (!r.ok) {
        console.warn(`[api] POST ${path} → ${r.status} (${ms}ms)`);
        return { ok: false, status: r.status, error: `HTTP ${r.status}`, ms };
      }
      const data = await r.json();
      console.log(`[api] POST ${path} → 200 (${ms}ms)`);
      return { ok: true, data, ms };
    } catch (e) {
      console.warn(`[api] POST ${path} → ${e.message}`);
      return { ok: false, error: e.message };
    }
  },
};

window.API = API;
