#!/usr/bin/env python3
"""
Claude Tool Manager
Manage Claude Code skills & MCP permissions, with Cowork guidance and session presets.
Run with: python tool-manager.py
Then open: http://localhost:9191
"""

import json, os, re, shutil, sys, uuid, webbrowser
from datetime import datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# ── Config paths ──────────────────────────────────────────────────────────────
SKILLS_DIR        = Path(r"C:\Software\.claude\skills")
SETTINGS_FILE     = Path(r"C:\Software\.claude\settings.local.json")
COWORK_STATE_FILE = Path(r"C:\Software\.claude\cowork-state.json")
PRESETS_FILE      = Path(r"C:\Software\.claude\presets.json")
GLOBAL_SETTINGS_FILE = Path.home() / ".claude" / "settings.json"
SESSIONS_ROOT = Path(os.environ.get("APPDATA", "")) / "Claude" / "local-agent-mode-sessions"
PORT = 9191

# ── Known MCPs ────────────────────────────────────────────────────────────────
KNOWN_MCPS = {
    "mcp__glance":            {"name": "Glance",           "icon": "🔍", "desc": "Automated browser testing & visual QA"},
    "mcp__claude_ai_Canva":   {"name": "Canva",            "icon": "🎨", "desc": "Create, edit & generate Canva designs"},
    "mcp__notebooklm-mcp":    {"name": "NotebookLM",       "icon": "📓", "desc": "Query your Google NotebookLM notebooks"},
    "mcp__Desktop_Commander": {"name": "Desktop Commander","icon": "🖥️", "desc": "Read/write files & run processes on your PC"},
    "mcp__stitch":            {"name": "Stitch",           "icon": "✏️", "desc": "Generate UI screen mockups from text"},
    "mcp___21st-dev_magic":   {"name": "21st.dev Magic",   "icon": "✨", "desc": "Build & refine React/UI components"},
    "mcp__bf349c11":          {"name": "Microsoft Docs",   "icon": "📖", "desc": "Search Microsoft documentation"},
    "mcp__scheduled-tasks":   {"name": "Scheduled Tasks",  "icon": "🗓️", "desc": "Create & manage automated tasks"},
    "mcp__session_info":      {"name": "Session Info",     "icon": "💬", "desc": "Browse & read previous Cowork sessions"},
    "mcp__cowork":            {"name": "Cowork Tools",     "icon": "🤝", "desc": "File delete, present files, request directory"},
    "mcp__mcp-registry":      {"name": "MCP Registry",     "icon": "🔌", "desc": "Search & install new MCP connectors"},
    "mcp__plugins":           {"name": "Plugins",          "icon": "🧩", "desc": "Search & install Cowork plugins"},
    "mcp__4904f7a1":          {"name": "Google Calendar",  "icon": "📅", "desc": "Manage calendar events & find free time"},
    "mcp__78178dcd":          {"name": "Gmail",            "icon": "📧", "desc": "Read, search & draft emails"},
    "mcp__Claude_in_Chrome":  {"name": "Claude in Chrome", "icon": "🌐", "desc": "Control Chrome browser for automation"},
}

# ── Cowork connectors ─────────────────────────────────────────────────────────
COWORK_CONNECTORS = [
    {"id": "desktop-commander", "name": "Desktop Commander", "icon": "🖥️", "desc": "Read/write files & run processes on your PC",   "how": "Settings → Connectors → Desktop Commander → Enable",              "cowork": True},
    {"id": "google-calendar",   "name": "Google Calendar",   "icon": "📅", "desc": "Manage calendar events & find free time",         "how": "Settings → Connectors → Google Calendar → Connect Google Account", "cowork": True},
    {"id": "gmail",             "name": "Gmail",             "icon": "📧", "desc": "Read, search & draft emails",                    "how": "Settings → Connectors → Gmail → Connect Google Account",           "cowork": True},
    {"id": "claude-in-chrome",  "name": "Claude in Chrome",  "icon": "🌐", "desc": "Control your Chrome browser for automation",     "how": "Settings → Connectors → Claude in Chrome → Enable",               "cowork": True},
    {"id": "stitch",            "name": "Stitch",            "icon": "✏️", "desc": "Generate UI mockups from text descriptions",     "how": "Settings → Connectors → Stitch → Enable",                        "cowork": True},
    {"id": "21st-magic",        "name": "21st.dev Magic",    "icon": "✨", "desc": "Build & refine React/UI components",             "how": "Settings → Connectors → 21st.dev → Enable",                       "cowork": True},
    {"id": "microsoft-docs",    "name": "Microsoft Docs",    "icon": "📖", "desc": "Search Microsoft documentation",                 "how": "Settings → Connectors → Microsoft Docs → Enable",                 "cowork": True},
    {"id": "glance",            "name": "Glance",            "icon": "🔍", "desc": "Automated browser testing & visual QA",          "how": "Settings → Connectors → Glance → Enable",                         "cowork": True},
    {"id": "scheduled-tasks",   "name": "Scheduled Tasks",   "icon": "🗓️", "desc": "Create & manage automated tasks",               "how": "Settings → Connectors → Scheduled Tasks → Enable",                "cowork": True},
    {"id": "canva",             "name": "Canva",             "icon": "🎨", "desc": "Create, edit & generate Canva designs",          "how": "Available via the Code tab in this same Claude desktop app",       "cowork": False},
    {"id": "notebooklm",        "name": "NotebookLM",        "icon": "📓", "desc": "Query your Google NotebookLM notebooks",         "how": "Available via the Code tab in this same Claude desktop app",       "cowork": False},
]

COWORK_STATE_DEFAULTS = {
    "desktop-commander": True, "google-calendar": True, "gmail": True,
    "claude-in-chrome": True,  "stitch": True,          "21st-magic": True,
    "microsoft-docs": True,    "glance": True,           "scheduled-tasks": True,
    "canva": False,            "notebooklm": False,
}

