@echo off
setlocal EnableExtensions EnableDelayedExpansion

if /I not "%~1"=="--run" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','\"%~f0\" --run' -WindowStyle Hidden"
    exit /b 0
)

set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

if not exist ".env" if exist ".env.example" copy /Y ".env.example" ".env" >nul
if not exist "logs" mkdir "logs"
if not exist "logs\pids" mkdir "logs\pids"
if not exist "chroma_db" mkdir "chroma_db"
if not exist "vault_docs" mkdir "vault_docs"
if not exist "vault_archive" mkdir "vault_archive"

call :resolve_python
if not defined PYTHON_EXE (
    echo [!] No suitable Python environment found. Set SENTINEL_PYTHON to a venv with Sentinel deps.
    exit /b 1
)

call :start_service "Monitor" "backend\sentinel_monitor.py" "logs\monitor_output.log"
call :start_service "API Backend" "backend\app.py" "logs\backend_output.log"
call :start_service "Tray Icon" "backend\tray_manager.py" "logs\tray_output.log"

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if not exist "%STARTUP_FOLDER%\SentinelShield.bat" (
    echo [*] Installing Windows auto-start on boot...
    (
        echo @echo off
        echo call "%%~f0"
    ) > "%STARTUP_FOLDER%\SentinelShield.bat"
)

echo --------------------------------------------------------
echo SENTINEL SHIELD ACTIVE
echo Run start.bat once - runs forever in background
echo --------------------------------------------------------
exit /b 0

:resolve_python
set "PYTHON_EXE="
if defined SENTINEL_PYTHON (
    if exist "%SENTINEL_PYTHON%" (
        call :validate_python "%SENTINEL_PYTHON%"
        if !errorlevel! equ 0 set "PYTHON_EXE=%SENTINEL_PYTHON%"
    )
)

if not defined PYTHON_EXE (
    if exist "%USERPROFILE%\vault_env\Scripts\python.exe" (
        call :validate_python "%USERPROFILE%\vault_env\Scripts\python.exe"
        if !errorlevel! equ 0 set "PYTHON_EXE=%USERPROFILE%\vault_env\Scripts\python.exe"
    )
)

if not defined PYTHON_EXE (
    if exist "%BASE_DIR%backend\venv\Scripts\python.exe" (
        call :validate_python "%BASE_DIR%backend\venv\Scripts\python.exe"
        if !errorlevel! equ 0 set "PYTHON_EXE=%BASE_DIR%backend\venv\Scripts\python.exe"
    )
)

if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        call :validate_python "%%P"
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=%%P"
            goto :resolve_done
        )
    )
)

:resolve_done
exit /b 0

:validate_python
set "CANDIDATE=%~1"
"%CANDIDATE%" -c "import importlib; [importlib.import_module(m) for m in ('fastapi','watchdog','langchain_ollama','langchain_chroma','plyer')]" >nul 2>&1
exit /b %errorlevel%

:start_service
set "SERVICE_NAME=%~1"
set "SCRIPT_REL=%~2"
set "LOG_REL=%~3"

for %%F in ("%BASE_DIR%%SCRIPT_REL%") do set "SCRIPT_ABS=%%~fF"
for %%F in ("%BASE_DIR%%LOG_REL%") do set "LOG_ABS=%%~fF"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$pattern=[regex]::Escape('%SCRIPT_ABS%'); $running=(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match $pattern }); if($running){exit 0}else{exit 1}" >nul 2>&1
if !errorlevel! equ 0 (
    echo [=] %SERVICE_NAME% already running
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList '%SCRIPT_ABS%' -WindowStyle Hidden -RedirectStandardOutput '%LOG_ABS%' -RedirectStandardError '%LOG_ABS%'"
echo [+] %SERVICE_NAME% started
exit /b 0
