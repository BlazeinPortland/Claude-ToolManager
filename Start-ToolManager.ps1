# Claude Tool Manager — Launcher
# Starts the local web server and opens the browser

$ScriptDir = "C:\Software\Claude-ToolManager"
$AppFile   = "$ScriptDir\tool-manager.py"

# Locate Python — check PATH first, then common install locations
$PythonExe = $null
foreach ($candidate in @("python", "python3", "py",
    "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "C:\Python312\python.exe", "C:\Python311\python.exe")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $PythonExe = $candidate; break
    }
    if ($candidate -like "*.exe" -and (Test-Path $candidate)) {
        $PythonExe = $candidate; break
    }
}

if (-not $PythonExe) {
    Write-Host ""
    Write-Host "  ERROR: Python not found." -ForegroundColor Red
    Write-Host "  Install Python from https://python.org and try again." -ForegroundColor Yellow
    Write-Host ""
    pause; exit 1
}

if (-not (Test-Path $AppFile)) {
    Write-Host ""
    Write-Host "  ERROR: tool-manager.py not found at $AppFile" -ForegroundColor Red
    Write-Host ""
    pause; exit 1
}

Write-Host ""
Write-Host "  Starting Claude Tool Manager..." -ForegroundColor Cyan
Write-Host "  Using Python: $PythonExe" -ForegroundColor DarkGray
Write-Host "  Open http://localhost:9191 in your browser if it doesn't open automatically."
Write-Host "  Press Ctrl+C to stop the server."
Write-Host ""

Set-Location $ScriptDir
& $PythonExe $AppFile