# ── Starter presets ───────────────────────────────────────────────────────────
DEFAULT_PRESETS = [
    {
        "id": "netscaler-citrix",
        "name": "NetScaler / Citrix Work",
        "icon": "🔧",
        "desc": "Infrastructure & NetScaler config, CLI work, HA validation, Duo/JWT troubleshooting",
        "cowork": {
            "desktop-commander": True,  "google-calendar": False, "gmail": False,
            "claude-in-chrome": False,  "stitch": False,          "21st-magic": False,
            "microsoft-docs": True,     "glance": True,           "scheduled-tasks": True,
            "canva": False,             "notebooklm": True,
        },
        "mcps": {
            "mcp__Desktop_Commander": True,  "mcp__bf349c11": True,
            "mcp__glance": True,             "mcp__notebooklm-mcp": True,
            "mcp__scheduled-tasks": True,    "mcp__session_info": True,
            "mcp__cowork": True,             "mcp__mcp-registry": False,
            "mcp__plugins": False,           "mcp__4904f7a1": False,
            "mcp__78178dcd": False,          "mcp__Claude_in_Chrome": False,
            "mcp__stitch": False,            "mcp___21st-dev_magic": False,
            "mcp__claude_ai_Canva": False,
        },
        "skills": {"ui-ux-pro-max": False},
    },
    {
        "id": "website-design",
        "name": "Website & Design",
        "icon": "🎨",
        "desc": "Landing pages, performer sites, HTML/CSS work, image editing, UI mockups",
        "cowork": {
            "desktop-commander": True,  "google-calendar": False, "gmail": False,
            "claude-in-chrome": True,   "stitch": True,           "21st-magic": True,
            "microsoft-docs": False,    "glance": True,           "scheduled-tasks": False,
            "canva": True,              "notebooklm": False,
        },
        "mcps": {
            "mcp__Desktop_Commander": True,  "mcp__Claude_in_Chrome": True,
            "mcp__stitch": True,             "mcp___21st-dev_magic": True,
            "mcp__glance": True,             "mcp__claude_ai_Canva": True,
            "mcp__session_info": True,       "mcp__cowork": True,
            "mcp__mcp-registry": False,      "mcp__plugins": False,
            "mcp__4904f7a1": False,          "mcp__78178dcd": False,
            "mcp__bf349c11": False,          "mcp__notebooklm-mcp": False,
            "mcp__scheduled-tasks": False,
        },
        "skills": {"ui-ux-pro-max": True},
    },
    {
        "id": "general",
        "name": "Default (Bare Minimum)",
        "icon": "🌱",
        "desc": "Core Claude tools only — no external connectors. A clean slate to build from.",
        "cowork": {
            "desktop-commander": False, "google-calendar": False, "gmail": False,
            "claude-in-chrome": False,  "stitch": False,          "21st-magic": False,
            "microsoft-docs": False,    "glance": False,           "scheduled-tasks": False,
            "canva": False,             "notebooklm": False,
        },
        "mcps": {
            "mcp__Desktop_Commander":  False, "mcp__claude_ai_Canva":  False,
            "mcp__notebooklm-mcp":     False, "mcp__stitch":           False,
            "mcp___21st-dev_magic":    False, "mcp__bf349c11":         False,
            "mcp__scheduled-tasks":    False, "mcp__session_info":     True,
            "mcp__cowork":             True,  "mcp__mcp-registry":     True,
            "mcp__plugins":            True,  "mcp__4904f7a1":         False,
            "mcp__78178dcd":           False, "mcp__Claude_in_Chrome": False,
            "mcp__glance":             False,
        },
        "skills": {"ui-ux-pro-max": False},
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_settings():
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"permissions": {"allow": []}}

def write_settings(data):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def get_skills():
    skills = []
    if not SKILLS_DIR.exists():
        return skills
    for item in sorted(SKILLS_DIR.iterdir()):
        if not item.is_dir():
            continue
        skill_md       = item / "SKILL.md"
        skill_disabled = item / "SKILL.md.disabled"
        enabled  = skill_md.exists()
        if not (enabled or skill_disabled.exists()):
            continue
        src  = skill_md if enabled else skill_disabled
        desc = ""
        try:
            lines = src.read_text(encoding="utf-8", errors="ignore").splitlines()
            for i, line in enumerate(lines):
                if line.startswith("# ") and i == 0:
                    continue
                if line.strip() and not line.startswith("#"):
                    desc = line.strip()[:120]
                    break
        except Exception:
            pass
        skills.append({"id": item.name, "name": item.name.replace("-"," ").replace("_"," ").title(),
                        "enabled": enabled, "desc": desc})
    return skills

def toggle_skill(skill_id, enable):
    p   = SKILLS_DIR / skill_id
    md  = p / "SKILL.md"
    dis = p / "SKILL.md.disabled"
    if enable:
        if dis.exists(): dis.rename(md); return True, f"{skill_id} enabled"
        return False, "SKILL.md.disabled not found"
    else:
        if md.exists(): md.rename(dis); return True, f"{skill_id} disabled"
        return False, "SKILL.md not found"

def read_global_settings():
    """Read ~/.claude/settings.json (global Claude Code settings)."""
    if GLOBAL_SETTINGS_FILE.exists():
        try:
            return json.loads(GLOBAL_SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def get_mcp_permissions():
    """
    Auto-discover every installed MCP from:
      1. mcpServers keys in settings.local.json  (project-level)
      2. mcpServers keys in ~/.claude/settings.json  (global / user-installed)
      3. mcp__* entries already in permissions.allow
    Then enrich with KNOWN_MCPS metadata where available.
    Unknown MCPs appear with a generic icon so nothing is ever hidden.
    """
    local_cfg  = read_settings()
    global_cfg = read_global_settings()

    # Collect all installed MCP server names -> normalise to mcp__<name> key
    installed_keys = set()
    for cfg in (local_cfg, global_cfg):
        for server_name in cfg.get("mcpServers", {}).keys():
            installed_keys.add("mcp__" + server_name)

    # Collect currently-enabled keys from permissions.allow
    allow = local_cfg.get("permissions", {}).get("allow", [])
    enabled_keys = set()
    for entry in allow:
        if entry.startswith("mcp__"):
            parts = entry.split("__")
            if len(parts) >= 2:
                enabled_keys.add("mcp__" + parts[1])

    # Union: KNOWN_MCPS + installed + enabled (so nothing is ever missing)
    all_keys = set(KNOWN_MCPS.keys()) | installed_keys | enabled_keys

    result = []
    for key in sorted(all_keys, key=lambda k: (KNOWN_MCPS.get(k, {}).get("name", k).lower())):
        if key in KNOWN_MCPS:
            meta = KNOWN_MCPS[key]
            result.append({"key": key, "name": meta["name"], "icon": meta["icon"],
                            "desc": meta["desc"], "enabled": key in enabled_keys})
        else:
            display = key.replace("mcp__", "").replace("_", " ").replace("-", " ").title()
            result.append({"key": key, "name": display, "icon": "🔧",
                            "desc": "MCP connector (auto-discovered)", "enabled": key in enabled_keys})
    return result

def toggle_mcp(mcp_key, enable):
    settings = read_settings()
    allow    = settings.setdefault("permissions", {}).setdefault("allow", [])
    wildcard = mcp_key + "__*"
    if enable:
        if wildcard not in allow: allow.append(wildcard)
    else:
        settings["permissions"]["allow"] = [e for e in allow if not e.startswith(mcp_key + "__")]
    write_settings(settings)
    return True, f"{mcp_key} {'enabled' if enable else 'disabled'}"

def get_cowork_state():
    if COWORK_STATE_FILE.exists():
        try:
            return json.loads(COWORK_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    COWORK_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COWORK_STATE_FILE.write_text(json.dumps(COWORK_STATE_DEFAULTS, indent=2), encoding="utf-8")
    return dict(COWORK_STATE_DEFAULTS)

def set_cowork_active(connector_id, active):
    state = get_cowork_state()
    state[connector_id] = active
    COWORK_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COWORK_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return True, f"{connector_id} marked {'active' if active else 'inactive'}"

# ── Preset helpers ────────────────────────────────────────────────────────────

def get_presets():
    if PRESETS_FILE.exists():
        try:
            return json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # First run — seed with defaults
    PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRESETS_FILE.write_text(json.dumps(DEFAULT_PRESETS, indent=2), encoding="utf-8")
    return list(DEFAULT_PRESETS)

def save_presets(presets):
    PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRESETS_FILE.write_text(json.dumps(presets, indent=2), encoding="utf-8")

def snapshot_as_preset(name, icon, desc):
    """Capture current full state as a new preset."""
    cowork_state = get_cowork_state()
    skills       = {s["id"]: s["enabled"] for s in get_skills()}
    mcps         = {m["key"]: m["enabled"] for m in get_mcp_permissions()}
    preset = {"id": str(uuid.uuid4())[:8], "name": name, "icon": icon,
              "desc": desc, "cowork": cowork_state, "mcps": mcps, "skills": skills}
    presets = get_presets()
    presets.append(preset)
    save_presets(presets)
    return preset

def load_preset(preset_id):
    """Apply a preset — updates Cowork state, skills, and MCP permissions."""
    presets = get_presets()
    preset  = next((p for p in presets if p["id"] == preset_id), None)
    if not preset:
        return False, "Preset not found"

    # Apply Cowork state
    state = get_cowork_state()
    for k, v in preset.get("cowork", {}).items():
        state[k] = v
    COWORK_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # Apply MCP permissions
    settings = read_settings()
    allow    = settings.setdefault("permissions", {}).setdefault("allow", [])
    # Remove all existing mcp__ entries, then re-add enabled ones
    allow[:] = [e for e in allow if not e.startswith("mcp__")]
    for key, enabled in preset.get("mcps", {}).items():
        if enabled:
            allow.append(key + "__*")
    write_settings(settings)

    # Apply skills
    for skill_id, enable in preset.get("skills", {}).items():
        toggle_skill(skill_id, enable)

    return True, f"Preset '{preset['name']}' loaded"

def delete_preset(preset_id):
    presets = get_presets()
    presets = [p for p in presets if p["id"] != preset_id]
    save_presets(presets)
    return True, "Preset deleted"

# ── Session manager ───────────────────────────────────────────────────────────

def _parse_ts(val):
    """Normalise a timestamp value to millisecond epoch int."""
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        try:
            return int(datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp() * 1000)
        except Exception:
            pass
    return 0

def discover_sessions():
    """Walk SESSIONS_ROOT two levels deep and collect all local_*.json session files."""
    sessions = []
    if not SESSIONS_ROOT.exists():
        return sessions
    try:
        for outer in SESSIONS_ROOT.iterdir():
            if not outer.is_dir():
                continue
            for inner in outer.iterdir():
                if not inner.is_dir():
                    continue
                for jf in inner.glob("local_*.json"):
                    try:
                        data = json.loads(jf.read_text(encoding="utf-8"))
                        created  = _parse_ts(data.get("createdAt", 0))
                        activity = _parse_ts(data.get("lastActivityAt", created))
                        title = data.get("title") or data.get("initialMessage") or "Untitled"
                        sessions.append({
                            "id":             jf.stem,
                            "title":          title[:120],
                            "createdAt":      created,
                            "lastActivityAt": activity,
                            "isArchived":     bool(data.get("isArchived", False)),
                            "_json_path":     str(jf),
                            "_folder_path":   str(inner / jf.stem),
                        })
                    except Exception:
                        continue
    except Exception:
        pass
    sessions.sort(key=lambda s: s["lastActivityAt"], reverse=True)
    return sessions

def delete_sessions(ids):
    """Delete a list of session IDs (json file + folder). Returns count deleted."""
    all_sessions = discover_sessions()
    lookup = {s["id"]: s for s in all_sessions}
    deleted = 0
    for sid in ids:
        s = lookup.get(sid)
        if not s:
            continue
        try:
            jp = Path(s["_json_path"])
            fp = Path(s["_folder_path"])
            if jp.exists():
                jp.unlink()
            if fp.exists():
                shutil.rmtree(fp, ignore_errors=True)
            deleted += 1
        except Exception:
            pass
    return deleted

# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Tool Manager</title>
<style>
  :root {
    --bg:#0f1117; --surface:#1a1d27; --surface2:#21253a; --border:#2a2d3e;
    --accent:#7c6af7; --accent2:#5b9cf6; --green:#4ade80; --red:#f87171;
    --text:#e2e8f0; --muted:#64748b; --warn:#fbbf24; --gold:#f59e0b;
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:16px;min-height:100vh;}

  header{background:var(--surface);border-bottom:1px solid var(--border);padding:18px 28px;display:flex;align-items:center;gap:14px;position:sticky;top:0;z-index:100;}
  .logo{font-size:22px;font-weight:700;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
  .subtitle{color:var(--muted);font-size:14px;}
  .status-dot{width:9px;height:9px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}

  .tabs{display:flex;border-bottom:1px solid var(--border);background:var(--surface);padding:0 28px;}
  .tab{padding:14px 22px;cursor:pointer;color:var(--muted);font-weight:500;font-size:15px;border-bottom:2px solid transparent;transition:all .2s;user-select:none;}
  .tab:hover{color:var(--text);}
  .tab.active{color:var(--accent);border-bottom-color:var(--accent);}

  .content{max-width:1000px;margin:0 auto;padding:28px;}
  .panel{display:none;}
  .panel.active{display:block;}

  .section-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;}
  .section-title{font-size:18px;font-weight:600;}
  .section-sub{color:var(--muted);font-size:14px;margin-top:3px;}
  .badge{font-size:13px;padding:3px 10px;border-radius:999px;font-weight:600;}
  .badge-green{background:rgba(74,222,128,.15);color:var(--green);}
  .badge-muted{background:rgba(100,116,139,.15);color:var(--muted);}

  .card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px;margin-bottom:36px;}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 18px;display:flex;align-items:flex-start;gap:14px;transition:border-color .2s;}
  .card:hover{border-color:var(--accent);}
  .card.enabled {border-left:3px solid var(--green);}
  .card.disabled{border-left:3px solid var(--border);opacity:.75;}
  .card.active-connector{border-left:3px solid var(--green);}
  .card:not(.active-connector):not(.codetab){border-left:3px solid var(--border);opacity:.8;}
  .card-icon{font-size:24px;line-height:1;margin-top:2px;flex-shrink:0;}
  .card-body{flex:1;min-width:0;}
  .card-name{font-weight:600;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .card-desc{color:var(--muted);font-size:13px;margin-top:4px;line-height:1.45;}
  .card-toggle{flex-shrink:0;margin-top:3px;}

  .switch{position:relative;display:inline-block;width:44px;height:24px;}
  .switch input{opacity:0;width:0;height:0;}
  .slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:var(--border);border-radius:24px;transition:.2s;}
  .slider:before{position:absolute;content:"";height:18px;width:18px;left:3px;bottom:3px;background:white;border-radius:50%;transition:.2s;}
  input:checked+.slider{background:var(--accent);}
  input:checked+.slider:before{transform:translateX(20px);}

  /* ── Preset cards ── */
  .preset-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin-bottom:36px;align-items:stretch;}
  .preset-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;display:flex;flex-direction:column;gap:12px;transition:border-color .2s;}
  .preset-card:hover{border-color:var(--accent);}
  .preset-card.builtin{border-top:3px solid var(--accent);}
  .preset-card.custom{border-top:3px solid var(--gold);}
  .preset-header{display:flex;align-items:center;gap:12px;}
  .preset-icon{font-size:28px;line-height:1;width:36px;text-align:center;flex-shrink:0;}
  .preset-name{font-size:17px;font-weight:700;}
  .preset-type{font-size:11px;padding:2px 7px;border-radius:999px;font-weight:600;margin-left:6px;vertical-align:middle;}
  .preset-type.builtin{background:rgba(124,106,247,.15);color:var(--accent);}
  .preset-type.custom{background:rgba(245,158,11,.15);color:var(--gold);}
  .preset-desc{color:var(--muted);font-size:14px;line-height:1.5;flex:1;}
  .preset-chips{display:flex;flex-wrap:wrap;gap:6px;}
  .chip{font-size:12px;padding:3px 9px;border-radius:999px;background:var(--surface2);color:var(--muted);border:1px solid var(--border);}
  .chip.on{background:rgba(74,222,128,.12);color:var(--green);border-color:rgba(74,222,128,.25);}
  .preset-actions{display:flex;gap:8px;margin-top:auto;padding-top:4px;}
  .btn{padding:9px 22px;border-radius:8px;border:none;cursor:pointer;font-weight:600;font-size:15px;transition:all .2s;}
  .btn-primary{background:var(--accent);color:white;}
  .btn-primary:hover{background:#6d5ce6;}
  .btn-secondary{background:var(--border);color:var(--text);}
  .btn-secondary:hover{background:#3a3d4e;}
  .btn-sm{padding:6px 14px;font-size:13px;}
  .btn-load{background:var(--accent);color:white;flex:1;}
  .btn-load:hover{background:#6d5ce6;}
  .btn-delete{background:rgba(248,113,113,.12);color:var(--red);border:1px solid rgba(248,113,113,.25);}
  .btn-delete:hover{background:rgba(248,113,113,.2);}

  /* Snapshot modal */
  .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:200;display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:.2s;}
  .modal-overlay.show{opacity:1;pointer-events:all;}
  .modal{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:28px;width:440px;max-width:90vw;display:flex;flex-direction:column;gap:18px;}
  .modal h2{font-size:18px;font-weight:700;}
  .modal label{font-size:14px;color:var(--muted);display:block;margin-bottom:6px;}
  .modal input,.modal textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 14px;color:var(--text);font-size:15px;outline:none;}
  .modal input:focus,.modal textarea:focus{border-color:var(--accent);}
  .modal textarea{resize:vertical;min-height:70px;font-family:inherit;}
  .icon-row{display:flex;gap:8px;flex-wrap:wrap;}
  .icon-btn{font-size:22px;padding:6px 10px;border-radius:8px;border:2px solid transparent;cursor:pointer;background:var(--surface2);transition:.15s;}
  .icon-btn.selected{border-color:var(--accent);}
  .modal-actions{display:flex;gap:10px;justify-content:flex-end;}

  .save-bar{position:sticky;bottom:0;background:var(--surface);border-top:1px solid var(--border);padding:14px 28px;display:flex;align-items:center;gap:14px;}
  .save-bar.hidden{display:none;}
  .restart-notice{background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);border-radius:8px;padding:10px 16px;color:var(--warn);font-size:14px;}

  .info-box{background:rgba(124,106,247,.08);border:1px solid rgba(124,106,247,.25);border-radius:8px;padding:14px 18px;margin-bottom:22px;font-size:14px;color:var(--muted);line-height:1.65;}
  .info-box strong{color:var(--text);}

  .guide-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 18px;display:flex;align-items:flex-start;gap:14px;margin-bottom:12px;}
  .guide-card .how{font-size:13px;color:var(--accent2);margin-top:6px;font-family:'Courier New',monospace;background:rgba(91,156,246,.1);padding:4px 10px;border-radius:4px;display:inline-block;}
  .guide-card.codetab{opacity:.85;}
  .codetab-tag{font-size:12px;color:var(--accent);background:rgba(124,106,247,.15);padding:2px 8px;border-radius:4px;margin-left:8px;}
  .active-tag{font-size:12px;color:var(--green);background:rgba(74,222,128,.12);padding:2px 8px;border-radius:4px;margin-left:8px;}

  .toast{position:fixed;bottom:84px;right:28px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 20px;font-size:15px;font-weight:500;box-shadow:0 8px 32px rgba(0,0,0,.4);z-index:999;transform:translateY(20px);opacity:0;transition:all .3s;pointer-events:none;}
  .toast.show{transform:translateY(0);opacity:1;}
  .toast.success{border-color:var(--green);color:var(--green);}
  .toast.error{border-color:var(--red);color:var(--red);}

  .empty{color:var(--muted);text-align:center;padding:48px;font-size:15px;}
  hr{border:none;border-top:1px solid var(--border);margin:28px 0;}

  /* ── Sessions tab ── */
  .sessions-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:18px;padding:12px 16px;background:var(--surface);border:1px solid var(--border);border-radius:10px;}
  .sessions-toolbar .spacer{flex:1;}
  .sessions-table-wrap{overflow-x:auto;border-radius:10px;border:1px solid var(--border);}
  table.sessions-tbl{width:100%;border-collapse:collapse;background:var(--surface);}
  table.sessions-tbl th{padding:12px 14px;text-align:left;font-size:13px;font-weight:600;color:var(--muted);border-bottom:1px solid var(--border);white-space:nowrap;}
  table.sessions-tbl td{padding:11px 14px;font-size:14px;border-bottom:1px solid var(--border);vertical-align:middle;}
  table.sessions-tbl tr:last-child td{border-bottom:none;}
  table.sessions-tbl tbody tr:hover{background:rgba(124,106,247,.06);}
  table.sessions-tbl tbody tr.archived{opacity:.6;}
  .session-title{font-weight:500;max-width:360px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .session-id-cell{font-family:'Courier New',monospace;font-size:12px;color:var(--muted);}
  .badge-active{background:rgba(74,222,128,.15);color:var(--green);padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;}
  .badge-archived{background:rgba(100,116,139,.15);color:var(--muted);padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;}
  .btn-danger{background:rgba(248,113,113,.12);color:var(--red);border:1px solid rgba(248,113,113,.25);padding:7px 16px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;transition:all .2s;}
  .btn-danger:hover:not(:disabled){background:rgba(248,113,113,.22);}
  .btn-danger:disabled{opacity:.4;cursor:not-allowed;}
  .del-modal-list{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px 16px;max-height:180px;overflow-y:auto;margin:10px 0;font-size:14px;color:var(--muted);line-height:1.8;}
</style>
</head>
<body>

<header>
  <span style="font-size:28px">🛠️</span>
  <div>
    <div class="logo">Claude Tool Manager</div>
    <div class="subtitle">Skills · MCP permissions · Cowork connectors · Session presets</div>
  </div>
  <div style="flex:1"></div>
  <div class="status-dot"></div>
  <span style="color:var(--muted);font-size:14px;margin-left:6px">Live</span>
</header>

<div class="tabs">
  <div class="tab active"  onclick="switchTab('presets')">⚡ Presets</div>
  <div class="tab"         onclick="switchTab('claude-code')">💻 Claude Code</div>
  <div class="tab"         onclick="switchTab('cowork')">🤝 Cowork</div>
  <div class="tab"         onclick="switchTab('sessions')">💬 Sessions</div>
</div>

<div class="content">

  <!-- ── Presets Panel ── -->
  <div class="panel active" id="panel-presets">

    <div class="info-box">
      <strong>Session presets</strong> let you switch your full tool configuration in one click.
      Each preset sets your <strong>Cowork connector checklist</strong>, <strong>Claude Code skills</strong>, and <strong>MCP permissions</strong> all at once.
      Use <strong>Snapshot current state</strong> to save what you have active right now as a new preset.
    </div>

    <div class="section-header">
      <div>
        <div class="section-title">Your Presets</div>
        <div class="section-sub">Click Load to apply a preset — Claude Code restart required for Code changes</div>
      </div>
      <button class="btn btn-primary btn-sm" onclick="showSnapshotModal()">📸 Snapshot current state</button>
    </div>

    <div class="preset-grid" id="preset-grid">
      <div class="empty">Loading presets…</div>
    </div>

  </div>

  <!-- ── Claude Code Panel ── -->
  <div class="panel" id="panel-claude-code">
    <div class="info-box">
      <strong>How this works:</strong> Changes update <code>C:\Software\.claude\</code> directly.
      Skills are toggled by renaming <code>SKILL.md</code>. MCPs update <code>settings.local.json</code>.
      <strong>A Claude Code restart is required</strong> after saving.
    </div>
    <div class="section-header">
      <div><div class="section-title">Skills</div><div class="section-sub">C:\Software\.claude\skills\</div></div>
      <div id="skills-count" class="badge badge-green">–</div>
    </div>
    <div class="card-grid" id="skills-grid"><div class="empty">Loading…</div></div>
    <hr>
    <div class="section-header">
      <div><div class="section-title">MCP Permissions</div><div class="section-sub">Pre-approved tools in settings.local.json</div></div>
      <div id="mcps-count" class="badge badge-green">–</div>
    </div>
    <div class="card-grid" id="mcps-grid"><div class="empty">Loading…</div></div>
  </div>

  <!-- ── Cowork Panel ── -->
  <div class="panel" id="panel-cowork">
    <div class="info-box">
      <strong>Cowork connectors</strong> are managed through the Cowork app UI.
      Toggle the switches below as a <strong>personal checklist</strong> of what's active in your current session.
      Items marked <span style="color:var(--accent);font-weight:600">Code tab</span> are available via the Code tab in this same app.
    </div>
    <div class="section-header">
      <div><div class="section-title">Connectors</div><div class="section-sub">Track which connectors are active in your current Cowork session</div></div>
      <div id="cowork-count" class="badge badge-green">–</div>
    </div>
    <div id="cowork-list">Loading…</div>
    <hr>
    <div class="section-header">
      <div><div class="section-title">Skills in Cowork</div><div class="section-sub">Bundled skills — load automatically</div></div>
    </div>
    <div class="card-grid" id="cowork-skills-grid"><div class="empty">Loading…</div></div>
  </div>

</div>

<!-- Save bar -->
<div class="save-bar hidden" id="save-bar">
  <div class="restart-notice">⚠️ Unsaved changes — Claude Code must be restarted after saving.</div>
  <div style="flex:1"></div>
  <button class="btn btn-secondary" onclick="discardChanges()">Discard</button>
  <button class="btn btn-primary"   onclick="saveAll()">💾 Save Changes</button>
</div>

<!-- Snapshot modal -->
<div class="modal-overlay" id="modal-overlay" onclick="hideModal(event)">
  <div class="modal" onclick="event.stopPropagation()">
    <h2>📸 Save current state as preset</h2>
    <div>
      <label>Preset name</label>
      <input id="preset-name" type="text" placeholder="e.g. Morning Routine, NetScaler Debug…" maxlength="40">
    </div>
    <div>
      <label>Icon</label>
      <div class="icon-row" id="icon-row">
        <!-- populated by JS -->
      </div>
    </div>
    <div>
      <label>Description (optional)</label>
      <textarea id="preset-desc" placeholder="What is this preset for?"></textarea>
    </div>
    <div class="modal-actions">
      <button class="btn btn-secondary" onclick="hideModal()">Cancel</button>
      <button class="btn btn-primary"   onclick="doSnapshot()">Save Preset</button>
    </div>
  </div>
</div>

  <!-- ── Sessions Panel ── -->
  <div class="panel" id="panel-sessions">
    <div class="info-box">
      <strong>Cowork session history</strong> — browse, filter, and permanently delete past sessions stored on your computer.
      Sessions are stored in <strong>%APPDATA%\Claude\local-agent-mode-sessions</strong>.
      Deletion is <strong>permanent</strong> and cannot be undone.
    </div>

    <div class="sessions-toolbar">
      <button class="btn btn-secondary btn-sm" onclick="selectAllSessions()">Select All</button>
      <button class="btn btn-secondary btn-sm" onclick="deselectAllSessions()">Deselect All</button>
      <label style="display:flex;align-items:center;gap:7px;font-size:14px;color:var(--muted);cursor:pointer;">
        <input type="checkbox" id="show-archived" onchange="renderSessions()" style="width:15px;height:15px;cursor:pointer;">
        Show archived
      </label>
      <div class="spacer"></div>
      <span id="selected-label" style="font-size:14px;color:var(--muted);">0 selected</span>
      <button class="btn-danger" id="delete-sessions-btn" disabled onclick="confirmDeleteSessions()">🗑 Delete Selected</button>
      <button class="btn btn-secondary btn-sm" onclick="loadSessions()">↺ Refresh</button>
    </div>

    <div class="sessions-table-wrap">
      <table class="sessions-tbl">
        <thead>
          <tr>
            <th style="width:36px"><input type="checkbox" id="header-checkbox" onchange="toggleAllSessions(this)" style="width:15px;height:15px;cursor:pointer;"></th>
            <th>Title</th>
            <th>Session ID</th>
            <th>Created</th>
            <th>Last Active</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="sessions-tbody"><tr><td colspan="6" class="empty">Loading sessions…</td></tr></tbody>
      </table>
    </div>

    <!-- Delete confirm modal -->
    <div class="modal-overlay" id="del-sessions-modal" onclick="if(event.target===this)cancelDeleteSessions()">
      <div class="modal">
        <h2>⚠️ Delete Sessions?</h2>
        <p style="color:var(--muted);font-size:14px;">This will permanently delete the selected sessions. This cannot be undone.</p>
        <div class="del-modal-list" id="del-modal-list"></div>
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick="cancelDeleteSessions()">Cancel</button>
          <button class="btn" style="background:var(--red);color:white;" onclick="executeDeleteSessions()">Delete</button>
        </div>
      </div>
    </div>
  </div>

</div><!-- /content -->

<div class="toast" id="toast"></div>

<script>
const ICONS = ['⚡','🔧','🎨','🌐','📊','🖥️','🔍','📝','🚀','💼','🧪','📱','🔒','🗂️','⚙️','🏗️'];
let selectedIcon = '⚡';
let skillsData = [], mcpsData = [];
let pendingSkills = {}, pendingMcps = {};
let dirty = false;

async function api(path, body) {
  const opts = body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {};
  return (await fetch(path, opts)).json();
}

function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'toast show ' + type;
  setTimeout(() => t.className='toast', 3200);
}

