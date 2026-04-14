#!/usr/bin/env python3
"""
Claude Tool Manager v2
Full-featured management dashboard for Claude Desktop settings.
Run with: python tool-manager.py [--project <path>]
Then open: http://localhost:9191
"""

import json, os, shutil, sys, uuid, webbrowser, time, re, subprocess, threading, platform
from datetime import datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
import urllib.request, urllib.error, ssl

# ── Path discovery ────────────────────────────────────────────────────────────

GLOBAL_DIR = Path.home() / ".claude"
SCRIPT_DIR = Path(__file__).resolve().parent
STATIC_DIR = SCRIPT_DIR / "static"
PORT = 9191
SERVER_START_TIME = time.time()

def _find_appdata_claude():
    """Find Claude AppData/Application Support dir — cross-platform."""
    system = platform.system()

    if system == "Darwin":  # macOS
        candidates = [
            Path.home() / "Library" / "Application Support" / "Claude",
        ]
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        candidates = [
            Path(appdata) / "Claude" if appdata else None,
            Path.home() / "AppData" / "Roaming" / "Claude",
        ]
        candidates = [c for c in candidates if c]
    else:  # Linux / other
        xdg = os.environ.get("XDG_CONFIG_HOME", "")
        candidates = [
            Path(xdg) / "Claude" if xdg else None,
            Path.home() / ".config" / "Claude",
        ]
        candidates = [c for c in candidates if c]

    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]  # best guess even if missing

def _find_project_dir():
    """Find project .claude/ dir: --project arg, or walk up from cwd."""
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--project" and i < len(sys.argv) - 1:
            p = Path(sys.argv[i + 1]) / ".claude"
            if p.is_dir():
                return p
    # Walk up from script dir
    d = SCRIPT_DIR
    while d != d.parent:
        candidate = d / ".claude"
        if candidate.is_dir() and (candidate / "settings.local.json").exists():
            return candidate
        d = d.parent
    return None

PROJECT_DIR = _find_project_dir()
_APPDATA_CLAUDE = _find_appdata_claude()
SESSIONS_DIRS = [
    _APPDATA_CLAUDE / "claude-code-sessions",
    _APPDATA_CLAUDE / "local-agent-mode-sessions",
]

# ── MIME types ────────────────────────────────────────────────────────────────

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".js":   "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".svg":  "image/svg+xml",
    ".ico":  "image/x-icon",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
}

# ── Cowork connector metadata ────────────────────────────────────────────────

COWORK_CONNECTORS = [
    {"id": "desktop-commander", "name": "Desktop Commander", "icon": "\U0001f5a5\ufe0f", "desc": "Read/write files & run processes", "cowork": True},
    {"id": "google-calendar",   "name": "Google Calendar",   "icon": "\U0001f4c5", "desc": "Manage calendar events & find free time", "cowork": True},
    {"id": "gmail",             "name": "Gmail",             "icon": "\U0001f4e7", "desc": "Read, search & draft emails", "cowork": True},
    {"id": "claude-in-chrome",  "name": "Claude in Chrome",  "icon": "\U0001f310", "desc": "Control Chrome browser for automation", "cowork": True},
    {"id": "stitch",            "name": "Stitch",            "icon": "\u270f\ufe0f", "desc": "Generate UI mockups from text", "cowork": True},
    {"id": "21st-magic",        "name": "21st.dev Magic",    "icon": "\u2728", "desc": "Build & refine React/UI components", "cowork": True},
    {"id": "microsoft-docs",    "name": "Microsoft Docs",    "icon": "\U0001f4d6", "desc": "Search Microsoft documentation", "cowork": True},
    {"id": "glance",            "name": "Glance",            "icon": "\U0001f50d", "desc": "Browser testing & visual QA", "cowork": True},
    {"id": "scheduled-tasks",   "name": "Scheduled Tasks",   "icon": "\U0001f5d3\ufe0f", "desc": "Create & manage automated tasks", "cowork": True},
    {"id": "canva",             "name": "Canva",             "icon": "\U0001f3a8", "desc": "Create & edit Canva designs", "cowork": False},
    {"id": "notebooklm",        "name": "NotebookLM",        "icon": "\U0001f4d3", "desc": "Query NotebookLM notebooks", "cowork": False},
    {"id": "computer-use",      "name": "Computer Use",      "icon": "\U0001f5b1\ufe0f", "desc": "Desktop mouse & keyboard control", "cowork": True},
    {"id": "nanobanana-mcp",    "name": "Nanobanana",        "icon": "\U0001f34c", "desc": "AI image generation via Gemini", "cowork": False},
]

