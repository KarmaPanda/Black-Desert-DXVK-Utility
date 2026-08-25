@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT_DIR=%%~fI\"
set "PYTHON_EXE=%ROOT_DIR%venv-py312\Scripts\python.exe"
set "DIST_DIR=%ROOT_DIR%dist"
set "NUITKA_BUILD_DIR=%ROOT_DIR%nuitka-build"
set "ICON_PATH=%ROOT_DIR%BlackDesert.ico"

if /I "%1"=="" goto :menu
if /I "%1"=="help" goto :show_usage
if /I "%1"=="bundled" goto :build_bundled_pyinstaller
if /I "%1"=="bundled-pyinstaller" goto :build_bundled_pyinstaller
if /I "%1"=="bundled-nuitka" goto :build_bundled_nuitka
if /I "%1"=="nonbundled" goto :build_nonbundled_pyinstaller
if /I "%1"=="nonbundled-pyinstaller" goto :build_nonbundled_pyinstaller
if /I "%1"=="nonbundled-nuitka" goto :build_nonbundled_nuitka
if /I "%1"=="pyinstaller" goto :build_bundled_pyinstaller
if /I "%1"=="nuitka" goto :build_bundled_nuitka

:show_usage
echo Black Desert Vulkan Utility Build Helper
echo.
echo Usage:
echo   build.bat [option]
echo.
echo Options:
echo   bundled               ^| Build bundled PyInstaller onefile
echo   bundled-pyinstaller   ^| Build bundled PyInstaller onefile
echo   bundled-nuitka        ^| Build bundled Nuitka onefile
echo   nonbundled            ^| Build non-bundled PyInstaller onefile
echo   nonbundled-pyinstaller ^| Build non-bundled PyInstaller onefile
echo   nonbundled-nuitka     ^| Build non-bundled Nuitka onefile
echo   help                  ^| Show this menu
echo.
exit /b 0

:menu
cls
echo.
echo Select build type:
echo  1) Bundled PyInstaller
echo  2) Bundled Nuitka
echo  3) Non-bundled PyInstaller
echo  4) Non-bundled Nuitka
echo  5) Exit
set /p choice="Choice [1-5]: "

if /I "%choice%"=="1" goto :build_bundled_pyinstaller
if /I "%choice%"=="2" goto :build_bundled_nuitka
if /I "%choice%"=="3" goto :build_nonbundled_pyinstaller
if /I "%choice%"=="4" goto :build_nonbundled_nuitka
if /I "%choice%"=="5" exit /b 0

echo Invalid choice.
pause
exit /b 1

:ensure_python_312
if not exist "%PYTHON_EXE%" (
  echo Missing Python 3.12 venv: "%PYTHON_EXE%"
  echo Creating it now...
  py -3.12 -m venv "%ROOT_DIR%venv-py312"
  if errorlevel 1 (
    echo Failed to create Python 3.12 venv.
    pause
    exit /b 1
  )
)

"%PYTHON_EXE%" -V >nul 2>&1
if errorlevel 1 (
  echo Failed to invoke Python 3.12 from: "%PYTHON_EXE%"
  pause
  exit /b 1
)
exit /b 0

:ensure_build_modules
call :ensure_python_312
if errorlevel 1 exit /b 1

for %%M in (nuitka pyinstaller PyQt6) do (
  set "MOD_NAME=%%~M"
  if /I "%%~M"=="pyinstaller" set "MOD_NAME=PyInstaller"
  if /I "%%~M"=="pyqt6" set "MOD_NAME=PyQt6"

  "%PYTHON_EXE%" -c "import importlib.util, sys; mod = r'!MOD_NAME!'; sys.exit(0 if importlib.util.find_spec(mod) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo Installing missing build dependency: %%M
    "%PYTHON_EXE%" -m pip install %%M
    if errorlevel 1 (
      echo Failed to install %%M
      pause
      exit /b 1
    )
  )
)
exit /b 0