function markDirty() {
  dirty = true;
  document.getElementById('save-bar').classList.remove('hidden');
}

function switchTab(tab) {
  const tabs = ['presets','claude-code','cowork','sessions'];
  document.querySelectorAll('.tab').forEach((el,i) => el.classList.toggle('active', tabs[i]===tab));
  document.querySelectorAll('.panel').forEach(el => el.classList.remove('active'));
  document.getElementById('panel-'+tab).classList.add('active');
  if (tab !== 'claude-code') document.getElementById('save-bar').classList.add('hidden');
  if (tab === 'claude-code' && dirty) document.getElementById('save-bar').classList.remove('hidden');
  if (tab === 'sessions') loadSessions();
}

/* ── Presets ── */
async function loadPresets() {
  const data = await api('/api/presets');
  const grid = document.getElementById('preset-grid');
  if (!data.length) { grid.innerHTML='<div class="empty">No presets yet — snapshot your current state to create one.</div>'; return; }
  grid.innerHTML = data.map(p => {
    const isBuiltin = ['netscaler-citrix','website-design','general'].includes(p.id);
    const activeCowork  = Object.values(p.cowork||{}).filter(Boolean).length;
    const activeMcps    = Object.values(p.mcps||{}).filter(Boolean).length;
    const activeSkills  = Object.values(p.skills||{}).filter(Boolean).length;
    return `<div class="preset-card ${isBuiltin?'builtin':'custom'}">
      <div class="preset-header">
        <div class="preset-icon">${p.icon}</div>
        <div>
          <div class="preset-name">${p.name}<span class="preset-type ${isBuiltin?'builtin':'custom'}">${isBuiltin?'Built-in':'Custom'}</span></div>
        </div>
      </div>
      <div class="preset-desc">${p.desc||''}</div>
      <div class="preset-chips">
        <span class="chip on">🤝 ${activeCowork} connectors</span>
        <span class="chip on">🔌 ${activeMcps} MCPs</span>
        ${activeSkills>0?`<span class="chip on">⚙️ ${activeSkills} skill${activeSkills>1?'s':''}</span>`:''}
      </div>
      <div class="preset-actions">
        <button class="btn btn-load btn-sm" onclick="applyPreset('${p.id}','${p.name.replace(/'/g,"\\'")}')">⚡ Load</button>
        ${!isBuiltin?`<button class="btn btn-delete btn-sm" onclick="removePreset('${p.id}')">🗑 Delete</button>`:''}
      </div>
    </div>`;
  }).join('');
}

