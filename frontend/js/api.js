/**
 * frontend/js/api.js
 * REST API Client for Tawbah Guiden (Islamisk Opgørelse & Anger App)
 */

const TOKEN_STORAGE_KEY = 'tawbah_auth_token';
const USER_STORAGE_KEY = 'tawbah_auth_user';

export const ApiClient = {
  getToken() {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || '';
  },

  getUser() {
    try {
      const raw = localStorage.getItem(USER_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  setSession(token, username, userId) {
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token);
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ username, userId }));
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem(USER_STORAGE_KEY);
    }
  },

  _headers(isJson = true) {
    const headers = {};
    if (isJson) {
      headers['Content-Type'] = 'application/json';
    }
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  },

  async request(path, options = {}) {
    const res = await fetch(path, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `Fejl ved kald til ${path} (HTTP ${res.status})`);
    }
    return data;
  },

  async register(username, password) {
    const data = await this.request('/api/auth/register', {
      method: 'POST',
      headers: this._headers(true),
      body: JSON.stringify({ username, password }),
    });
    if (data.access_token) {
      this.setSession(data.access_token, data.username || username, data.user_id);
    }
    return data;
  },

  async login(username, password) {
    const data = await this.request('/api/auth/login', {
      method: 'POST',
      headers: this._headers(true),
      body: JSON.stringify({ username, password }),
    });
    if (data.access_token) {
      this.setSession(data.access_token, data.username || username, data.user_id);
    }
    return data;
  },

  logout() {
    this.setSession('', '', '');
  },

  async submitTextConfession(text, consent) {
    return this.request('/api/confessions/text', {
      method: 'POST',
      headers: this._headers(true),
      body: JSON.stringify({ text, consent: Boolean(consent) }),
    });
  },

  async submitVoiceConfession(audioBlob, filename, consent, transcriptHint = '') {
    const formData = new FormData();
    formData.append('audio', audioBlob, filename || 'confession.webm');
    formData.append('consent', consent ? 'true' : 'false');
    if (transcriptHint && transcriptHint.trim()) {
      formData.append('transcript_hint', transcriptHint.trim());
    }
    return this.request('/api/confessions/voice', {
      method: 'POST',
      headers: this._headers(false),
      body: formData,
    });
  },

  async getConfessions() {
    return this.request('/api/confessions', {
      method: 'GET',
      headers: this._headers(false),
    });
  },

  async getConfessionById(confessionId) {
    return this.request(`/api/confessions/${encodeURIComponent(confessionId)}`, {
      method: 'GET',
      headers: this._headers(false),
    });
  },

  async deleteConfession(confessionId) {
    return this.request(`/api/confessions/${encodeURIComponent(confessionId)}`, {
      method: 'DELETE',
      headers: this._headers(false),
    });
  },

  async getActions() {
    return this.request('/api/actions', {
      method: 'GET',
      headers: this._headers(false),
    });
  },

  async toggleAction(actionId, completed) {
    return this.request(`/api/actions/${encodeURIComponent(actionId)}`, {
      method: 'PATCH',
      headers: this._headers(true),
      body: JSON.stringify({ completed: Boolean(completed) }),
    });
  },

  async getJournal() {
    return this.request('/api/journal', {
      method: 'GET',
      headers: this._headers(false),
    });
  },

  async createJournalEntry(title, reflection, tags = []) {
    return this.request('/api/journal', {
      method: 'POST',
      headers: this._headers(true),
      body: JSON.stringify({ title, reflection, tags }),
    });
  },

  async deleteJournalEntry(entryId) {
    return this.request(`/api/journal/${encodeURIComponent(entryId)}`, {
      method: 'DELETE',
      headers: this._headers(false),
    });
  },

  async getDashboardSummary() {
    return this.request('/api/dashboard/summary', {
      method: 'GET',
      headers: this._headers(false),
    });
  },

  async getKnowledgeBase(query = '', category = '') {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (category) params.set('category', category);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request(`/api/knowledge${qs}`, {
      method: 'GET',
      headers: this._headers(false),
    });
  },

  async wipeAccountData() {
    return this.request('/api/account/wipe', {
      method: 'POST',
      headers: this._headers(true),
    });
  },
};