COWORK_STATE_DEFAULTS = {c["id"]: False for c in COWORK_CONNECTORS}

# ── Default presets ───────────────────────────────────────────────────────────

DEFAULT_PRESETS = [
    {
        "id": "netscaler-citrix", "name": "NetScaler / Citrix Work", "icon": "\U0001f527",
        "desc": "Infrastructure, CLI, HA validation, Duo troubleshooting",
        "builtin": True,
        "cowork": {"desktop-commander": True, "microsoft-docs": True, "glance": True, "scheduled-tasks": True, "notebooklm": True},
        "mcps": {},
        "skills_global": {},
        "skills_project": {},
        "plugins": {},
    },
    {
        "id": "website-design", "name": "Website & Design", "icon": "\U0001f3a8",
        "desc": "Landing pages, HTML/CSS, UI mockups, image editing",
        "builtin": True,
        "cowork": {"desktop-commander": True, "claude-in-chrome": True, "stitch": True, "21st-magic": True, "glance": True, "canva": True},
        "mcps": {},
        "skills_global": {},
        "skills_project": {},
        "plugins": {},
    },
    {
        "id": "general", "name": "General / Minimal", "icon": "\u26a1",
        "desc": "Core Claude only — all extras disabled",
        "builtin": True,
        "cowork": {},
        "mcps": {},
        "skills_global": {},
        "skills_project": {},
        "plugins": {},
    },
]

# ── JSON helpers ──────────────────────────────────────────────────────────────

def _read_json(path, default=None):
    """Read a JSON file, return default on missing/corrupt."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default if default is not None else {}

def _write_json(path, data):
    """Write JSON with pretty-print, create parent dirs."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

# ── Path helpers ──────────────────────────────────────────────────────────────

def _decode_project_dir_name(name):
    """Convert ~/.claude/projects/ dir name to real path. 'C--Software' -> 'C:\\Software'"""
    # Format: 'C--Software' or 'C--Users-Kara' — first char is drive, -- separates drive from path, - separates path segments
    if len(name) >= 3 and name[0].isalpha() and name[1:3] == "--":
        drive = name[0].upper()
        rest = name[3:].replace("-", "\\")
        return f"{drive}:\\{rest}"
    return name

def get_projects():
    """List available projects from ~/.claude/projects/."""
    projects_dir = GLOBAL_DIR / "projects"
    if not projects_dir.is_dir():
        return []
    result = []
    for d in sorted(projects_dir.iterdir()):
        if d.is_dir():
            real_path = _decode_project_dir_name(d.name)
            project_claude = Path(real_path) / ".claude"
            result.append({"id": d.name, "path": real_path, "has_settings": (project_claude / "settings.local.json").exists()})
    return result

# ── Dashboard endpoints ───────────────────────────────────────────────────────

