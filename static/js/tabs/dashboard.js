/* ── Dashboard Tab ──────────────────────────────────────────────────────── */

App.tabs.dashboard = {
  _refreshTimer: null,

  init() {
    // Auto-refresh server status every 30s
    this._refreshTimer = setInterval(() => {
      if (App.currentTab === 'dashboard') this._loadServerStatus();
    }, 30000);
  },

  async render() {
    const panel = document.getElementById('panel-dashboard');
    panel.innerHTML = '<div class="loading"><div class="spinner"></div><br>Loading dashboard...</div>';

    // Fetch stats first (local, fast) — don't block on server status
    const stats = await App.api('/api/dashboard/stats');

    let html = '';

    // ── Server Status Section (placeholder, filled async) ──
    html += '<div class="card" id="ss-card">';
    html += '<div class="card-header"><span class="card-title">Server Status</span>';
    html += `<span class="card-badge badge-green" id="ss-badge">live</span>`;
    html += '</div>';
    html += '<div id="ss-content"><div class="loading" style="padding:16px"><div class="spinner"></div></div></div>';
    html += '</div>';

    // ── Summary Cards ──
    if (stats && !stats.error) {
      const totalOutputTokens = Object.values(stats.modelUsage || {}).reduce((s, m) => s + (m.outputTokens || 0), 0);
      const peakHour = this._peakHour(stats.hourCounts || {});

      html += '<div class="grid grid-3" style="margin-bottom:16px">';
      html += this._statCard(App.fmtNum(stats.totalSessions || 0), 'Total Sessions');
      html += this._statCard(App.fmtNum(stats.totalMessages || 0), 'Total Messages');
      html += this._statCard(App.fmtNum(totalOutputTokens), 'Output Tokens');
      html += this._statCard(stats.firstSessionDate ? App.fmtDate(new Date(stats.firstSessionDate).getTime()) : '—', 'First Session');
      html += this._statCard(peakHour, 'Peak Hour');
      html += this._statCard(stats.longestSession ? `${stats.longestSession.messageCount} msgs` : '—', 'Longest Session');
      html += '</div>';

      // ── Activity Chart ──
      html += '<div class="card">';
      html += '<div class="card-header"><span class="card-title">Daily Activity (Messages)</span></div>';
      html += this._renderActivityChart(stats.dailyActivity || []);
      html += '</div>';

      // ── Token Usage Chart ──
      html += '<div class="card">';
      html += '<div class="card-header"><span class="card-title">Daily Token Output by Model</span></div>';
      html += this._renderTokenChart(stats.dailyModelTokens || []);
      html += '</div>';

      // ── Model Breakdown ──
      html += '<div class="card">';
      html += '<div class="card-header"><span class="card-title">Model Usage Totals</span></div>';
      html += this._renderModelTable(stats.modelUsage || {});
      html += '</div>';
    } else {
      html += '<div class="empty-state">Stats not available. Claude Code stores usage data in stats-cache.json after sessions.</div>';
    }

    panel.innerHTML = html;

    // Load server status async (don't block page render)
    this._loadServerStatus();
  },

  async _loadServerStatus() {
    try {
      const status = await App.api('/api/server/status');
      const container = document.getElementById('ss-content');
      if (container) container.innerHTML = this._renderServerStatus(status);
    } catch (e) {
      const container = document.getElementById('ss-content');
      if (container) container.innerHTML = '<div class="empty-state" style="padding:12px">Server status unavailable</div>';
    }
  },

  _renderServerStatus(s) {
    if (!s || s.error) {
      return `<div class="empty-state" style="padding:12px">Status unavailable: ${s?.error || 'unknown'}</div>`;
    }

    const cfIcon = (ok) => ok
      ? `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`
      : `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--red)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;

    const cf = s.config_files || {};
    const cfRows = [
      ['Global Settings', cf.global_settings],
      ['Project Settings', cf.project_settings],
      ['Credentials', cf.credentials],
      ['Stats Cache', cf.stats_cache],
      ['Cowork State', cf.cowork_state],
    ];

    let html = '<div class="status-grid">';
    html += `<div class="status-item"><div class="status-item-label">Uptime</div><div class="status-item-value">${s.uptime_str || '—'}</div></div>`;
    html += `<div class="status-item"><div class="status-item-label">Session Files</div><div class="status-item-value">${s.session_files ?? '—'}</div></div>`;
    html += `<div class="status-item"><div class="status-item-label">Port</div><div class="status-item-value">${s.port || 9191}</div></div>`;
    html += `<div class="status-item"><div class="status-item-label">Python</div><div class="status-item-value">${s.python_version || '—'}</div></div>`;
    html += '</div>';

    html += '<div style="margin-top:12px;display:flex;gap:16px;flex-wrap:wrap">';
    for (const [label, ok] of cfRows) {
      html += `<div style="display:flex;align-items:center;gap:5px;font-size:13px">
        ${cfIcon(ok)}
        <span style="color:${ok ? 'var(--text)' : 'var(--red)'}">${label}</span>
      </div>`;
    }
    html += '</div>';

    if (s.appdata_claude) {
      html += `<div style="margin-top:10px;font-size:12px;color:var(--text-dim);font-family:var(--font-mono)">${s.appdata_claude}</div>`;
    }

    return html;
  },

  _statCard(value, label) {
    return `<div class="stat-card"><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div>`;
  },

  _fmtChartDate(dateStr) {
    if (!dateStr) return '?';
    try {
      const d = new Date(dateStr + 'T12:00:00');
      const mon = d.toLocaleDateString('en-US', { month: 'short' });
      const day = d.getDate();
      return `${mon}<br>${day}`;
    } catch { return dateStr.slice(5); }
  },

  _renderActivityChart(data) {
    const recent = data.slice(-14);
    if (!recent.length) return '<div class="empty-state">No activity data</div>';
    const maxVal = Math.max(...recent.map(d => d.messageCount || 0), 1);

    let bars = '<div class="chart-bars">';
    let labels = '<div class="chart-labels">';
    for (const day of recent) {
      const h = Math.max(2, ((day.messageCount || 0) / maxVal) * 100);
      bars += `<div class="chart-bar" style="height:${h}%"><span class="tooltip">${day.date}: ${day.messageCount} msgs, ${day.toolCallCount || 0} tools</span></div>`;
      labels += `<div class="chart-label">${this._fmtChartDate(day.date)}</div>`;
    }
    bars += '</div>';
    labels += '</div>';
    return bars + labels;
  },

  _renderTokenChart(data) {
    const recent = data.slice(-14);
    if (!recent.length) return '<div class="empty-state">No token data</div>';

    // Get all models
    const models = new Set();
    recent.forEach(d => Object.keys(d.tokensByModel || {}).forEach(m => models.add(m)));
    const modelList = [...models];

    // Colors for models
    const colors = ['var(--accent)', 'var(--green)', 'var(--amber)', 'var(--blue)'];

    const totals = recent.map(d => {
      return Object.values(d.tokensByModel || {}).reduce((s, v) => s + v, 0);
    });
    const maxVal = Math.max(...totals, 1);

    let bars = '<div class="chart-bars">';
    let labels = '<div class="chart-labels">';
    for (const day of recent) {
      const total = Object.values(day.tokensByModel || {}).reduce((s, v) => s + v, 0);
      const h = Math.max(2, (total / maxVal) * 100);
      const detail = modelList.map(m => {
        const short = m.replace('claude-', '').replace(/-\d+$/, '');
        return `${short}: ${App.fmtNum(day.tokensByModel?.[m] || 0)}`;
      }).join(', ');
      bars += `<div class="chart-bar" style="height:${h}%"><span class="tooltip">${day.date}: ${detail}</span></div>`;
      labels += `<div class="chart-label">${this._fmtChartDate(day.date)}</div>`;
    }
    bars += '</div>';
    labels += '</div>';

    // Legend
    let legend = '<div style="display:flex;gap:16px;margin-top:8px;padding:0 4px">';
    modelList.forEach((m, i) => {
      const short = m.replace('claude-', '').replace(/-20\d+$/, '');
      legend += `<span style="font-size:11px;color:var(--text-dim)"><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${colors[i % colors.length]};margin-right:4px"></span>${short}</span>`;
    });
    legend += '</div>';

    return bars + labels + legend;
  },

  _renderModelTable(usage) {
    const models = Object.entries(usage);
    if (!models.length) return '<div class="empty-state">No model data</div>';

    let html = '<div class="table-wrap"><table>';
    html += '<tr><th>Model</th><th>Input</th><th>Output</th><th>Cache Read</th><th>Cache Write</th></tr>';
    for (const [name, m] of models) {
      const short = name.replace('claude-', '').replace(/-20\d+$/, '');
      html += `<tr>
        <td><strong>${short}</strong></td>
        <td>${App.fmtNum(m.inputTokens || 0)}</td>
        <td>${App.fmtNum(m.outputTokens || 0)}</td>
        <td>${App.fmtNum(m.cacheReadInputTokens || 0)}</td>
        <td>${App.fmtNum(m.cacheCreationInputTokens || 0)}</td>
      </tr>`;
    }
    html += '</table></div>';
    return html;
  },

  _peakHour(counts) {
    const entries = Object.entries(counts);
    if (!entries.length) return '—';
    entries.sort((a, b) => b[1] - a[1]);
    const h = parseInt(entries[0][0]);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${h12}:00 ${ampm} (${entries[0][1]} sessions)`;
  },
};
