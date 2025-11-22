@echo off
REM BDO Vulkan Utility Launcher
REM Checks for Python, installs if needed, and runs the script

echo Black Desert Vulkan Utility Launcher
echo =====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python is installed
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
if %errorlevel% neq 0 (
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
python -c "import tkinter" >nul 2>&1
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
python bdo_vulkan_manager.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Script encountered an error
    pause
)

exit /b %errorlevel%