def get_dashboard_stats():
    """Build fresh dashboard stats from session files, supplemented by stats-cache."""
    cache = _read_json(GLOBAL_DIR / "stats-cache.json") or {}

    # ── Scan all session files for live data ──────────────────────────────
    day_msgs    = {}   # date_str -> {messageCount, toolCallCount}
    day_tokens  = {}   # date_str -> {model -> outputTokens}
    model_totals = {}  # model -> {inputTokens, outputTokens, ...}
    hour_counts = {}
    total_msgs  = 0
    first_ts    = None
    longest     = None

    for d in SESSIONS_DIRS:
        if not d.is_dir():
            continue
        try:
            for jp in d.rglob("local_*.json"):
                try:
                    data = json.loads(jp.read_text(encoding="utf-8"))
                except Exception:
                    continue

                created_ms = data.get("createdAt") or data.get("lastActivityAt") or 0
                if not created_ms:
                    # Fall back to file mtime in milliseconds
                    created_ms = int(jp.stat().st_mtime * 1000)

                turns = data.get("completedTurns", 0)
                model = data.get("model", "unknown")

                if not created_ms:
                    continue

                ts_sec = created_ms / 1000
                dt = datetime.fromtimestamp(ts_sec)
                date_str = dt.strftime("%Y-%m-%d")
                hour = dt.hour

                # Daily activity
                slot = day_msgs.setdefault(date_str, {"date": date_str, "messageCount": 0, "toolCallCount": 0})
                slot["messageCount"] += turns * 2  # approx: each turn = 1 user + 1 assistant
                total_msgs += turns * 2

                # Hour histogram
                hour_counts[hour] = hour_counts.get(hour, 0) + 1

                # Per-model token tracking (use cache data if available for accuracy)
                tok_slot = day_tokens.setdefault(date_str, {})
                # We don't have per-session token counts in session files, just track model presence
                tok_slot[model] = tok_slot.get(model, 0)

                # Model totals (basic)
                mt = model_totals.setdefault(model, {"inputTokens": 0, "outputTokens": 0,
                                                      "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0})

                # Longest session
                if longest is None or turns > longest.get("messageCount", 0):
                    longest = {"sessionId": data.get("sessionId", ""), "messageCount": turns}

                # First session date
                if first_ts is None or ts_sec < first_ts:
                    first_ts = ts_sec
        except OSError:
            pass

    # ── Merge cache token data where available ────────────────────────────
    # Use cache's modelUsage totals (accurate) if present
    if cache.get("modelUsage"):
        model_totals = cache["modelUsage"]

    # Merge daily token data from cache (accurate) with session-derived date coverage
    cache_daily_tokens = {d["date"]: d for d in cache.get("dailyModelTokens", [])}
    for date_str in sorted(day_tokens.keys()):
        if date_str in cache_daily_tokens:
            day_tokens[date_str] = cache_daily_tokens[date_str].get("tokensByModel", day_tokens[date_str])
        else:
            day_tokens[date_str] = {}

    # Build sorted daily activity list (all dates we know about)
    all_dates = sorted(set(list(day_msgs.keys()) + list(cache_daily_tokens.keys())))

    # For dates only in cache, pull from cache
    cache_daily_msgs = {d["date"]: d for d in cache.get("dailyActivity", [])}
    daily_activity = []
    for date_str in all_dates:
        if date_str in day_msgs:
            daily_activity.append(day_msgs[date_str])
        elif date_str in cache_daily_msgs:
            daily_activity.append(cache_daily_msgs[date_str])

    daily_model_tokens = [
        {"date": d, "tokensByModel": day_tokens.get(d, {})}
        for d in all_dates
    ]

    total_sessions = sum(
        sum(1 for _ in sd.rglob("local_*.json"))
        for sd in SESSIONS_DIRS if sd.is_dir()
    )

    return {
        "totalSessions": total_sessions,
        "totalMessages": cache.get("totalMessages", total_msgs),
        "firstSessionDate": datetime.fromtimestamp(first_ts).isoformat() if first_ts else cache.get("firstSessionDate"),
        "longestSession": longest or cache.get("longestSession"),
        "hourCounts": hour_counts or cache.get("hourCounts", {}),
        "modelUsage": model_totals,
        "dailyActivity": daily_activity,
        "dailyModelTokens": daily_model_tokens,
    }

_rate_limit_cache = {"data": None, "time": 0}

def get_rate_limits():
    """Proxy rate limit request to Anthropic API using local OAuth token."""
    now = time.time()
    if _rate_limit_cache["data"] and (now - _rate_limit_cache["time"]) < 30:
        return _rate_limit_cache["data"]

    creds = _read_json(GLOBAL_DIR / ".credentials.json")
    oauth = creds.get("claudeAiOauth", {})
    token = oauth.get("accessToken", "")
    if not token:
        return {"error": "No OAuth token found in .credentials.json"}

    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            "https://api.anthropic.com/api/oauth/usage",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _rate_limit_cache["data"] = data
            _rate_limit_cache["time"] = now
            return data
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}

# ── Settings endpoints ────────────────────────────────────────────────────────

def get_global_settings():
    return _read_json(GLOBAL_DIR / "settings.json")

def save_global_settings(data):
    _write_json(GLOBAL_DIR / "settings.json", data)

def get_project_settings():
    if not PROJECT_DIR:
        return {"error": "No project directory found"}
    return _read_json(PROJECT_DIR / "settings.local.json", {"permissions": {"allow": []}})

def save_project_settings(data):
    if not PROJECT_DIR:
        return {"error": "No project directory found"}
    _write_json(PROJECT_DIR / "settings.local.json", data)

def get_mcp_servers():
    """List MCP servers from global settings with metadata."""
    gs = get_global_settings()
    servers = gs.get("mcpServers", {})
    result = []
    for name, config in servers.items():
        result.append({
            "name": name,
            "command": config.get("command", ""),
            "args": config.get("args", []),
            "env_count": len(config.get("env", {})),
            "config": config,
        })
    return result

def toggle_project_permission(entry, enable):
    """Add or remove a permission entry in project settings."""
    settings = get_project_settings()
    if isinstance(settings, dict) and "error" in settings:
        return settings
    perms = settings.setdefault("permissions", {}).setdefault("allow", [])
    if enable and entry not in perms:
        perms.append(entry)
    elif not enable:
        settings["permissions"]["allow"] = [p for p in perms if p != entry]
    save_project_settings(settings)
    return {"ok": True}

# ── Skills endpoints ──────────────────────────────────────────────────────────

def _parse_skill_md(path):
    """Parse SKILL.md for frontmatter name/description."""
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return {}, ""

    frontmatter = {}
    body_lines = []
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    frontmatter[key.strip()] = val.strip().strip('"').strip("'")
            body_lines = parts[2].strip().splitlines()
    else:
        body_lines = text.strip().splitlines()

    # First non-empty, non-header line as description fallback
    desc = frontmatter.get("description", "")
    if not desc:
        for line in body_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                desc = stripped[:200]
                break
    return frontmatter, desc

def get_global_skills():
    """Scan ~/.claude/skills/ and skills-disabled/ for global skills."""
    skills_dir = GLOBAL_DIR / "skills"
    disabled_dir = GLOBAL_DIR / "skills-disabled"
    result = []

    for d in (skills_dir, disabled_dir):
        if not d.is_dir():
            continue
        enabled = (d == skills_dir)
        for child in sorted(d.iterdir()):
            if not child.is_dir():
                continue
            skill_file = child / "SKILL.md"
            if not skill_file.exists():
                skill_file = child / "SKILL.md.disabled"
            fm, desc = _parse_skill_md(skill_file) if skill_file.exists() else ({}, "")
            result.append({
                "id": child.name,
                "name": fm.get("name", child.name.replace("-", " ").title()),
                "enabled": enabled,
                "desc": desc,
                "icon": fm.get("icon", ""),
                "scope": "global",
            })
    return result

def toggle_global_skill(skill_id, enable):
    """Move skill dir between skills/ and skills-disabled/."""
    skills_dir = GLOBAL_DIR / "skills"
    disabled_dir = GLOBAL_DIR / "skills-disabled"

    if enable:
        src = disabled_dir / skill_id
        dst = skills_dir / skill_id
    else:
        src = skills_dir / skill_id
        dst = disabled_dir / skill_id

    if not src.is_dir():
        return {"ok": False, "error": f"Skill directory not found: {src}"}

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return {"ok": True}

def get_project_skills():
    """Scan project .claude/skills/ for project-level skills."""
    if not PROJECT_DIR:
        return []
    skills_dir = PROJECT_DIR / "skills"
    if not skills_dir.is_dir():
        return []
    result = []
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_file = child / "SKILL.md"
        disabled_file = child / "SKILL.md.disabled"
        enabled = skill_file.exists()
        active_file = skill_file if enabled else disabled_file
        fm, desc = _parse_skill_md(active_file) if active_file.exists() else ({}, "")
        result.append({
            "id": child.name,
            "name": fm.get("name", child.name.replace("-", " ").title()),
            "enabled": enabled,
            "desc": desc,
            "icon": fm.get("icon", ""),
            "scope": "project",
        })
    return result

def toggle_project_skill(skill_id, enable):
    """Toggle project skill via SKILL.md rename."""
    if not PROJECT_DIR:
        return {"ok": False, "error": "No project directory"}
    skill_dir = PROJECT_DIR / "skills" / skill_id
    if not skill_dir.is_dir():
        return {"ok": False, "error": f"Skill not found: {skill_id}"}

    src = skill_dir / ("SKILL.md.disabled" if enable else "SKILL.md")
    dst = skill_dir / ("SKILL.md" if enable else "SKILL.md.disabled")
    if src.exists():
        src.rename(dst)
        return {"ok": True}
    return {"ok": False, "error": f"Source file not found: {src}"}

# ── Plugins endpoints ─────────────────────────────────────────────────────────

def get_plugins():
    """Merge installed plugins, enabled state, blocklist, and marketplaces."""
    installed = _read_json(GLOBAL_DIR / "plugins" / "installed_plugins.json", {"plugins": {}})
    gs = get_global_settings()
    enabled_map = gs.get("enabledPlugins", {})
    blocklist = _read_json(GLOBAL_DIR / "plugins" / "blocklist.json", {"plugins": []})
    marketplaces_file = _read_json(GLOBAL_DIR / "plugins" / "known_marketplaces.json", {})
    extra_mkts = gs.get("extraKnownMarketplaces", {})

    plugins = []
    for pid, versions in installed.get("plugins", {}).items():
        info = versions[0] if versions else {}
        name_parts = pid.split("@")
        plugins.append({
            "id": pid,
            "name": name_parts[0] if name_parts else pid,
            "marketplace": name_parts[1] if len(name_parts) > 1 else "unknown",
            "version": info.get("version", "unknown"),
            "scope": info.get("scope", "user"),
            "installedAt": info.get("installedAt", ""),
            "lastUpdated": info.get("lastUpdated", ""),
            "enabled": enabled_map.get(pid, True),
        })

    blocked = blocklist.get("plugins", [])

    mkts = {}
    for name, data in {**marketplaces_file, **extra_mkts}.items():
        source = data.get("source", data)
        mkts[name] = {
            "name": name,
            "sourceType": source.get("source", "unknown"),
            "repo": source.get("repo", source.get("url", "")),
            "lastUpdated": data.get("lastUpdated", ""),
        }

    return {"plugins": plugins, "blocklist": blocked, "marketplaces": mkts}

def toggle_plugin(plugin_id, enable):
    """Toggle enabledPlugins in global settings.json."""
    gs = get_global_settings()
    ep = gs.setdefault("enabledPlugins", {})
    ep[plugin_id] = enable
    save_global_settings(gs)
    return {"ok": True}

# ── Connectors endpoints ─────────────────────────────────────────────────────

def _parse_connector_name(server_name):
    """Parse 'plugin:design:notion|abc123' -> 'Notion'."""
    name = server_name.split("|")[0]  # strip instance ID
    parts = name.split(":")
    if len(parts) >= 3:
        return parts[-1].replace("-", " ").title()
    return name.replace("-", " ").title()

def get_connectors():
    """Merge OAuth status, auth-cache, and cowork state."""
    creds = _read_json(GLOBAL_DIR / ".credentials.json")
    auth_cache = _read_json(GLOBAL_DIR / "mcp-needs-auth-cache.json")
    cowork_state = get_cowork_state()

    # OAuth connectors from credentials
    oauth_entries = creds.get("mcpOAuth", {})
    oauth_connectors = []
    if isinstance(oauth_entries, dict):
        for server_name, entry in oauth_entries.items():
            if isinstance(entry, dict):
                has_token = bool(entry.get("accessToken"))
                expires = entry.get("expiresAt", 0)
                is_valid = has_token and (expires > time.time() * 1000 if expires else False)
                oauth_connectors.append({
                    "serverName": server_name,
                    "displayName": _parse_connector_name(server_name),
                    "authenticated": is_valid,
                    "hasToken": has_token,
                    "needsAuth": server_name in auth_cache or any(
                        server_name.startswith(k) for k in auth_cache
                    ),
                })

    # Cowork connectors with state
    cowork_list = []
    for c in COWORK_CONNECTORS:
        cowork_list.append({
            **c,
            "active": cowork_state.get(c["id"], False),
        })

    return {"oauth": oauth_connectors, "cowork": cowork_list}

def get_cowork_state():
    """Read cowork-state.json."""
    if not PROJECT_DIR:
        return COWORK_STATE_DEFAULTS.copy()
    state = _read_json(PROJECT_DIR / "cowork-state.json")
    if not state:
        return COWORK_STATE_DEFAULTS.copy()
    return state

def toggle_cowork(connector_id, active):
    """Toggle a cowork connector state."""
    if not PROJECT_DIR:
        return {"ok": False, "error": "No project directory"}
    state = get_cowork_state()
    state[connector_id] = active
    _write_json(PROJECT_DIR / "cowork-state.json", state)
    return {"ok": True}

# ── Sessions endpoints ────────────────────────────────────────────────────────

def _parse_ts(val):
    """Convert timestamp to milliseconds int."""
    if isinstance(val, (int, float)):
        return int(val) if val > 1e12 else int(val * 1000)
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except (ValueError, OSError):
            return 0
    return 0

def get_sessions():
    """Discover Claude Code sessions from AppData (resilient rglob scan)."""
    sessions = []
    seen_ids = set()
    for sessions_root in SESSIONS_DIRS:
        if not sessions_root.is_dir():
            continue
        try:
            for jp in sessions_root.rglob("local_*.json"):
                # Accept files 2-4 levels deep (UUID/UUID/local_*.json)
                try:
                    depth = len(jp.relative_to(sessions_root).parts)
                except ValueError:
                    continue
                if depth < 2 or depth > 4:
                    continue
                try:
                    data = json.loads(jp.read_text(encoding="utf-8"))
                    sid = jp.stem.replace("local_", "")
                    if sid in seen_ids:
                        continue
                    seen_ids.add(sid)
                    sessions.append({
                        "id": sid,
                        "title": data.get("title", data.get("initialMessage", sid))[:120],
                        "created": _parse_ts(data.get("createdAt", 0)),
                        "lastActivity": _parse_ts(data.get("lastActivityAt", 0)),
                        "archived": data.get("isArchived", False),
                        "model": data.get("model", ""),
                        "cwd": data.get("cwd", ""),
                        "jsonPath": str(jp),
                        "folderPath": str(jp.parent / sid) if (jp.parent / sid).is_dir() else "",
                    })
                except (json.JSONDecodeError, OSError, ValueError):
                    continue
        except OSError:
            pass
    sessions.sort(key=lambda s: s["lastActivity"], reverse=True)
    return sessions

def delete_sessions(ids):
    """Delete session files and folders."""
    all_sessions = get_sessions()
    session_map = {s["id"]: s for s in all_sessions}
    deleted = 0
    for sid in ids:
        s = session_map.get(sid)
        if not s:
            continue
        try:
            jp = Path(s["jsonPath"])
            if jp.exists():
                jp.unlink()
            if s["folderPath"]:
                fp = Path(s["folderPath"])
                if fp.is_dir():
                    shutil.rmtree(fp, ignore_errors=True)
            deleted += 1
        except OSError:
            continue
    return {"ok": True, "deleted": deleted}

# ── Presets endpoints ─────────────────────────────────────────────────────────

def _presets_file():
    if PROJECT_DIR:
        return PROJECT_DIR / "presets.json"
    return GLOBAL_DIR / "presets.json"

def get_presets():
    presets = _read_json(_presets_file(), [])
    if not presets:
        presets = DEFAULT_PRESETS[:]
        _write_json(_presets_file(), presets)
    return presets

def snapshot_preset(name, icon, desc):
    """Capture current full state as a new preset."""
    presets = get_presets()
    cowork = get_cowork_state()

    new_preset = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "icon": icon or "\u2b50",
        "desc": desc or "",
        "builtin": False,
        "cowork": cowork,
        "mcps": {},
        "skills_global": {s["id"]: s["enabled"] for s in get_global_skills()},
        "skills_project": {s["id"]: s["enabled"] for s in get_project_skills()},
        "plugins": {},
    }

    # Capture plugin states
    gs = get_global_settings()
    new_preset["plugins"] = gs.get("enabledPlugins", {}).copy()

    presets.append(new_preset)
    _write_json(_presets_file(), presets)
    return new_preset