async function applyPreset(id, name) {
  const r = await api('/api/presets/load', {id});
  if (r.ok) {
    showToast(`✅ "${name}" loaded — restart Claude Code to apply Code changes`);
    loadPresets(); loadCowork(); loadData();
  } else showToast(r.msg, 'error');
}

async function removePreset(id) {
  if (!confirm('Delete this preset?')) return;
  await api('/api/presets/delete', {id});
  showToast('Preset deleted'); loadPresets();
}

function showSnapshotModal() {
  document.getElementById('preset-name').value = '';
  document.getElementById('preset-desc').value = '';
  selectedIcon = '⚡';
  document.getElementById('icon-row').innerHTML = ICONS.map(ic =>
    `<button class="icon-btn ${ic===selectedIcon?'selected':''}" onclick="selectIcon('${ic}')">${ic}</button>`
  ).join('');
  document.getElementById('modal-overlay').classList.add('show');
  setTimeout(() => document.getElementById('preset-name').focus(), 100);
}

function selectIcon(ic) {
  selectedIcon = ic;
  document.querySelectorAll('.icon-btn').forEach(b => b.classList.toggle('selected', b.textContent===ic));
}

function hideModal(e) {
  if (!e || e.target===document.getElementById('modal-overlay'))
    document.getElementById('modal-overlay').classList.remove('show');
}

