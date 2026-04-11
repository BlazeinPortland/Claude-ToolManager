/* ── Dashboard Tab ──────────────────────────────────────────────────────── */

App.tabs.dashboard = {
  _refreshTimer: null,

  init() {
    // Auto-refresh rate limits every 60s
    this._refreshTimer = setInterval(() => {
      if (App.currentTab === 'dashboard') this._loadRateLimits();
    }, 60000);
  },

  async render() {
    const panel = document.getElementById('panel-dashboard');
    panel.innerHTML = '<div class="loading"><div class="spinner"></div><br>Loading dashboard...</div>';

    // Fetch stats first (local, fast) — don't block on rate limits
    const stats = await App.api('/api/dashboard/stats');

    let html = '';

    // ── Rate Limits Section (placeholder, filled async) ──
    html += '<div class="card" id="rl-card">';
    html += '<div class="card-header"><span class="card-title">Rate Limits</span>';
    html += `<span class="card-badge badge-dim" id="rl-refresh">loading...</span>`;
    html += '</div>';
    html += '<div id="rl-content"><div class="loading" style="padding:16px"><div class="spinner"></div></div></div>';
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

    // Load rate limits async (don't block page render)
    this._loadRateLimits();
  },

  async _loadRateLimits() {
    try {
      const limits = await App.api('/api/dashboard/rate-limits');
      const container = document.getElementById('rl-content');
      if (container) {
        container.innerHTML = this._renderRateLimits(limits);
      }
      const badge = document.getElementById('rl-refresh');
      if (badge) badge.textContent = App.timeAgo(Date.now());
    } catch (e) {
      const container = document.getElementById('rl-content');
      if (container) {
        container.innerHTML = '<div class="empty-state" style="padding:12px">Rate limit request failed</div>';
      }
    }
  },

  _renderRateLimits(data) {
    if (!data || data.error) {
      return `<div class="empty-state" style="padding:12px">Rate limit data unavailable: ${data?.error || 'unknown error'}</div>`;
    }

    let html = '';

    // Try different response formats
    const fiveHour = data.five_hour || data.fiveHour || data.daily || null;
    const sevenDay = data.seven_day || data.sevenDay || data.monthly || null;

    if (fiveHour) {
      const pct = fiveHour.used_percentage || fiveHour.usedPercentage || fiveHour.percentUsed || 0;
      const resets = fiveHour.resets_at || fiveHour.resetsAt || '';
      html += this._gauge('5-Hour Window', pct, resets);
    }

    if (sevenDay) {
      const pct = sevenDay.used_percentage || sevenDay.usedPercentage || sevenDay.percentUsed || 0;
      const resets = sevenDay.resets_at || sevenDay.resetsAt || '';
      html += this._gauge('7-Day Window', pct, resets);
    }

    if (!fiveHour && !sevenDay) {
      // Maybe the data is in a different format, show raw keys
      const keys = Object.keys(data).filter(k => k !== 'error');
      if (keys.length === 0) {
        html += '<div class="empty-state" style="padding:12px">No rate limit data in response</div>';
      } else {
        // Show whatever we got
        for (const key of keys) {
          const val = data[key];
          if (typeof val === 'object' && val !== null) {
            const pct = val.used_percentage || val.usedPercentage || val.percentUsed || val.percent_used || 0;
            const resets = val.resets_at || val.resetsAt || '';
            html += this._gauge(key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()), pct, resets);
          }
        }
        if (!html) {
          html += `<div class="empty-state" style="padding:12px">Rate limit response keys: ${keys.join(', ')}</div>`;
        }
      }
    }

    return html;
  },

  _gauge(label, percent, resetsAt) {
    const pct = Math.min(100, Math.max(0, Math.round(percent)));
    const level = pct < 50 ? 'low' : pct < 80 ? 'mid' : 'high';
    const resetStr = resetsAt ? `Resets: ${new Date(resetsAt).toLocaleTimeString()}` : '';
    return `<div class="gauge">
      <div class="gauge-label">
        <span>${label}</span>
        <span>${pct}% used${resetStr ? ' · ' + resetStr : ''}</span>
      </div>
      <div class="gauge-track">
        <div class="gauge-fill ${level}" style="width:${pct}%"></div>
      </div>
    </div>`;
  },

  _statCard(value, label) {
    return `<div class="stat-card"><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div>`;
  },

  _renderActivityChart(data) {
    const recent = data.slice(-14);
    if (!recent.length) return '<div class="empty-state">No activity data</div>';
    const maxVal = Math.max(...recent.map(d => d.messageCount || 0), 1);

    let bars = '<div class="chart-bars">';
    let labels = '<div class="chart-labels">';
    for (const day of recent) {
      const h = Math.max(2, ((day.messageCount || 0) / maxVal) * 100);
      const date = day.date ? day.date.slice(5) : '?';
      bars += `<div class="chart-bar" style="height:${h}%"><span class="tooltip">${day.date}: ${day.messageCount} msgs, ${day.toolCallCount || 0} tools</span></div>`;
      labels += `<div class="chart-label">${date}</div>`;
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
      labels += `<div class="chart-label">${(day.date || '').slice(5)}</div>`;
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
