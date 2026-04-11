/* ── Settings Tab ──────────────────────────────────────────────────────── */

App.tabs.settings = {
  _subTab: 'global',

  init() {},

  async render() {
    const panel = document.getElementById('panel-settings');
    panel.innerHTML = '<div class="loading"><div class="spinner"></div><br>Loading settings...</div>';

    const [global, project, mcps] = await Promise.all([
      App.api('/api/settings/global'),
      App.api('/api/settings/project'),
      App.api('/api/settings/mcp-servers'),
    ]);

    let html = '';

    // Sub-tabs
    html += '<div class="sub-tabs">';
    html += `<button class="sub-tab ${this._subTab === 'global' ? 'active' : ''}" onclick="App.tabs.settings._switchSub('global')">Global</button>`;
    html += `<button class="sub-tab ${this._subTab === 'project' ? 'active' : ''}" onclick="App.tabs.settings._switchSub('project')">Project</button>`;
    html += '</div>';

    // ── Global Sub-tab ──
    html += `<div id="settings-global" style="display:${this._subTab === 'global' ? 'block' : 'none'}">`;

    // MCP Servers
    html += '<div class="card">';
    html += '<div class="card-header"><span class="card-title">MCP Servers</span>';
    html += `<span class="card-badge badge-blue">${Array.isArray(mcps) ? mcps.length : 0} configured</span>`;
    html += '</div>';

    if (Array.isArray(mcps) && mcps.length) {
      html += '<div class="table-wrap"><table>';
      html += '<tr><th>Name</th><th>Command</th><th>Args</th><th>Env Vars</th></tr>';
      for (const s of mcps) {
        const args = (s.args || []).join(' ');
        html += `<tr>
          <td><strong>${this._esc(s.name)}</strong></td>
          <td><code>${this._esc(s.command)}</code></td>
          <td style="font-family:var(--font-mono);font-size:12px;max-width:300px;overflow:hidden;text-overflow:ellipsis">${this._esc(args)}</td>
          <td>${s.env_count}</td>
        </tr>`;
      }
      html += '</table></div>';
    } else {
      html += '<div class="empty-state">No MCP servers configured in global settings</div>';
    }
    html += '</div>';

    // Global Permissions
    html += '<div class="card">';
    html += '<div class="card-header"><span class="card-title">Global Permissions</span></div>';
    const gPerms = global?.permissions?.allow || [];
    if (gPerms.length) {
      html += '<div class="chip-list">';
      for (const p of gPerms) {
        html += `<span class="chip">${this._esc(p)}</span>`;
      }
      html += '</div>';
    } else {
      html += '<div class="empty-state">No global permissions set</div>';
    }
    html += '</div>';

    // Voice & Statusline
    html += '<div class="card">';
    html += '<div class="card-header"><span class="card-title">Preferences</span></div>';
    html += '<div style="display:flex;gap:24px;flex-wrap:wrap">';
    html += `<div><span style="font-size:13px;color:var(--text-dim)">Voice:</span> <span class="card-badge ${global?.voiceEnabled ? 'badge-green' : 'badge-dim'}">${global?.voiceEnabled ? 'Enabled' : 'Disabled'}</span></div>`;
    const slCmd = global?.statusLine?.command || '(not set)';
    html += `<div><span style="font-size:13px;color:var(--text-dim)">Statusline:</span> <code style="font-size:12px;color:var(--text-muted)">${this._esc(slCmd)}</code></div>`;
    html += '</div>';
    html += '</div>';

    html += '</div>'; // end global

    // ── Project Sub-tab ──
    html += `<div id="settings-project" style="display:${this._subTab === 'project' ? 'block' : 'none'}">`;

    if (project && !project.error) {
      // Project Permissions
      html += '<div class="card">';
      html += '<div class="card-header"><span class="card-title">Project Permissions</span>';
      const pPerms = project?.permissions?.allow || [];
      html += `<span class="card-badge badge-blue">${pPerms.length} entries</span>`;
      html += '</div>';

      if (pPerms.length) {
        html += '<div class="chip-list" style="margin-bottom:12px">';
        for (const p of pPerms) {
          html += `<span class="chip">${this._esc(p)} <span class="chip-remove" onclick="App.tabs.settings._removePerm('${this._esc(p)}')">&times;</span></span>`;
        }
        html += '</div>';
      }

      // Add permission input
      html += '<div class="input-row">';
      html += '<input class="input" id="new-perm-input" placeholder="Add permission, e.g. mcp__my_server__*" style="max-width:400px">';
      html += '<button class="btn btn-primary btn-sm" onclick="App.tabs.settings._addPerm()">Add</button>';
      html += '</div>';
      html += '</div>';

      // Raw JSON editor
      html += '<div class="card">';
      html += '<div class="card-header"><span class="card-title">Raw Project Settings</span>';
      html += '<button class="btn btn-ghost btn-sm" onclick="App.tabs.settings._saveProjectJson()">Save Changes</button>';
      html += '</div>';
      html += `<textarea class="input" id="project-json-editor" rows="12">${JSON.stringify(project, null, 2)}</textarea>`;
      html += '</div>';
    } else {
      html += '<div class="empty-state">No project directory detected</div>';
    }

    html += '</div>'; // end project

    panel.innerHTML = html;
  },

  _switchSub(sub) {
    this._subTab = sub;
    document.querySelectorAll('#panel-settings .sub-tab').forEach(t => {
      t.classList.toggle('active', t.textContent.toLowerCase() === sub);
    });
    const globalEl = document.getElementById('settings-global');
    const projectEl = document.getElementById('settings-project');
    if (globalEl) globalEl.style.display = sub === 'global' ? 'block' : 'none';
    if (projectEl) projectEl.style.display = sub === 'project' ? 'block' : 'none';
  },

  async _addPerm() {
    const input = document.getElementById('new-perm-input');
    const entry = input?.value?.trim();
    if (!entry) return;
    const result = await App.api('/api/settings/permissions/project/toggle', { entry, enable: true });
    if (result.ok) {
      App.toast('Permission added', 'success');
      input.value = '';
      this.render();
    } else {
      App.toast(result.error || 'Failed', 'error');
    }
  },

  async _removePerm(entry) {
    const result = await App.api('/api/settings/permissions/project/toggle', { entry, enable: false });
    if (result.ok) {
      App.toast('Permission removed', 'success');
      this.render();
    } else {
      App.toast(result.error || 'Failed', 'error');
    }
  },

  async _saveProjectJson() {
    const textarea = document.getElementById('project-json-editor');
    try {
      const data = JSON.parse(textarea.value);
      const result = await App.api('/api/settings/project', data);
      if (result.ok) {
        App.toast('Project settings saved', 'success');
      } else {
        App.toast(result.error || 'Failed to save', 'error');
      }
    } catch (e) {
      App.toast('Invalid JSON: ' + e.message, 'error');
    }
  },

  _esc(s) {
    const el = document.createElement('span');
    el.textContent = s || '';
    return el.innerHTML;
  },
};