:build_bundled_pyinstaller
call :ensure_build_modules
if errorlevel 1 exit /b 1

if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%ROOT_DIR%build" rmdir /s /q "%ROOT_DIR%build"
mkdir "%DIST_DIR%"
mkdir "%ROOT_DIR%build"
if exist "%NUITKA_BUILD_DIR%" rmdir /s /q "%NUITKA_BUILD_DIR%"

cd /d "%ROOT_DIR%"
"%PYTHON_EXE%" -m PyInstaller --onefile --windowed ^
  --distpath "%DIST_DIR%" ^
  --workpath "%ROOT_DIR%build" ^
  --specpath "%ROOT_DIR%build" ^
  --add-data "%ROOT_DIR%assets;assets" ^
  --add-data "%ROOT_DIR%BlackDesert.ico;." ^
  --name "BDOVulkanUtility" ^
  bdo_vulkan_manager.py

if errorlevel 1 (
  echo PyInstaller bundled build failed.
  pause
  exit /b 1
)

call :cleanup_build_artifacts

echo.
echo Bundled PyInstaller build complete.
echo Output is in: %DIST_DIR%
pause
exit /b 0

:build_bundled_nuitka
call :ensure_build_modules
if errorlevel 1 exit /b 1

if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"
if exist "%NUITKA_BUILD_DIR%" rmdir /s /q "%NUITKA_BUILD_DIR%"

cd /d "%ROOT_DIR%"
"%PYTHON_EXE%" -m nuitka ^
  --onefile ^
  --windows-console-mode=disable ^
  --enable-plugin=pyqt6 ^
  --noinclude-pytest-mode=nofollow ^
  --noinclude-setuptools-mode=nofollow ^
  --noinclude-unittest-mode=nofollow ^
  --mingw64 ^
  --windows-icon-from-ico=BlackDesert.ico ^
  --include-data-files=assets/d3d11.dll=assets/d3d11.dll ^
  --include-data-files=assets/dxgi.dll=assets/dxgi.dll ^
  --include-data-files=assets/dxvk.conf=assets/dxvk.conf ^
  --include-data-files=BlackDesert.ico=BlackDesert.ico ^
  --include-data-files=app.manifest=app.manifest ^
  --output-filename=BDOVulkanUtility.exe ^
  --company-name=KarmaPanda ^
  --product-name="Black Desert Vulkan Utility" ^
  --file-version=1.0.1.0 ^
  --product-version=1.0.1.0 ^
  --file-description="Black Desert Online Vulkan/DXVK Manager" ^
  --copyright="Copyright (c) 2025 KarmaPanda" ^
  --trademarks="Black Desert Online is a trademark of Pearl Abyss" ^
  --disable-ccache ^
  --lto=no ^
  --remove-output ^
  --assume-yes-for-downloads ^
  --output-dir="%NUITKA_BUILD_DIR%" ^
  bdo_vulkan_manager.py

if errorlevel 1 (
  echo Nuitka bundled build failed.
  pause
  exit /b 1
)

if exist "%NUITKA_BUILD_DIR%\BDOVulkanUtility.exe" (
  copy /Y "%NUITKA_BUILD_DIR%\BDOVulkanUtility.exe" "%DIST_DIR%\BDOVulkanUtility.exe" >nul
)

call :cleanup_build_artifacts

echo.
echo Bundled Nuitka build complete.
echo Output is in: %DIST_DIR%
pause
exit /b 0

:cleanup_build_artifacts
if exist "%ROOT_DIR%build" rmdir /s /q "%ROOT_DIR%build"
if exist "%ROOT_DIR%__pycache__" rmdir /s /q "%ROOT_DIR%__pycache__"
if exist "%ROOT_DIR%BDOVulkanUtility.spec" del /f /q "%ROOT_DIR%BDOVulkanUtility.spec"
if exist "%ROOT_DIR%BDOVulkanUtility.exe" del /f /q "%ROOT_DIR%BDOVulkanUtility.exe"
if exist "%NUITKA_BUILD_DIR%" rmdir /s /q "%NUITKA_BUILD_DIR%"
exit /b 0

