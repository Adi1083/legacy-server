/**
 * IND PROJECT Control Center — FF 2019 Restoration
 * Centralized Player Context: Global Account State Manager
 */

class PlayerContext {
  constructor() {
    const saved = localStorage.getItem('ind_selected_account_id');
    this.selectedAccountId = saved ? parseInt(saved, 10) : 10001;
    this.playerData = null;
    this.isLoading = false;
    this.error = null;
    this.subscribers = new Set();
  }

  getSelectedAccountId() {
    return this.selectedAccountId;
  }

  getCurrentPlayer() {
    return this.playerData;
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    // Trigger immediately with current state
    if (this.playerData) {
      try { callback(this.selectedAccountId, this.playerData, this.isLoading); } catch (e) { console.error(e); }
    }
    return () => this.subscribers.delete(callback);
  }

  _notify() {
    for (const cb of this.subscribers) {
      try {
        cb(this.selectedAccountId, this.playerData, this.isLoading, this.error);
      } catch (err) {
        console.error('PlayerContext subscriber error:', err);
      }
    }
  }

  async setAccountId(accountId) {
    const aid = parseInt(accountId, 10);
    if (!aid || isNaN(aid)) return;

    this.selectedAccountId = aid;
    localStorage.setItem('ind_selected_account_id', aid.toString());
    await this.refresh();
  }

  async refresh() {
    this.isLoading = true;
    this.error = null;
    this._notify();

    try {
      const res = await window.apiClient.get('/api/dashboard/state', { account_id: this.selectedAccountId });
      if (res.ok && res.data) {
        this.playerData = res.data;
        this.error = null;
      } else {
        this.error = res.error || 'Failed to load player state';
      }
    } catch (e) {
      this.error = e.message;
    } finally {
      this.isLoading = false;
      this._notify();
    }
  }
}

// Global Singleton Export
window.playerContext = new PlayerContext();
