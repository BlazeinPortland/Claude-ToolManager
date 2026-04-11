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
        let statusBadge, statusClass;
        if (c.authenticated) {
          statusBadge = 'Authenticated';
          statusClass = 'badge-green';
        } else if (c.needsAuth) {
          statusBadge = 'Needs Auth';
          statusClass = 'badge-amber';
        } else if (c.hasToken) {
          statusBadge = 'Token Expired';
          statusClass = 'badge-red';
        } else {
          statusBadge = 'Not Connected';
          statusClass = 'badge-dim';
        }

        html += `<div class="item-card">
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
    html += `<span class="card-badge badge-blue">${activeCount} / ${cowork.length} active</span>`;
    html += '</div>';

    if (cowork.length) {
      html += '<div class="grid grid-auto">';
      for (const c of cowork) {
        const canToggle = c.cowork;
        const onChange = canToggle
          ? `App.tabs.connectors._toggleCowork('${c.id}', this.checked)`
          : '';

        html += `<div class="item-card">
          <div class="item-icon">${c.icon || '🔧'}</div>
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