:build_nonbundled_pyinstaller
call :ensure_build_modules
if errorlevel 1 exit /b 1

if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%ROOT_DIR%build" rmdir /s /q "%ROOT_DIR%build"
mkdir "%DIST_DIR%"
mkdir "%ROOT_DIR%build"
cd /d "%ROOT_DIR%"
"%PYTHON_EXE%" -m PyInstaller --onefile --windowed ^
  --distpath "%DIST_DIR%" ^
  --workpath "%ROOT_DIR%build" ^
  --specpath "%ROOT_DIR%build" ^
  --icon "%ICON_PATH%" ^
  --name "BDOVulkanUtility" ^
  bdo_vulkan_manager.py

if errorlevel 1 (
  echo PyInstaller non-bundled build failed.
  pause
  exit /b 1
)

if exist "%ROOT_DIR%assets" (
  echo Copying assets folder to dist...
  if not exist "%DIST_DIR%\assets" mkdir "%DIST_DIR%\assets"
  xcopy "%ROOT_DIR%assets" "%DIST_DIR%\assets\" /E /I /Y >nul
)

if exist "%ICON_PATH%" (
  copy /Y "%ICON_PATH%" "%DIST_DIR%\BlackDesert.ico" >nul
)

call :cleanup_build_artifacts

echo.
echo Non-bundled PyInstaller build complete.
echo Output is in: %DIST_DIR%
pause
exit /b 0

:build_nonbundled_nuitka
call :ensure_build_modules
if errorlevel 1 exit /b 1

if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"
cd /d "%ROOT_DIR%"
"%PYTHON_EXE%" -m nuitka ^
  --onefile ^
  --windows-console-mode=disable ^
  --enable-plugin=pyqt6 ^
  --noinclude-pytest-mode=nofollow ^
  --noinclude-setuptools-mode=nofollow ^
  --noinclude-unittest-mode=nofollow ^
  --mingw64 ^
  --windows-icon-from-ico=BlackDesert.ico ^
  --include-data-dir=assets=assets ^
  --include-data-files=BlackDesert.ico=BlackDesert.ico ^
  --include-data-files=app.manifest=app.manifest ^
  --output-filename=BDOVulkanUtility.exe ^
  --company-name=KarmaPanda ^
  --product-name="Black Desert Vulkan Utility" ^
  --file-version=1.0.1.0 ^
  --product-version=1.0.1.0 ^
  --file-description="Black Desert Online Vulkan/DXVK Manager" ^
  --copyright="Copyright (c) 2025 KarmaPanda" ^
  --trademarks="Black Desert Online is a trademark of Pearl Abyss" ^
  --disable-ccache ^
  --lto=no ^
  --remove-output ^
  --assume-yes-for-downloads ^
  --output-dir="%NUITKA_BUILD_DIR%" ^
  bdo_vulkan_manager.py

if errorlevel 1 (
  echo Nuitka non-bundled build failed.
  pause
  exit /b 1
)

if exist "%NUITKA_BUILD_DIR%\BDOVulkanUtility.exe" (
  copy /Y "%NUITKA_BUILD_DIR%\BDOVulkanUtility.exe" "%DIST_DIR%\BDOVulkanUtility.exe" >nul
)

if exist "%ROOT_DIR%assets" (
  echo Copying assets folder to dist...
  if not exist "%DIST_DIR%\assets" mkdir "%DIST_DIR%\assets"
  xcopy "%ROOT_DIR%assets" "%DIST_DIR%\assets\" /E /I /Y >nul
)

call :cleanup_build_artifacts

echo.
echo Non-bundled Nuitka build complete.
echo Output is in: %DIST_DIR%
pause
exit /b 0
