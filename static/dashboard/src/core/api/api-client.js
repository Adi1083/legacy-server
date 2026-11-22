/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Core API Client: Centralized HTTP Transport & Error Normalizer
 */

class ApiClient {
  constructor() {
    this.baseUrl = '';
    this.adminToken = localStorage.getItem('ind_admin_token') || '';
    this.listeners = new Set();
  }

  setToken(token) {
    this.adminToken = token || '';
    if (token) {
      localStorage.setItem('ind_admin_token', token);
    } else {
      localStorage.removeItem('ind_admin_token');
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
    const start = performance.now();
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
      const duration = Math.round(performance.now() - start);
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
      const duration = Math.round(performance.now() - start);
      const result = {
        ok: false,
        status: 0,
        data: null,
        error: err.message || 'Network unreachable'
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
window.apiClient = new ApiClient();
