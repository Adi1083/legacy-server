/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Core API Client: Authoritative Local HTTP Transport & Error Normalizer
 *
 * Strict Local Architecture:
 * - Authoritative local backend: http://127.0.0.1:8080
 * - Prefer same-origin relative paths when hosted on server.py
 * - Strictly zero traffic permitted to legacy Render cloud URLs
 */

const LOCAL_BACKEND_ORIGIN = 'http://127.0.0.1:8080';
const BLOCKED_REMOTE_ORIGINS = [
  'https://legacy-server-1mkj.onrender.com',
  'http://legacy-server-1mkj.onrender.com',
  'legacy-server-1mkj.onrender.com',
  'onrender.com'
];

class ApiClient {
  constructor() {
    // Determine base URL:
    // If served from local server.py (port 8080), use relative paths '' to avoid unnecessary CORS/preflight.
    // If opened via file:// or another dev host/port, explicitly target http://127.0.0.1:8080.
    const isSameOriginLocal = (typeof window !== 'undefined' && window.location)
      && (window.location.protocol === 'http:' || window.location.protocol === 'https:')
      && (window.location.port === '8080' || window.location.host === '127.0.0.1:8080' || window.location.host === 'localhost:8080');

    this.baseUrl = isSameOriginLocal ? '' : LOCAL_BACKEND_ORIGIN;
    this.localBackendUrl = LOCAL_BACKEND_ORIGIN;
    this.adminToken = (typeof localStorage !== 'undefined') ? (localStorage.getItem('ind_admin_token') || '') : '';
    this.listeners = new Set();
  }

  setToken(token) {
    this.adminToken = token || '';
    if (typeof localStorage !== 'undefined') {
      if (token) {
        localStorage.setItem('ind_admin_token', token);
      } else {
        localStorage.removeItem('ind_admin_token');
      }
    }
  }

  getToken() {
    return this.adminToken;
  }

  onActivity(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  _notify(entry) {
    for (const cb of this.listeners) {
      try { cb(entry); } catch (e) { console.error('API log error', e); }
    }
  }

  _getHeaders(isUpload = false) {
    const headers = {};
    if (!isUpload) {
      headers['Content-Type'] = 'application/json';
    }
    if (this.adminToken) {
      headers['Authorization'] = `Bearer ${this.adminToken}`;
      headers['X-Admin-Token'] = this.adminToken;
    }
    return headers;
  }

  async _request(method, endpoint, body = null, isUpload = false) {
    const start = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();

    // Security audit: Hard block any attempt to contact Render or remote legacy servers
    for (const blocked of BLOCKED_REMOTE_ORIGINS) {
      if (typeof endpoint === 'string' && endpoint.includes(blocked)) {
        console.error(`[API Security Block] Forbidden remote request to Render blocked: ${endpoint}`);
        const errResult = {
          ok: false,
          status: 403,
          data: null,
          error: `Forbidden: Remote Render backend (${blocked}) is disabled. Use local backend at ${LOCAL_BACKEND_ORIGIN}.`
        };
        this._notify({
          timestamp: new Date().toLocaleTimeString(),
          method,
          url: endpoint,
          status: 403,
          duration: 0,
          ok: false,
          error: errResult.error
        });
        return errResult;
      }
    }

    const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
    const options = {
      method,
      headers: this._getHeaders(isUpload)
    };

    if (body) {
      options.body = isUpload ? body : JSON.stringify(body);
    }

    try {
      const response = await fetch(url, options);
      const duration = Math.round(((typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()) - start);
      let data = null;
      const contentType = response.headers.get('content-type') || '';

      if (contentType.includes('application/json')) {
        try {
          data = await response.json();
        } catch (e) {
          data = { error: 'Invalid JSON payload returned' };
        }
      } else {
        const text = await response.text();
        data = { raw: text };
      }

      const isOk = response.ok && (data && data.ok !== false);
      const result = {
        ok: isOk,
        status: response.status,
        data: data,
        error: !isOk ? (data && (data.error || data.msg || data.message)) || `HTTP ${response.status}` : null
      };

      this._notify({
        timestamp: new Date().toLocaleTimeString(),
        method,
        url: endpoint,
        status: response.status,
        duration,
        ok: isOk
      });

      return result;
    } catch (err) {
      const duration = Math.round(((typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now()) - start);
      const isConnectionRefused = err.message && (
        err.message.includes('Failed to fetch') ||
        err.message.includes('NetworkError') ||
        err.message.includes('Network unreachable') ||
        err.message.includes('ECONNREFUSED')
      );
      const errorMsg = isConnectionRefused
        ? `Local backend unreachable at ${LOCAL_BACKEND_ORIGIN}. Verify python server.py is running on port 8080.`
        : (err.message || 'Network unreachable');

      const result = {
        ok: false,
        status: 0,
        data: null,
        error: errorMsg
      };

      this._notify({
        timestamp: new Date().toLocaleTimeString(),
        method,
        url: endpoint,
        status: 0,
        duration,
        ok: false,
        error: result.error
      });

      return result;
    }
  }

  async get(endpoint, params = null) {
    let url = endpoint;
    if (params) {
      const sp = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null && v !== '') {
          sp.append(k, v);
        }
      }
      const qs = sp.toString();
      if (qs) url += (url.includes('?') ? '&' : '?') + qs;
    }
    return this._request('GET', url);
  }

  async post(endpoint, body = {}) {
    return this._request('POST', endpoint, body);
  }

  async put(endpoint, body = {}) {
    return this._request('PUT', endpoint, body);
  }

  async delete(endpoint, body = null) {
    return this._request('DELETE', endpoint, body);
  }

  async upload(endpoint, formData) {
    return this._request('POST', endpoint, formData, true);
  }
}

// Global Singleton Export
if (typeof window !== 'undefined') {
  window.apiClient = new ApiClient();
} else if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ApiClient, LOCAL_BACKEND_ORIGIN };
}
