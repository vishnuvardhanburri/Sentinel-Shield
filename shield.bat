@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "API_URL=http://localhost:8000"
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

call :resolve_python
if not defined PYTHON_EXE set "PYTHON_EXE=python"

if /I "%~1"=="start" (
    echo --- SENTINEL SHIELD CONTROL (VISHNULABS) ---
    echo [*] Activating Sentinel Shield in background...
    call start.bat
    exit /b 0
)

if /I "%~1"=="stop" (
    echo --- SENTINEL SHIELD CONTROL (VISHNULABS) ---
    echo [*] Deactivating Sentinel Shield...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$patterns=@('backend\\sentinel_monitor.py','backend\\app.py','backend\\tray_manager.py'); Get-CimInstance Win32_Process | Where-Object { $cmd=$_.CommandLine; if(-not $cmd){return $false}; foreach($p in $patterns){ if($cmd -like ('*'+$p+'*')){ return $true } }; return $false } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
    echo [-] System Offline.
    exit /b 0
)

if /I "%~1"=="status" (
    echo --- SENTINEL SHIELD STATUS (VISHNULABS) ---
    echo [*] Fetching Integrity Status...
    "%PYTHON_EXE%" -c "import json, urllib.request, sys; data=json.loads(urllib.request.urlopen('%API_URL%/status', timeout=8).read().decode()); stats=data.get('stats', {}); print('STATUS:   OPERATIONAL'); print(f'VAULT:    {len(data.get(\"processed_files\", {}))} docs'); print(f'LEAKS:    {stats.get(\"leaks_blocked\", 0)} blocked'); print(f'SAVED:    {stats.get(\"hours_saved\", 0)} hours'); print(f'VALUE:    ${stats.get(\"money_saved\", 0)} (Billable Equiv)'); print(f'AUDIT:    {stats.get(\"redaction_stats\", {})}'); print(f'REFRESH:  {stats.get(\"last_sync\", \"N/A\")}')" 2>nul
    if errorlevel 1 echo STATUS:   OFFLINE
    echo ------------------------------
    exit /b 0
)

if /I "%~1"=="ask" (
    set "QUERY=%~2"
    if "!QUERY!"=="" (
        echo Usage: shield.bat ask "your query"
        exit /b 1
    )
    echo --- SENTINEL SHIELD QUERY (VISHNULABS) ---
    "%PYTHON_EXE%" -c "import json, urllib.request, sys; q=sys.argv[1]; req=urllib.request.Request('%API_URL%/ask', data=json.dumps({'prompt': q}).encode(), headers={'Content-Type':'application/json'}); d=json.loads(urllib.request.urlopen(req, timeout=30).read().decode()); print('\nSENTINEL RESPONSE:\n' + d.get('answer', 'Error')); print('\nSources: ' + ', '.join(d.get('sources', []))); print('\nfindings_alert=' + d.get('findings_alert','CLEAN'))" "!QUERY!"
    echo -----------------------------
    exit /b 0
)

if /I "%~1"=="audit-export" (
    echo --- SENTINEL SHIELD AUDIT (VISHNULABS) ---
    echo [*] Generating Compliance Audit Log...
    "%PYTHON_EXE%" -c "import json, urllib.request; req=urllib.request.Request('%API_URL%/export-audit', method='POST'); d=json.loads(urllib.request.urlopen(req, timeout=15).read().decode()); print('[+] Audit Export Successful!\nLocation: ' + d.get('file','Error')) if d.get('status') == 'success' else print('[!] Export Failed.')"
    exit /b 0
)

echo --- SENTINEL SHIELD (VISHNULABS) ---
echo Professional Commands:
echo   start           - Activate background guardian
echo   stop            - Deactivate all services
echo   status          - View ROI stats
echo   ask "query"     - Search vault
echo   audit-export    - Generate CSV audit log
echo --------------------------
exit /b 0

:resolve_python
set "PYTHON_EXE="
if defined SENTINEL_PYTHON (
    if exist "%SENTINEL_PYTHON%" set "PYTHON_EXE=%SENTINEL_PYTHON%"
)
if not defined PYTHON_EXE (
    if exist "%USERPROFILE%\vault_env\Scripts\python.exe" set "PYTHON_EXE=%USERPROFILE%\vault_env\Scripts\python.exe"
)
if not defined PYTHON_EXE (
    if exist "%BASE_DIR%backend\venv\Scripts\python.exe" set "PYTHON_EXE=%BASE_DIR%backend\venv\Scripts\python.exe"
)
if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        set "PYTHON_EXE=%%P"
        goto :resolve_done
    )
)
:resolve_done
exit /b 0
