@echo off
REM Build BDO Vulkan Utility with Nuitka (bundled assets mode)
REM This includes the assets folders to avoid false positive virus warnings from PyInstaller

REM Activate Python 3.12 virtual environment
call venv-py312\Scripts\activate.bat

python -m nuitka ^
  --onefile ^
  --windows-console-mode=disable ^
  --enable-plugin=tk-inter ^
  --enable-plugin=anti-bloat ^
  --noinclude-pytest-mode=nofollow ^
  --noinclude-setuptools-mode=nofollow ^
  --noinclude-unittest-mode=nofollow ^
  --mingw64 ^
  --windows-icon-from-ico=BlackDesert.ico ^
  --include-data-dir=assets/Normal=assets/Normal ^
  --include-data-dir=assets/Potato=assets/Potato ^
  --include-data-files=BlackDesert.ico=BlackDesert.ico ^
  --output-filename=BDOVulkanUtility.exe ^
  --company-name=KarmaPanda ^
  --product-name="Black Desert Vulkan Utility" ^
  --file-version=1.0.0.0 ^
  --product-version=1.0.0.0 ^
  --file-description="Black Desert Online Vulkan/DXVK Manager" ^
  --copyright="Copyright (c) 2025 KarmaPanda" ^
  --trademarks="Black Desert Online is a trademark of Pearl Abyss" ^
  --disable-ccache ^
  --lto=no ^
  --remove-output ^
  --assume-yes-for-downloads ^
  bdo_vulkan_manager.py

echo.
echo Build complete! Executable is in the current directory.
pause