async function doSnapshot() {
  const name = document.getElementById('preset-name').value.trim();
  if (!name) { document.getElementById('preset-name').focus(); return; }
  const desc = document.getElementById('preset-desc').value.trim();
  const r = await api('/api/presets/snapshot', {name, icon: selectedIcon, desc});
  if (r.ok) {
    hideModal(); showToast(`✅ Preset "${name}" saved!`); loadPresets();
  } else showToast(r.msg, 'error');
}

/* ── Claude Code tab ── */
function renderSkills() {
  const grid = document.getElementById('skills-grid');
  const en = skillsData.filter(s => (s.id in pendingSkills ? pendingSkills[s.id] : s.enabled));
  document.getElementById('skills-count').textContent = en.length+'/'+skillsData.length+' enabled';
  if (!skillsData.length) { grid.innerHTML='<div class="empty">No skills found</div>'; return; }
  grid.innerHTML = skillsData.map(s => {
    const on = s.id in pendingSkills ? pendingSkills[s.id] : s.enabled;
    return `<div class="card ${on?'enabled':'disabled'}">
      <div class="card-icon">⚙️</div>
      <div class="card-body"><div class="card-name">${s.name}</div><div class="card-desc">${s.desc||'No description'}</div></div>
      <div class="card-toggle"><label class="switch"><input type="checkbox" ${on?'checked':''} onchange="toggleSkill('${s.id}',this.checked)"><span class="slider"></span></label></div>
    </div>`;
  }).join('');
}

