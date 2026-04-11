/* ── Presets Tab ────────────────────────────────────────────────────────── */

App.tabs.presets = {
  init() {},

  async render() {
    const panel = document.getElementById('panel-presets');
    panel.innerHTML = '<div class="loading"><div class="spinner"></div><br>Loading presets...</div>';

    const presets = await App.api('/api/presets');
    if (!Array.isArray(presets)) {
      panel.innerHTML = '<div class="empty-state">Failed to load presets</div>';
      return;
    }

    let html = '';

    // Snapshot button
    html += '<div style="margin-bottom:16px">';
    html += '<button class="btn btn-primary" onclick="App.tabs.presets._showSnapshot()">Snapshot Current State</button>';
    html += '</div>';

    // Preset cards
    if (presets.length) {
      html += '<div class="grid grid-auto">';
      for (const p of presets) {
        const coworkCount = Object.values(p.cowork || {}).filter(v => v).length;
        const skillsGCount = Object.values(p.skills_global || {}).filter(v => v).length;
        const skillsPCount = Object.values(p.skills_project || {}).filter(v => v).length;
        const pluginCount = Object.values(p.plugins || {}).filter(v => v).length;

        html += `<div class="card" style="margin-bottom:0">
          <div style="display:flex;align-items:flex-start;gap:12px">
            <span style="font-size:28px">${p.icon || '⭐'}</span>
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                <strong style="font-size:14px">${this._esc(p.name)}</strong>
                <span class="card-badge ${p.builtin ? 'badge-dim' : 'badge-blue'}">${p.builtin ? 'Built-in' : 'Custom'}</span>
              </div>
              <div style="font-size:12px;color:var(--text-dim);margin-bottom:8px">${this._esc(p.desc || '')}</div>
              <div style="display:flex;gap:8px;flex-wrap:wrap">
                ${coworkCount ? `<span class="card-badge badge-dim">${coworkCount} connectors</span>` : ''}
                ${skillsGCount ? `<span class="card-badge badge-dim">${skillsGCount} global skills</span>` : ''}
                ${skillsPCount ? `<span class="card-badge badge-dim">${skillsPCount} project skills</span>` : ''}
                ${pluginCount ? `<span class="card-badge badge-dim">${pluginCount} plugins</span>` : ''}
              </div>
            </div>
          </div>
          <div style="display:flex;gap:8px;margin-top:12px;justify-content:flex-end">
            <button class="btn btn-primary btn-sm" onclick="App.tabs.presets._load('${p.id}')">Load</button>
            ${!p.builtin ? `<button class="btn btn-danger btn-sm" onclick="App.tabs.presets._delete('${p.id}', '${this._esc(p.name)}')">Delete</button>` : ''}
          </div>
        </div>`;
      }
      html += '</div>';
    } else {
      html += '<div class="empty-state">No presets saved</div>';
    }

    panel.innerHTML = html;
  },

  _showSnapshot() {
    const icons = ['⚡', '🔧', '🎨', '🌐', '📊', '🧪', '🚀', '💻', '📝', '🔒', '🎯', '🛠️', '⭐', '🔮', '🎪', '🏗️'];
    let iconHtml = '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px">';
    for (const ic of icons) {
      iconHtml += `<button class="btn btn-ghost btn-sm preset-icon-btn" onclick="App.tabs.presets._pickIcon(this, '${ic}')" style="font-size:18px;padding:4px 8px">${ic}</button>`;
    }
    iconHtml += '</div>';

    App.modal(
      'Snapshot Current State',
      `<div style="margin-bottom:12px">
        <label style="font-size:13px;color:var(--text-dim);display:block;margin-bottom:4px">Name</label>
        <input class="input" id="preset-name" placeholder="My Preset">
      </div>
      <label style="font-size:13px;color:var(--text-dim);display:block;margin-bottom:4px">Icon</label>
      ${iconHtml}
      <input type="hidden" id="preset-icon" value="⭐">
      <div>
        <label style="font-size:13px;color:var(--text-dim);display:block;margin-bottom:4px">Description</label>
        <input class="input" id="preset-desc" placeholder="What is this preset for?">
      </div>`,
      [
        { label: 'Cancel', class: 'btn-ghost' },
        { label: 'Save Snapshot', class: 'btn-primary', action: () => this._doSnapshot() },
      ]
    );
  },

  _pickIcon(btn, icon) {
    document.querySelectorAll('.preset-icon-btn').forEach(b => b.style.outline = '');
    btn.style.outline = '2px solid var(--accent)';
    document.getElementById('preset-icon').value = icon;
  },

  async _doSnapshot() {
    const name = document.getElementById('preset-name')?.value?.trim();
    if (!name) { App.toast('Name is required', 'error'); return; }
    const icon = document.getElementById('preset-icon')?.value || '⭐';
    const desc = document.getElementById('preset-desc')?.value?.trim() || '';

    const result = await App.api('/api/presets/snapshot', { name, icon, desc });
    if (result && result.id) {
      App.toast('Preset saved!', 'success');
      this.render();
    } else {
      App.toast('Failed to save preset', 'error');
    }
  },

  async _load(id) {
    App.modal(
      'Load Preset',
      '<p>This will apply the preset settings to your current configuration. Continue?</p>',
      [
        { label: 'Cancel', class: 'btn-ghost' },
        {
          label: 'Apply Preset', class: 'btn-primary',
          action: async () => {
            const result = await App.api('/api/presets/load', { id });
            if (result.ok) {
              App.toast('Preset applied!', 'success');
            } else {
              App.toast(result.error || 'Failed to apply preset', 'error');
            }
          },
        },
      ]
    );
  },

  async _delete(id, name) {
    App.modal(
      'Delete Preset',
      `<p>Delete preset <strong>${name}</strong>? This cannot be undone.</p>`,
      [
        { label: 'Cancel', class: 'btn-ghost' },
        {
          label: 'Delete', class: 'btn-danger',
          action: async () => {
            const result = await App.api('/api/presets/delete', { id });
            if (result.ok) {
              App.toast('Preset deleted', 'success');
              this.render();
            } else {
              App.toast('Failed to delete', 'error');
            }
          },
        },
      ]
    );
  },

  _esc(s) {
    const el = document.createElement('span');
    el.textContent = s || '';
    return el.innerHTML;
  },
};
