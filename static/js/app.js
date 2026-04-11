/* ── Claude Tool Manager — SPA Framework ───────────────────────────────── */

const App = {
  currentTab: 'dashboard',
  tabs: {},        // Populated by tab modules: { init(), render() }
  initialized: {}, // Track which tabs have been initialized
  config: null,    // Cached config/paths

  // ── API Client ──────────────────────────────────────────────────────
  async api(path, body = null, timeoutMs = 15000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const opts = {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
    };
    if (body !== null) {
      opts.method = 'POST';
      opts.body = JSON.stringify(body);
    }
    try {
      const resp = await fetch(path, opts);
      clearTimeout(timer);
      return resp.json();
    } catch (e) {
      clearTimeout(timer);
      if (e.name === 'AbortError') return { error: 'Request timed out' };
      return { error: e.message };
    }
  },

  // ── Tab Router ──────────────────────────────────────────────────────
  switchTab(name) {
    if (!this.tabs[name]) return;

    // Update tab bar
    document.querySelectorAll('.tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === name);
    });

    // Update panels
    document.querySelectorAll('.panel').forEach(p => {
      p.classList.toggle('active', p.id === `panel-${name}`);
    });

    this.currentTab = name;

    // Init on first visit, then render
    if (!this.initialized[name]) {
      this.initialized[name] = true;
      if (this.tabs[name].init) this.tabs[name].init();
    }
    if (this.tabs[name].render) this.tabs[name].render();
  },

  // ── Toast System ────────────────────────────────────────────────────
  toast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 200); }, 3000);
  },

  // ── Modal System ────────────────────────────────────────────────────
  modal(title, bodyHtml, buttons = []) {
    const overlay = document.getElementById('modal-overlay');
    document.getElementById('modal-header').textContent = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    const footer = document.getElementById('modal-footer');
    footer.innerHTML = '';
    buttons.forEach(b => {
      const btn = document.createElement('button');
      btn.className = `btn ${b.class || 'btn-ghost'}`;
      btn.textContent = b.label;
      btn.onclick = () => { overlay.classList.add('hidden'); if (b.action) b.action(); };
      footer.appendChild(btn);
    });
    overlay.classList.remove('hidden');
  },

  closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
  },

  // ── Utility: Format numbers ─────────────────────────────────────────
  fmtNum(n) {
    if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return String(n);
  },

  // ── Utility: Format date ────────────────────────────────────────────
  fmtDate(ms) {
    if (!ms) return '—';
    const d = new Date(ms);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  },

  fmtDateTime(ms) {
    if (!ms) return '—';
    const d = new Date(ms);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' +
           d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  },

  // ── Utility: Time ago ───────────────────────────────────────────────
  timeAgo(ms) {
    if (!ms) return '—';
    const diff = Date.now() - ms;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  },

  // ── Utility: Create toggle HTML ─────────────────────────────────────
  toggleHtml(checked, onchange) {
    const id = 'tog_' + Math.random().toString(36).slice(2, 8);
    return `<label class="toggle">
      <input type="checkbox" id="${id}" ${checked ? 'checked' : ''} onchange="${onchange}">
      <span class="toggle-slider"></span>
    </label>`;
  },

  // ── Project Selector ────────────────────────────────────────────────
  async loadProjects() {
    const projects = await this.api('/api/projects');
    const config = await this.api('/api/config/paths');
    this.config = config;

    const select = document.getElementById('project-select');
    select.innerHTML = '';
    if (Array.isArray(projects)) {
      projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.path;
        if (config.project && config.project.includes(p.path.replace(/\\/g, '/'))) {
          opt.selected = true;
        }
        select.appendChild(opt);
      });
    }

    const info = document.getElementById('path-info');
    info.textContent = config.project ? '' : 'No project';
  },

  async switchProject(projectId) {
    const result = await this.api('/api/config/project', { project: projectId });
    if (result.ok) {
      this.config = await this.api('/api/config/paths');
      this.toast('Switched project', 'success');
      // Re-render current tab to pick up new project data
      if (this.tabs[this.currentTab] && this.tabs[this.currentTab].render) {
        this.tabs[this.currentTab].render();
      }
    } else {
      this.toast(result.error || 'Failed to switch project', 'error');
    }
  },

  // ── Server Control ──────────────────────────────────────────────────
  shutdownServer() {
    this.modal(
      'Shutdown Server',
      '<p>Are you sure you want to shut down the Tool Manager server?</p><p style="color:var(--text-dim)">You will need to restart it manually.</p>',
      [
        { label: 'Cancel', class: 'btn-ghost' },
        {
          label: 'Shutdown', class: 'btn-danger',
          action: async () => {
            await this.api('/api/server/shutdown');
            document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;color:var(--text-dim);font-size:18px;background:var(--bg)">Server has been shut down.</div>';
          },
        },
      ]
    );
  },

  restartClaude() {
    this.modal(
      'Restart Claude Desktop',
      '<p>This will close and relaunch Claude Desktop.</p><p style="color:var(--text-dim)">Any unsaved work in Claude will be lost. Config changes will take effect after restart.</p>',
      [
        { label: 'Cancel', class: 'btn-ghost' },
        {
          label: 'Restart Claude', class: 'btn-primary',
          action: async () => {
            this.toast('Restarting Claude Desktop...', 'info');
            const result = await this.api('/api/claude/restart');
            if (result.ok) {
              this.toast('Claude Desktop is restarting', 'success');
            } else {
              this.toast(result.error || 'Failed to restart Claude', 'error');
            }
          },
        },
      ]
    );
  },

  // ── Init ────────────────────────────────────────────────────────────
  async init() {
    // Tab clicks
    document.querySelectorAll('.tab').forEach(t => {
      t.addEventListener('click', () => this.switchTab(t.dataset.tab));
    });

    // Modal close on overlay click
    document.getElementById('modal-overlay').addEventListener('click', e => {
      if (e.target === e.currentTarget) this.closeModal();
    });

    // Project selector
    document.getElementById('project-select').addEventListener('change', e => {
      this.switchProject(e.target.value);
    });

    // Load projects and config
    await this.loadProjects();

    // Show default tab
    this.switchTab('dashboard');
  },
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());