function renderMcps() {
  const grid = document.getElementById('mcps-grid');
  const en = mcpsData.filter(m => (m.key in pendingMcps ? pendingMcps[m.key] : m.enabled));
  document.getElementById('mcps-count').textContent = en.length+'/'+mcpsData.length+' enabled';
  if (!mcpsData.length) { grid.innerHTML='<div class="empty">No MCPs configured</div>'; return; }
  grid.innerHTML = mcpsData.map(m => {
    const on = m.key in pendingMcps ? pendingMcps[m.key] : m.enabled;
    return `<div class="card ${on?'enabled':'disabled'}">
      <div class="card-icon">${m.icon}</div>
      <div class="card-body"><div class="card-name">${m.name}</div><div class="card-desc">${m.desc}</div></div>
      <div class="card-toggle"><label class="switch"><input type="checkbox" ${on?'checked':''} onchange="toggleMcp('${m.key}',this.checked)"><span class="slider"></span></label></div>
    </div>`;
  }).join('');
}

function toggleSkill(id,val){ pendingSkills[id]=val; markDirty(); renderSkills(); }
function toggleMcp(key,val) { pendingMcps[key]=val;  markDirty(); renderMcps();  }

async function saveAll() {
  let ok=0,fail=0;
  for (const [id,enable] of Object.entries(pendingSkills)) {
    const r = await api('/api/skills/toggle',{id,enable}); r.ok?ok++:fail++;
  }
  for (const [key,enable] of Object.entries(pendingMcps)) {
    const r = await api('/api/mcps/toggle',{key,enable}); r.ok?ok++:fail++;
  }
  pendingSkills={}; pendingMcps={}; dirty=false;
  document.getElementById('save-bar').classList.add('hidden');
  await loadData();
  if (fail) showToast(`Saved ${ok}, ${fail} failed`,'error');
  else showToast('✅ Saved! Restart Claude Code to apply changes.');
}

