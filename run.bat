@echo off
REM BDO Vulkan Utility Launcher
REM Checks for Python, installs if needed, and runs the script

setlocal EnableExtensions

echo Black Desert Vulkan Utility Launcher
echo =====================================
echo.

REM Check if Python is installed
set "PY_CMD="
call :detect_python
if %errorlevel% equ 0 (
    echo [OK] Python is installed ^(using: %PY_CMD%^)
    goto :check_deps
)

echo [WARNING] Python is not installed!
echo.
echo This utility requires Python to run.
echo.
echo Option 1: Install Python automatically (requires winget)
echo Option 2: Manual installation instructions
echo.
choice /C 12 /N /M "Choose option (1 or 2): "

if %errorlevel% equ 1 goto :auto_install
if %errorlevel% equ 2 goto :manual_install

:auto_install
echo.
echo Attempting to install Python using winget...
winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
set "WINGET_EXIT=%errorlevel%"

REM Re-check after winget attempt in case Python was already present but not detected earlier.
call :detect_python
if %errorlevel% equ 0 (
    echo.
    echo [OK] Python is available ^(using: %PY_CMD%^)
    goto :check_deps
)

if not "%WINGET_EXIT%"=="0" (
    echo.
    echo [ERROR] Automatic installation failed.
    goto :manual_install
)
echo.
echo [OK] Python installed successfully!
echo Please close this window and run the script again.
pause
exit /b 0

:manual_install
echo.
echo Please install Python manually:
echo 1. Visit: https://www.python.org/downloads/
echo 2. Download Python 3.12 or newer
echo 3. Run the installer and CHECK "Add Python to PATH"
echo 4. After installation, run this script again
echo.
pause
exit /b 1

:check_deps
REM Check if required packages are installed
%PY_CMD% -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] tkinter not found. Installing...
    echo Note: tkinter usually comes with Python. You may need to reinstall Python with Tcl/Tk support.
)

echo [OK] All dependencies satisfied
echo.

REM Check if assets exist (required when BUNDLED=False in the script)
if not exist "assets\Normal\dxvk.conf" (
    if not exist "BDO_Vulkan_API\Normal\dxvk.conf" (
        echo [WARNING] Asset files not found!
        echo.
        echo The script requires either:
        echo   - assets\Normal and assets\Potato folders, OR
        echo   - BDO_Vulkan_API\Normal and BDO_Vulkan_API\Potato folders
        echo.
        echo Please ensure the asset files are in the correct location.
        echo You will be prompted to select the source folder manually when you run the script.
        echo.
    )
)

echo Starting BDO Vulkan Utility...
echo.

REM Run the script
%PY_CMD% bdo_vulkan_manager.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Script encountered an error
    pause
)

exit /b %errorlevel%

:detect_python
set "PY_CMD="

where python >nul 2>&1
if %errorlevel% equ 0 (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=python"
        exit /b 0
    )
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3 --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=py -3"
        exit /b 0
    )

    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
        exit /b 0
    )
)

for /f "delims=" %%P in ('dir /b /ad "%LocalAppData%\Programs\Python\Python3*" 2^>nul') do (
    if exist "%LocalAppData%\Programs\Python\%%P\python.exe" (
        set "PY_CMD="%LocalAppData%\Programs\Python\%%P\python.exe""
        exit /b 0
    )
)

exit /b 1
