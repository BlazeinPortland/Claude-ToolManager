# Claude Tool Manager

A local web dashboard for managing all [Claude Desktop](https://claude.ai/download) settings — MCP servers, skills, plugins, connectors, sessions, and presets — in one place.
<img width="1905" height="818" alt="image" src="https://github.com/user-attachments/assets/9f7fc7bd-70c4-485c-83d9-232cd44114d7" />

<img width="1652" height="672" alt="image" src="https://github.com/user-attachments/assets/0e6c0258-d70f-46da-9983-d9503b333d46" />



![Dashboard](https://img.shields.io/badge/Python-3.8%2B-blue) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## Features

- **Dashboard** — Usage analytics, daily activity charts, token breakdown by model, server health status
- **Settings** — View/edit global and project-level permissions, MCP servers, voice & statusline preferences
- **Skills** — Enable/disable all 30+ global skills and project skills with one toggle
- **Plugins** — Manage installed plugins, view blocklist, and marketplace sources
- **Connectors** — OAuth connector status and cowork toggle switches
- **Sessions** — Browse and bulk-delete Claude Code sessions
- **Presets** — Snapshot and restore full configuration states across all domains

## Requirements

- **Python 3.8+** (no external packages — pure stdlib)
- **Claude Desktop** installed

## Quick Start

### macOS / Linux

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/Claude-ToolManager.git
cd Claude-ToolManager

# Make launcher executable
chmod +x start-tool-manager.sh

# Run
./start-tool-manager.sh
```

Then open **http://localhost:9191** in your browser.

### Windows

```powershell
# Clone the repo
git clone https://github.com/YOUR_USERNAME/Claude-ToolManager.git
cd Claude-ToolManager

# Run
.\Start-ToolManager.ps1
```

Or just double-click `Start-ToolManager.ps1` in Explorer.

## Configuration Files

The tool reads from standard Claude Desktop config locations — no setup needed:

| Platform | Location |
|---|---|
| macOS | `~/Library/Application Support/Claude/` |
| Windows | `%APPDATA%\Claude\` |
| Linux | `~/.config/Claude/` |

Global Claude settings are always at `~/.claude/`.

## Options

```bash
python tool-manager.py [--project /path/to/project]
```

`--project` overrides the auto-detected project directory for project-scoped settings.

## Port

Default port is **9191**. Change the `PORT` constant at the top of `tool-manager.py` if needed.
