/* ── Plugins Tab ────────────────────────────────────────────────────────── */

App.tabs.plugins = {
  init() {},

  async render() {
    const panel = document.getElementById('panel-plugins');
    panel.innerHTML = '<div class="loading"><div class="spinner"></div><br>Loading plugins...</div>';

    const data = await App.api('/api/plugins');
    if (!data || data.error) {
      panel.innerHTML = '<div class="empty-state">Failed to load plugin data</div>';
      return;
    }

    let html = '';
    const plugins = data.plugins || [];
    const blocklist = data.blocklist || [];
    const marketplaces = data.marketplaces || {};

    // ── Installed Plugins ──
    const enabledCount = plugins.filter(p => p.enabled).length;
    html += '<div class="section-title">';
    html += '<span>Installed Plugins</span>';
    html += `<span class="card-badge badge-cyan">${enabledCount} / ${plugins.length} enabled</span>`;
    html += '</div>';

    if (plugins.length) {
      html += '<div class="grid grid-auto">';
      for (const p of plugins) {
        const onChange = `App.tabs.plugins._toggle('${this._esc(p.id)}', this.checked)`;
        html += `<div class="item-card">
          <div class="item-icon">${this._pluginIcon()}</div>
          <div class="item-info">
            <div class="item-name">${this._esc(p.name)}</div>
            <div class="item-desc">v${this._esc(p.version)} · ${this._esc(p.marketplace)}</div>
            <div class="item-meta">Installed: ${p.installedAt ? App.fmtDate(new Date(p.installedAt).getTime()) : '—'}</div>
          </div>
          <div class="item-actions">
            ${App.toggleHtml(p.enabled, onChange)}
          </div>
        </div>`;
      }
      html += '</div>';
    } else {
      html += '<div class="empty-state">No plugins installed</div>';
    }

    // ── Blocklist ──
    if (blocklist.length) {
      html += '<div class="section-title" style="margin-top:32px"><span>Blocklist</span>';
      html += `<span class="card-badge badge-red">${blocklist.length} blocked</span></div>`;

      html += '<div class="table-wrap"><table>';
      html += '<tr><th>Plugin</th><th>Reason</th><th>Description</th></tr>';
      for (const b of blocklist) {
        html += `<tr>
          <td><strong>${this._esc(b.plugin || '')}</strong></td>
          <td>${this._esc(b.reason || '')}</td>
          <td style="color:var(--text-dim)">${this._esc(b.text || '')}</td>
        </tr>`;
      }
      html += '</table></div>';
    }

    // ── Marketplaces ──
    const mktEntries = Object.values(marketplaces);
    if (mktEntries.length) {
      html += '<div class="section-title" style="margin-top:32px"><span>Marketplaces</span>';
      html += `<span class="card-badge badge-dim">${mktEntries.length} registered</span></div>`;

      html += '<div class="grid grid-auto">';
      for (const m of mktEntries) {
        html += `<div class="item-card">
          <div class="item-icon">${this._marketplaceIcon()}</div>
          <div class="item-info">
            <div class="item-name">${this._esc(m.name)}</div>
            <div class="item-desc">${this._esc(m.sourceType)}: ${this._esc(m.repo)}</div>
            <div class="item-meta">Updated: ${m.lastUpdated ? App.fmtDate(new Date(m.lastUpdated).getTime()) : '—'}</div>
          </div>
        </div>`;
      }
      html += '</div>';
    }

    panel.innerHTML = html;
  },

  _pluginIcon() {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5l6.74-6.76z"/>
      <line x1="16" y1="8" x2="2" y2="22"/>
      <line x1="17.5" y1="15" x2="9" y2="15"/>
    </svg>`;
  },

  _marketplaceIcon() {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
      <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>`;
  },

  async _toggle(pluginId, enable) {
    const result = await App.api('/api/plugins/toggle', { id: pluginId, enable });
    if (result.ok) {
      App.toast(`Plugin ${enable ? 'enabled' : 'disabled'}`, 'success');
    } else {
      App.toast(result.error || 'Failed', 'error');
      this.render();
    }
  },

  _esc(s) {
    const el = document.createElement('span');
    el.textContent = s || '';
    return el.innerHTML;
  },
};
