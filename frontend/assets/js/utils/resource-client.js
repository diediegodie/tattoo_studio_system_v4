(function (window) {
  'use strict';

  // Generic resource client factory
  // Usage: const client = makeResourceClient('/inventory');
  // Methods: getAll(), get(id), create(payload), update(id, payload), delete(id)
  function makeResourceClient(basePath) {
    if (!basePath) throw new Error('makeResourceClient: basePath is required');

    // Normalize base path (no trailing slash)
    const base = basePath.replace(/\/+$|\s+$/g, '').replace(/\s+/g, '');

    function callShowStatus(message, isSuccess = false) {
      if (typeof window.showStatus === 'function') {
        try {
          window.showStatus(message, isSuccess);
        } catch (e) {
          // swallow showStatus errors but log for debugging
          console.error('showStatus threw:', e);
        }
      }
    }

    async function handleResponse(response) {
      const contentType = response.headers.get('Content-Type') || '';
      let payload = null;

      if (contentType.includes('application/json')) {
        payload = await response.json();
      } else {
        payload = await response.text();
      }

      if (!response.ok) {
        const message = (payload && payload.message) || response.statusText || 'Request failed';
        callShowStatus(message, false);
        const err = new Error(message);
        err.status = response.status;
        err.payload = payload;
        throw err;
      }

      return payload;
    }

    function handleError(err) {
      const message = (err && err.message) || 'Network error';
      callShowStatus(message, false);
      console.error('ResourceClient error:', err);
      throw err;
    }

    function buildUrl(path = '') {
      // allow passing '/:id' or 'id'
      if (!path) return base;
      const trimmed = String(path).replace(/^\/+/, '');
      return base + (base.endsWith('/') ? '' : '/') + trimmed;
    }

    async function getAll() {
      try {
        const res = await fetch(buildUrl(), { headers: { 'Accept': 'application/json' } });
        return handleResponse(res);
      } catch (err) {
        return handleError(err);
      }
    }

    async function get(id) {
      if (typeof id === 'undefined' || id === null) throw new Error('get(id) requires id');
      try {
        const res = await fetch(buildUrl(String(id)), { headers: { 'Accept': 'application/json' } });
        return handleResponse(res);
      } catch (err) {
        return handleError(err);
      }
    }

    async function create(payload) {
      try {
        const res = await fetch(buildUrl(), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(payload),
        });
        return handleResponse(res);
      } catch (err) {
        return handleError(err);
      }
    }

    async function update(id, payload) {
      if (typeof id === 'undefined' || id === null) throw new Error('update(id, payload) requires id');
      try {
        const res = await fetch(buildUrl(String(id)), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify(payload),
        });
        return handleResponse(res);
      } catch (err) {
        return handleError(err);
      }
    }

    async function del(id) {
      if (typeof id === 'undefined' || id === null) throw new Error('delete(id) requires id');
      try {
        const res = await fetch(buildUrl(String(id)), { method: 'DELETE', headers: { 'Accept': 'application/json' } });
        return handleResponse(res);
      } catch (err) {
        return handleError(err);
      }
    }

    return {
      getAll,
      get,
      create,
      update,
      delete: del,
    };
  }

  // Expose factory globally so existing non-module code can consume it
  if (typeof window !== 'undefined') {
    window.makeResourceClient = makeResourceClient;
  }

  // Also support CommonJS / AMD in case the project uses bundlers (non-intrusive)
  try {
    if (typeof module !== 'undefined' && module.exports) module.exports.makeResourceClient = makeResourceClient;
  } catch (e) {
    // ignore
  }
})(typeof window !== 'undefined' ? window : this);
