/* ── Sessions Tab ──────────────────────────────────────────────────────── */

App.tabs.sessions = {
  _showArchived: false,
  _selected: new Set(),

  init() {},

  async render() {
    const panel = document.getElementById('panel-sessions');
    panel.innerHTML = '<div class="loading"><div class="spinner"></div><br>Loading sessions...</div>';

    const sessions = await App.api('/api/sessions');
    if (!Array.isArray(sessions)) {
      panel.innerHTML = '<div class="empty-state">Failed to load sessions</div>';
      return;
    }

    this._selected.clear();
    const filtered = this._showArchived ? sessions : sessions.filter(s => !s.archived);

    let html = '';

    // Controls
    html += '<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap">';
    html += `<label style="font-size:13px;color:var(--text-dim);display:flex;align-items:center;gap:6px">
      <input type="checkbox" class="checkbox" ${this._showArchived ? 'checked' : ''} onchange="App.tabs.sessions._toggleArchived(this.checked)">
      Show archived
    </label>`;
    html += `<span style="font-size:13px;color:var(--text-muted)">${filtered.length} sessions</span>`;
    html += '<div style="flex:1"></div>';
    html += '<button class="btn btn-ghost btn-sm" onclick="App.tabs.sessions._selectAll()">Select All</button>';
    html += '<button class="btn btn-ghost btn-sm" onclick="App.tabs.sessions._selectNone()">Deselect All</button>';
    html += '<button class="btn btn-danger btn-sm" id="sessions-delete-btn" disabled onclick="App.tabs.sessions._confirmDelete()">Delete Selected</button>';
    html += '</div>';

    if (!filtered.length) {
      html += '<div class="empty-state">No sessions found</div>';
      panel.innerHTML = html;
      return;
    }

    // Table
    html += '<div class="table-wrap"><table>';
    html += '<tr><th style="width:30px"></th><th>Title</th><th>Created</th><th>Last Activity</th><th>Status</th></tr>';

    for (const s of filtered) {
      const title = s.title || s.id;
      const truncTitle = title.length > 60 ? title.slice(0, 60) + '...' : title;
      html += `<tr>
        <td><input type="checkbox" class="checkbox" data-sid="${s.id}" onchange="App.tabs.sessions._onCheck()"></td>
        <td title="${this._esc(title)}">${this._esc(truncTitle)}</td>
        <td style="white-space:nowrap">${App.fmtDateTime(s.created)}</td>
        <td style="white-space:nowrap">${App.timeAgo(s.lastActivity)}</td>
        <td><span class="card-badge ${s.archived ? 'badge-dim' : 'badge-green'}">${s.archived ? 'Archived' : 'Active'}</span></td>
      </tr>`;
    }

    html += '</table></div>';
    panel.innerHTML = html;
  },

  _toggleArchived(show) {
    this._showArchived = show;
    this.render();
  },

  _onCheck() {
    this._selected.clear();
    document.querySelectorAll('#panel-sessions .checkbox[data-sid]').forEach(cb => {
      if (cb.checked) this._selected.add(cb.dataset.sid);
    });
    const btn = document.getElementById('sessions-delete-btn');
    if (btn) btn.disabled = this._selected.size === 0;
  },

  _selectAll() {
    document.querySelectorAll('#panel-sessions .checkbox[data-sid]').forEach(cb => {
      cb.checked = true;
    });
    this._onCheck();
  },

  _selectNone() {
    document.querySelectorAll('#panel-sessions .checkbox[data-sid]').forEach(cb => {
      cb.checked = false;
    });
    this._onCheck();
  },

  _confirmDelete() {
    const count = this._selected.size;
    if (!count) return;
    App.modal(
      'Delete Sessions',
      `<p>Are you sure you want to delete <strong>${count}</strong> session${count > 1 ? 's' : ''}?</p><p style="color:var(--red)">This cannot be undone.</p>`,
      [
        { label: 'Cancel', class: 'btn-ghost' },
        { label: `Delete ${count}`, class: 'btn-danger', action: () => this._doDelete() },
      ]
    );
  },

  async _doDelete() {
    const ids = [...this._selected];
    const result = await App.api('/api/sessions/delete', { ids });
    if (result.ok) {
      App.toast(`Deleted ${result.deleted} session(s)`, 'success');
      this.render();
    } else {
      App.toast('Failed to delete sessions', 'error');
    }
  },

  _esc(s) {
    const el = document.createElement('span');
    el.textContent = s || '';
    return el.innerHTML;
  },
};