function discardChanges() {
  pendingSkills={}; pendingMcps={}; dirty=false;
  document.getElementById('save-bar').classList.add('hidden');
  renderSkills(); renderMcps(); showToast('Changes discarded');
}

async function loadData() {
  const [skills,mcps] = await Promise.all([api('/api/skills'),api('/api/mcps')]);
  skillsData=skills; mcpsData=mcps; renderSkills(); renderMcps();
}

/* ── Cowork tab ── */
async function toggleCowork(id,active) {
  await api('/api/cowork/toggle',{id,active}); loadCowork();
}

async function loadCowork() {
  const data = await api('/api/cowork');
  const active = data.connectors.filter(c=>c.active&&c.cowork).length;
  const total  = data.connectors.filter(c=>c.cowork).length;
  document.getElementById('cowork-count').textContent = active+'/'+total+' active';

  document.getElementById('cowork-list').innerHTML = data.connectors.map(c => {
    const isCodeTab = !c.cowork;
    return `<div class="guide-card ${isCodeTab?'codetab':''} ${c.active&&!isCodeTab?'active-connector':''}">
      <div class="card-icon">${c.icon}</div>
      <div class="card-body">
        <div class="card-name">${c.name}
          ${isCodeTab?'<span class="codetab-tag">Code tab</span>':''}
          ${c.active&&!isCodeTab?'<span class="active-tag">● Active</span>':''}
        </div>
        <div class="card-desc">${c.desc}</div>
        <div class="how">${c.how}</div>
      </div>
      ${!isCodeTab?`<div class="card-toggle" style="margin-top:3px"><label class="switch"><input type="checkbox" ${c.active?'checked':''} onchange="toggleCowork('${c.id}',this.checked)"><span class="slider"></span></label></div>`
        :'<div style="font-size:13px;color:var(--accent);margin-top:3px;white-space:nowrap">Code tab</div>'}
    </div>`;
  }).join('');

  // Live skills — read directly from the skills directory (same data as Claude Code tab)
  const skillsGrid = document.getElementById('cowork-skills-grid');
  const liveSkills = await api('/api/skills');
  if (!liveSkills.length) {
    skillsGrid.innerHTML = '<div class="empty">No skills found in skills directory</div>';
  } else {
    skillsGrid.innerHTML = liveSkills.map(s => {
      const badge = s.enabled
        ? `<div style="font-size:13px;color:var(--green);white-space:nowrap">&#9679; Enabled</div>`
        : `<div style="font-size:13px;color:var(--muted);white-space:nowrap">Disabled</div>`;
      return `<div class="card ${s.enabled?'enabled':'disabled'}">
        <div class="card-icon">&#9881;&#65039;</div>
        <div class="card-body"><div class="card-name">${s.name}</div><div class="card-desc">${s.desc||'No description'}</div></div>
        ${badge}</div>`;
    }).join('');
  }
}

/* ── Sessions tab ── */
let sessionsData = [];
let selectedSessionIds = new Set();
let sessionsToDelete = [];

async function loadSessions() {
  document.getElementById('sessions-tbody').innerHTML =
    '<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--muted)">Loading sessions\u2026</td></tr>';
  sessionsData = await api('/api/sessions');
  selectedSessionIds.clear();
  renderSessions();
  updateSessionDeleteBtn();
}

function fmtDate(ms) {
  if (!ms) return '\u2014';
  const d = new Date(ms);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
}

function renderSessions() {
  const showArchived = document.getElementById('show-archived').checked;
  const filtered = showArchived ? sessionsData : sessionsData.filter(s => !s.isArchived);
  const tbody = document.getElementById('sessions-tbody');
  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:48px;color:var(--muted)">' +
      (sessionsData.length ? 'No active sessions. Enable "Show archived" to see all.' : 'No sessions found.') + '</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map(s => {
    const checked = selectedSessionIds.has(s.id) ? 'checked' : '';
    const arc = s.isArchived ? 'archived' : '';
    const badge = s.isArchived
      ? '<span class="badge-archived">Archived</span>'
      : '<span class="badge-active">Active</span>';
    const shortId = s.id.replace('local_','').substring(0,12) + '\u2026';
    return `<tr class="${arc}">
      <td class="checkbox-cell"><input type="checkbox" data-id="${s.id}" ${checked} onchange="toggleSessionRow(this)" style="width:15px;height:15px;cursor:pointer;"></td>
      <td><div class="session-title" title="${escSess(s.title)}">${escSess(s.title)}</div></td>
      <td class="session-id-cell" title="${s.id}">${shortId}</td>
      <td style="white-space:nowrap;font-size:13px;color:var(--muted)">${fmtDate(s.createdAt)}</td>
      <td style="white-space:nowrap;font-size:13px;color:var(--muted)">${fmtDate(s.lastActivityAt)}</td>
      <td>${badge}</td>
    </tr>`;
  }).join('');
  updateHeaderCheckbox();
}