def load_preset(preset_id):
    """Apply a preset across all config domains."""
    presets = get_presets()
    preset = next((p for p in presets if p["id"] == preset_id), None)
    if not preset:
        return {"ok": False, "error": "Preset not found"}

    # Apply cowork state
    if preset.get("cowork") and PROJECT_DIR:
        _write_json(PROJECT_DIR / "cowork-state.json", preset["cowork"])

    # Apply global skills
    if preset.get("skills_global"):
        for skill_id, should_enable in preset["skills_global"].items():
            current = next((s for s in get_global_skills() if s["id"] == skill_id), None)
            if current and current["enabled"] != should_enable:
                toggle_global_skill(skill_id, should_enable)

    # Apply project skills
    if preset.get("skills_project"):
        for skill_id, should_enable in preset["skills_project"].items():
            current = next((s for s in get_project_skills() if s["id"] == skill_id), None)
            if current and current["enabled"] != should_enable:
                toggle_project_skill(skill_id, should_enable)

    # Apply plugin states
    if preset.get("plugins"):
        gs = get_global_settings()
        gs["enabledPlugins"] = preset["plugins"]
        save_global_settings(gs)

    return {"ok": True}

def delete_preset(preset_id):
    presets = get_presets()
    presets = [p for p in presets if p["id"] != preset_id]
    _write_json(_presets_file(), presets)
    return {"ok": True}

