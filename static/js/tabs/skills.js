/* ── Skills Tab ─────────────────────────────────────────────────────────── */

App.tabs.skills = {
  init() {},

  async render() {
    const panel = document.getElementById('panel-skills');
    panel.innerHTML = '<div class="loading"><div class="spinner"></div><br>Loading skills...</div>';

    const [global, project] = await Promise.all([
      App.api('/api/skills/global'),
      App.api('/api/skills/project'),
    ]);

    let html = '';

    // ── Global Skills ──
    const gEnabled = Array.isArray(global) ? global.filter(s => s.enabled).length : 0;
    const gTotal = Array.isArray(global) ? global.length : 0;

    html += '<div class="section-title">';
    html += '<span>Global Skills</span>';
    html += `<span class="card-badge badge-cyan">${gEnabled} / ${gTotal} enabled</span>`;
    html += '</div>';

    if (Array.isArray(global) && global.length) {
      html += '<div class="grid grid-auto">';
      // Sort: enabled first, then alphabetical
      const sorted = [...global].sort((a, b) => {
        if (a.enabled !== b.enabled) return a.enabled ? -1 : 1;
        return a.name.localeCompare(b.name);
      });
      for (const s of sorted) {
        html += this._skillCard(s, 'global');
      }
      html += '</div>';
    } else {
      html += '<div class="empty-state">No global skills found</div>';
    }

    // ── Project Skills ──
    html += '<div class="section-title" style="margin-top:32px">';
    html += '<span>Project Skills</span>';
    const pEnabled = Array.isArray(project) ? project.filter(s => s.enabled).length : 0;
    const pTotal = Array.isArray(project) ? project.length : 0;
    html += `<span class="card-badge badge-cyan">${pEnabled} / ${pTotal} enabled</span>`;
    html += '</div>';

    if (Array.isArray(project) && project.length) {
      html += '<div class="grid grid-auto">';
      for (const s of project) {
        html += this._skillCard(s, 'project');
      }
      html += '</div>';
    } else {
      html += '<div class="empty-state">No project-level skills</div>';
    }

    panel.innerHTML = html;
  },

  _skillIcon(skill) {
    if (skill.icon) {
      // Frontmatter icon — could be emoji or text
      return `<div class="item-icon" style="font-size:22px;display:flex;align-items:center;justify-content:center">${this._esc(skill.icon)}</div>`;
    }
    // Generate initials avatar from skill name
    const words = (skill.name || skill.id || '?').split(/[\s\-_]+/);
    const initials = words.length >= 2
      ? (words[0][0] + words[1][0]).toUpperCase()
      : (skill.name || skill.id || '?')[0].toUpperCase();
    const hue = [...(skill.id || '')].reduce((h, c) => (h * 31 + c.charCodeAt(0)) & 0xFFFF, 0) % 360;
    return `<div class="item-icon" style="font-size:14px;font-weight:700;display:flex;align-items:center;justify-content:center;background:hsl(${hue},60%,18%);color:hsl(${hue},80%,65%);border-color:hsl(${hue},60%,30%)">${initials}</div>`;
  },

  _skillCard(skill, scope) {
    const onChange = `App.tabs.skills._toggle('${skill.id}', '${scope}', this.checked)`;
    return `<div class="item-card">
      ${this._skillIcon(skill)}
      <div class="item-info">
        <div class="item-name">${this._esc(skill.name)}</div>
        <div class="item-desc">${this._esc(skill.desc || 'No description')}</div>
        <div class="item-meta">${scope === 'global' ? 'Global' : 'Project'} · ${skill.id}</div>
      </div>
      <div class="item-actions">
        ${App.toggleHtml(skill.enabled, onChange)}
      </div>
    </div>`;
  },

  async _toggle(id, scope, enable) {
    const endpoint = scope === 'global' ? '/api/skills/global/toggle' : '/api/skills/project/toggle';
    const result = await App.api(endpoint, { id, enable });
    if (result.ok) {
      App.toast(`${id} ${enable ? 'enabled' : 'disabled'}`, 'success');
      // Brief delay then refresh to show new state
      setTimeout(() => this.render(), 300);
    } else {
      App.toast(result.error || 'Failed to toggle skill', 'error');
      this.render();
    }
  },

  _esc(s) {
    const el = document.createElement('span');
    el.textContent = s || '';
    return el.innerHTML;
  },
};