function escSess(t) {
  const d = document.createElement('div'); d.textContent = t; return d.innerHTML;
}

function toggleSessionRow(cb) {
  if (cb.checked) selectedSessionIds.add(cb.dataset.id);
  else selectedSessionIds.delete(cb.dataset.id);
  updateSessionDeleteBtn(); updateHeaderCheckbox();
}

function toggleAllSessions(cb) {
  document.querySelectorAll('#sessions-tbody [data-id]').forEach(c => {
    c.checked = cb.checked;
    if (cb.checked) selectedSessionIds.add(c.dataset.id);
    else selectedSessionIds.delete(c.dataset.id);
  });
  updateSessionDeleteBtn();
}

function selectAllSessions() {
  document.querySelectorAll('#sessions-tbody [data-id]').forEach(c => {
    c.checked = true; selectedSessionIds.add(c.dataset.id);
  });
  updateSessionDeleteBtn(); updateHeaderCheckbox();
}

function deselectAllSessions() {
  document.querySelectorAll('#sessions-tbody [data-id]').forEach(c => {
    c.checked = false; selectedSessionIds.delete(c.dataset.id);
  });
  updateSessionDeleteBtn(); updateHeaderCheckbox();
}

function updateHeaderCheckbox() {
  const all = document.querySelectorAll('#sessions-tbody [data-id]');
  const checked = Array.from(all).filter(c => c.checked).length;
  const hdr = document.getElementById('header-checkbox');
  if (!hdr) return;
  hdr.checked = checked > 0 && checked === all.length;
  hdr.indeterminate = checked > 0 && checked < all.length;
}

function updateSessionDeleteBtn() {
  const n = selectedSessionIds.size;
  document.getElementById('selected-label').textContent = n + ' selected';
  document.getElementById('delete-sessions-btn').disabled = n === 0;
}

function confirmDeleteSessions() {
  if (!selectedSessionIds.size) return;
  sessionsToDelete = Array.from(selectedSessionIds);
  const list = document.getElementById('del-modal-list');
  const shown = sessionsToDelete.slice(0, 8);
  const rest = sessionsToDelete.length - shown.length;
  list.innerHTML = shown.map(id => {
    const s = sessionsData.find(x => x.id === id);
    return '<div style="padding:2px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' +
      escSess(s ? s.title : id) + '</div>';
  }).join('') + (rest > 0 ? `<div style="color:var(--muted);margin-top:4px">\u2026and ${rest} more</div>` : '');
  document.getElementById('del-sessions-modal').classList.add('show');
}

function cancelDeleteSessions() {
  document.getElementById('del-sessions-modal').classList.remove('show');
}

async function executeDeleteSessions() {
  const ids = sessionsToDelete;
  cancelDeleteSessions();
  const r = await api('/api/sessions/delete', {ids});
  showToast(r.ok ? `\u2705 Deleted ${r.deleted} session${r.deleted!==1?'s':''}` : 'Delete failed', r.ok?'success':'error');
  loadSessions();
}

// Init
loadPresets(); loadData(); loadCowork();
</script>
</body>
</html>
"""

# ── HTTP Handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers(); self.wfile.write(body)

    def send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self.send_html(HTML)
        elif path == "/api/skills":
            self.send_json(get_skills())
        elif path == "/api/mcps":
            self.send_json(get_mcp_permissions())
        elif path == "/api/cowork":
            state = get_cowork_state()
            connectors = [{**c, "active": state.get(c["id"], COWORK_STATE_DEFAULTS.get(c["id"], False))}
                          for c in COWORK_CONNECTORS]
            # Auto-surface any extra connectors saved in cowork-state.json but not in the hardcoded list
            known_ids = {c["id"] for c in COWORK_CONNECTORS}
            for cid, active in state.items():
                if cid not in known_ids:
                    display = cid.replace("-", " ").replace("_", " ").title()
                    connectors.append({"id": cid, "name": display, "icon": "🔌",
                                       "desc": "Connector (auto-discovered from saved state)",
                                       "how": "Settings -> Connectors in the Cowork app",
                                       "cowork": True, "active": active})
            self.send_json({"connectors": connectors})
        elif path == "/api/presets":
            self.send_json(get_presets())
        elif path == "/api/sessions":
            sessions = discover_sessions()
            public = [{"id": s["id"], "title": s["title"], "createdAt": s["createdAt"],
                       "lastActivityAt": s["lastActivityAt"], "isArchived": s["isArchived"]}
                      for s in sessions]
            self.send_json(public)
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length)) if length else {}
        path   = urlparse(self.path).path

        if   path == "/api/skills/toggle":
            ok, msg = toggle_skill(body.get("id",""), body.get("enable", True))
            self.send_json({"ok": ok, "msg": msg})
        elif path == "/api/mcps/toggle":
            ok, msg = toggle_mcp(body.get("key",""), body.get("enable", True))
            self.send_json({"ok": ok, "msg": msg})
        elif path == "/api/cowork/toggle":
            ok, msg = set_cowork_active(body.get("id",""), body.get("active", True))
            self.send_json({"ok": ok, "msg": msg})
        elif path == "/api/presets/snapshot":
            p = snapshot_as_preset(body.get("name","Untitled"), body.get("icon","⚡"), body.get("desc",""))
            self.send_json({"ok": True, "preset": p})
        elif path == "/api/presets/load":
            ok, msg = load_preset(body.get("id",""))
            self.send_json({"ok": ok, "msg": msg})
        elif path == "/api/presets/delete":
            ok, msg = delete_preset(body.get("id",""))
            self.send_json({"ok": ok, "msg": msg})
        elif path == "/api/sessions/delete":
            ids = body.get("ids", [])
            count = delete_sessions(ids)
            self.send_json({"ok": True, "deleted": count})
        else:
            self.send_response(404); self.end_headers()

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    print(f"\n  🛠️  Claude Tool Manager")
    print(f"  ─────────────────────────────────────────")
    print(f"  Server  : {url}")
    print(f"  Skills  : {SKILLS_DIR}")
    print(f"  Settings: {SETTINGS_FILE}")
    print(f"  Presets : {PRESETS_FILE}")
    print(f"\n  Opening browser... (Ctrl+C to stop)\n")
    try:
        webbrowser.open(url)
        with HTTPServer(("localhost", PORT), Handler) as srv:
            srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped."); sys.exit(0)
    except OSError as e:
        print(f"\n  ERROR: Could not start on port {PORT}: {e}"); sys.exit(1)