# ── Server control ───────────────────────────────────────────────────────────

_server_instance = None  # set in main()

def shutdown_server():
    """Force-exit after brief delay so HTTP response gets sent first."""
    def _exit():
        time.sleep(0.4)
        os._exit(0)
    threading.Thread(target=_exit, daemon=True).start()
    return {"ok": True}

def restart_claude_desktop():
    """Kill Claude Desktop and relaunch — cross-platform."""
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["pkill", "-x", "Claude"], capture_output=True)
            time.sleep(1.5)
            subprocess.Popen(["open", "-a", "Claude"])
        elif system == "Windows":
            # Kill only the WindowsApps (Store) Claude, not the CLI
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Process -Name 'claude' -ErrorAction SilentlyContinue | "
                 "Where-Object { $_.Path -like '*WindowsApps*' } | "
                 "Stop-Process -Force"],
                capture_output=True, timeout=10
            )
            time.sleep(1.5)
            subprocess.Popen(
                ["explorer.exe", "shell:AppsFolder\\Claude_pzs8sxrjxfjjc!Claude"],
                creationflags=subprocess.DETACHED_PROCESS
            )
        else:  # Linux
            subprocess.run(["pkill", "-x", "claude"], capture_output=True)
            time.sleep(1.5)
            subprocess.Popen(["claude-desktop"])
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_server_status():
    """Return server health, uptime, session counts, and config file status."""
    uptime_sec = int(time.time() - SERVER_START_TIME)
    hrs, rem = divmod(uptime_sec, 3600)
    mins, secs = divmod(rem, 60)
    uptime_str = f"{hrs}h {mins}m {secs}s" if hrs else (f"{mins}m {secs}s" if mins else f"{secs}s")

    # Quick session count — count top-level UUID dirs (one per session, instant)
    total_files = 0
    for d in SESSIONS_DIRS:
        if d.is_dir():
            try:
                total_files += sum(1 for e in d.iterdir() if e.is_dir())
            except OSError:
                pass

    # Config file status
    config_files = {
        "global_settings":  (GLOBAL_DIR / "settings.json").is_file(),
        "credentials":      (GLOBAL_DIR / ".credentials.json").is_file(),
        "stats_cache":      (GLOBAL_DIR / "stats-cache.json").is_file(),
        "project_settings": bool(PROJECT_DIR and (PROJECT_DIR / "settings.local.json").is_file()),
        "cowork_state":     bool(PROJECT_DIR and (PROJECT_DIR / "cowork-state.json").is_file()),
    }

    sessions_dirs_info = [{"path": str(d), "exists": d.is_dir()} for d in SESSIONS_DIRS]

    return {
        "uptime_str": uptime_str,
        "uptime_seconds": uptime_sec,
        "session_files": total_files,
        "config_files": config_files,
        "sessions_dirs": sessions_dirs_info,
        "python_version": platform.python_version(),
        "port": PORT,
        "appdata_claude": str(_APPDATA_CLAUDE),
    }

