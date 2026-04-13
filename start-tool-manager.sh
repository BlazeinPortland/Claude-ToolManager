#!/usr/bin/env bash
# Claude Tool Manager — Launcher (macOS / Linux)
# Usage: ./start-tool-manager.sh [--project /path/to/project]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_FILE="$SCRIPT_DIR/tool-manager.py"

# Find Python 3
PYTHON=""
for candidate in python3 python py; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c "import sys; print(sys.version_info.major)" 2>/dev/null)
        if [ "$version" = "3" ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo ""
    echo "  ERROR: Python 3 not found."
    echo "  Install it with: brew install python3  (macOS)"
    echo "  or visit: https://python.org"
    echo ""
    exit 1
fi

if [ ! -f "$APP_FILE" ]; then
    echo ""
    echo "  ERROR: tool-manager.py not found at $APP_FILE"
    echo ""
    exit 1
fi

# Kill any stale instance on port 9191
STALE=$(lsof -ti tcp:9191 2>/dev/null)
if [ -n "$STALE" ]; then
    echo "  Stopping old instance (PID $STALE)..."
    kill -9 $STALE 2>/dev/null
    sleep 0.5
fi

echo ""
echo "  Starting Claude Tool Manager..."
echo "  Using Python: $(which $PYTHON) ($($PYTHON --version))"
echo "  Open http://localhost:9191 in your browser if it doesn't open automatically."
echo "  Press Ctrl+C to stop the server."
echo ""

cd "$SCRIPT_DIR"
exec "$PYTHON" "$APP_FILE" "$@"
