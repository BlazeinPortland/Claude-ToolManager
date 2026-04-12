/* ── Connectors Tab ─────────────────────────────────────────────────────── */

App.tabs.connectors = {
  init() {},

  async render() {
    const panel = document.getElementById('panel-connectors');
    panel.innerHTML = '<div class="loading"><div class="spinner"></div><br>Loading connectors...</div>';

    const data = await App.api('/api/connectors');
    if (!data) {
      panel.innerHTML = '<div class="empty-state">Failed to load connector data</div>';
      return;
    }

    let html = '';
    const oauth = data.oauth || [];
    const cowork = data.cowork || [];

    // ── OAuth Connectors ──
    const authed = oauth.filter(c => c.authenticated).length;
    html += '<div class="section-title">';
    html += '<span>MCP OAuth Connectors</span>';
    html += `<span class="card-badge ${authed > 0 ? 'badge-green' : 'badge-dim'}">${authed} / ${oauth.length} authenticated</span>`;
    html += '</div>';

    if (oauth.length) {
      html += '<div class="grid grid-auto">';
      for (const c of oauth) {
        let statusBadge, statusClass, iconSvg;
        if (c.authenticated) {
          statusBadge = 'Authenticated';
          statusClass = 'badge-green';
          iconSvg = this._oauthIcon('green');
        } else if (c.needsAuth) {
          statusBadge = 'Needs Auth';
          statusClass = 'badge-amber';
          iconSvg = this._oauthIcon('amber');
        } else if (c.hasToken) {
          statusBadge = 'Token Expired';
          statusClass = 'badge-red';
          iconSvg = this._oauthIcon('red');
        } else {
          statusBadge = 'Not Connected';
          statusClass = 'badge-dim';
          iconSvg = this._oauthIcon('dim');
        }

        html += `<div class="item-card">
          <div class="item-icon">${iconSvg}</div>
          <div class="item-info">
            <div class="item-name">${this._esc(c.displayName)}</div>
            <div class="item-meta" style="font-family:var(--font-mono)">${this._esc(c.serverName.split('|')[0])}</div>
          </div>
          <div class="item-actions">
            <span class="card-badge ${statusClass}">${statusBadge}</span>
          </div>
        </div>`;
      }
      html += '</div>';
    } else {
      html += '<div class="empty-state">No OAuth connectors found</div>';
    }

    // ── Cowork Connectors ──
    const activeCount = cowork.filter(c => c.active).length;
    html += '<div class="section-title" style="margin-top:32px">';
    html += '<span>Cowork Connectors</span>';
    html += `<span class="card-badge badge-cyan">${activeCount} / ${cowork.length} active</span>`;
    html += '</div>';

    if (cowork.length) {
      html += '<div class="grid grid-auto">';
      for (const c of cowork) {
        const canToggle = c.cowork;
        const onChange = canToggle
          ? `App.tabs.connectors._toggleCowork('${c.id}', this.checked)`
          : '';

        html += `<div class="item-card">
          <div class="item-icon" style="font-size:22px;display:flex;align-items:center;justify-content:center">${c.icon || this._coworkIconSvg(c.active)}</div>
          <div class="item-info">
            <div class="item-name">${this._esc(c.name)}</div>
            <div class="item-desc">${this._esc(c.desc)}</div>
            ${!canToggle ? '<div class="item-meta">Code tab only</div>' : ''}
          </div>
          <div class="item-actions">
            ${canToggle
              ? App.toggleHtml(c.active, onChange)
              : '<span class="card-badge badge-dim">Code tab</span>'
            }
          </div>
        </div>`;
      }
      html += '</div>';
    }

    panel.innerHTML = html;
  },

  _oauthIcon(state) {
    const colors = { green: 'var(--green)', amber: 'var(--amber)', red: 'var(--red)', dim: 'var(--text-dim)' };
    const color = colors[state] || 'var(--text-dim)';
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
    </svg>`;
  },

  _coworkIconSvg(active) {
    const color = active ? 'var(--accent)' : 'var(--text-dim)';
    return `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07M8.46 8.46a5 5 0 0 0 0 7.07"/>
    </svg>`;
  },

  async _toggleCowork(id, active) {
    const result = await App.api('/api/connectors/cowork/toggle', { id, active });
    if (result.ok) {
      App.toast(`${id} ${active ? 'activated' : 'deactivated'}`, 'success');
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