# ── HTTP Server ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Silence default logging

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath):
        try:
            resolved = filepath.resolve()
            static_resolved = STATIC_DIR.resolve()
            if not str(resolved).startswith(str(static_resolved)):
                self.send_error(403, "Forbidden")
                return
            if not resolved.is_file():
                self.send_error(404, "Not Found")
                return
            content = resolved.read_bytes()
            mime = MIME_TYPES.get(resolved.suffix.lower(), "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", len(content))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except OSError:
            self.send_error(500, "Internal Server Error")

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        # Redirect root to index
        if path == "/" or path == "":
            self.send_response(302)
            self.send_header("Location", "/static/index.html")
            self.end_headers()
            return

        # Static files
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._send_file(STATIC_DIR / rel)
            return

        # API routes
        routes = {
            "/api/config/paths": lambda: {
                "global": str(GLOBAL_DIR),
                "project": str(PROJECT_DIR) if PROJECT_DIR else None,
                "sessions": [str(d) for d in SESSIONS_DIRS],
            },
            "/api/projects": get_projects,
            "/api/dashboard/stats": get_dashboard_stats,
            "/api/dashboard/rate-limits": get_rate_limits,
            "/api/settings/global": get_global_settings,
            "/api/settings/project": get_project_settings,
            "/api/settings/mcp-servers": get_mcp_servers,
            "/api/skills/global": get_global_skills,
            "/api/skills/project": get_project_skills,
            "/api/plugins": get_plugins,
            "/api/connectors": get_connectors,
            "/api/sessions": get_sessions,
            "/api/presets": get_presets,
            "/api/server/status": get_server_status,
        }

        handler = routes.get(path)
        if handler:
            try:
                self._send_json(handler())
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        try:
            if path == "/api/config/project":
                global PROJECT_DIR
                pid = body.get("project", "")
                candidate = GLOBAL_DIR / "projects" / pid
                if candidate.is_dir():
                    real_path = _decode_project_dir_name(pid)
                    PROJECT_DIR = Path(real_path) / ".claude"
                    self._send_json({"ok": True, "project": str(PROJECT_DIR)})
                else:
                    self._send_json({"ok": False, "error": "Project not found"}, 404)

            elif path == "/api/settings/global":
                save_global_settings(body)
                self._send_json({"ok": True})

            elif path == "/api/settings/project":
                save_project_settings(body)
                self._send_json({"ok": True})

            elif path == "/api/settings/permissions/project/toggle":
                result = toggle_project_permission(body.get("entry", ""), body.get("enable", True))
                self._send_json(result)

            elif path == "/api/skills/global/toggle":
                result = toggle_global_skill(body.get("id", ""), body.get("enable", True))
                self._send_json(result)

            elif path == "/api/skills/project/toggle":
                result = toggle_project_skill(body.get("id", ""), body.get("enable", True))
                self._send_json(result)

            elif path == "/api/plugins/toggle":
                result = toggle_plugin(body.get("id", ""), body.get("enable", True))
                self._send_json(result)

            elif path == "/api/connectors/cowork/toggle":
                result = toggle_cowork(body.get("id", ""), body.get("active", True))
                self._send_json(result)

            elif path == "/api/sessions/delete":
                result = delete_sessions(body.get("ids", []))
                self._send_json(result)

            elif path == "/api/presets/snapshot":
                result = snapshot_preset(body.get("name", ""), body.get("icon", ""), body.get("desc", ""))
                self._send_json(result)

            elif path == "/api/presets/load":
                result = load_preset(body.get("id", ""))
                self._send_json(result)

            elif path == "/api/presets/delete":
                result = delete_preset(body.get("id", ""))
                self._send_json(result)

            elif path == "/api/server/shutdown":
                self._send_json({"ok": True, "message": "Server shutting down..."})
                shutdown_server()

            elif path == "/api/claude/restart":
                result = restart_claude_desktop()
                self._send_json(result)

            else:
                self.send_error(404, "Not Found")

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

# ── Main ──────────────────────────────────────────────────────────────────────

def _kill_stale_server():
    """Kill any process already listening on PORT so a fresh start always works."""
    killed = []
    try:
        # Windows: use netstat (works without admin rights)
        if platform.system() == "Windows":
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL
            )
            pids = set()
            for line in out.splitlines():
                if f":{PORT} " in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        try:
                            pids.add(int(parts[-1]))
                        except ValueError:
                            pass
            for pid in pids:
                if pid and pid != os.getpid():
                    try:
                        subprocess.run(
                            ["powershell", "-NoProfile", "-Command",
                             f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
                            capture_output=True
                        )
                        killed.append(pid)
                    except Exception:
                        pass
        else:
            # macOS/Linux: lsof
            out = subprocess.check_output(
                ["lsof", "-ti", f"tcp:{PORT}"], text=True, stderr=subprocess.DEVNULL
            ).strip()
            for pid_str in out.splitlines():
                try:
                    pid = int(pid_str)
                    if pid != os.getpid():
                        os.kill(pid, 9)
                        killed.append(pid)
                except Exception:
                    pass
    except Exception:
        pass
    if killed:
        print(f"  Stopped old instance(s): PID {', '.join(str(p) for p in killed)}")
        time.sleep(0.8)

def main():
    _kill_stale_server()

    print()
    print("  Claude Tool Manager v2")
    print(f"  Global config:  {GLOBAL_DIR}")
    print(f"  Project config: {PROJECT_DIR or '(none)'}")
    print(f"  Sessions dirs:  {', '.join(str(d) for d in SESSIONS_DIRS)}")
    print(f"  Static files:   {STATIC_DIR}")
    print()

    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True

    global _server_instance
    try:
        server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
        _server_instance = server
    except OSError as e:
        print(f"  ERROR: Could not bind port {PORT}: {e}")
        sys.exit(1)

    url = f"http://localhost:{PORT}"
    print(f"  Listening on {url}")
    print("  Press Ctrl+C to stop.")
    print()

    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
        server.server_close()

if __name__ == "__main__":
    main()
