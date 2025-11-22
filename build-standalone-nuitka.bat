@echo off
REM Build BDO Vulkan Utility with Nuitka (standalone mode - lower false positive rate)
REM This creates a folder with the executable and dependencies instead of a single file
REM This approach typically has fewer antivirus false positives than --onefile

REM Activate Python 3.12 virtual environment
call venv-py312\Scripts\activate.bat

python -m nuitka ^
  --standalone ^
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
  --output-dir=build-standalone ^
  bdo_vulkan_manager.py

echo.
echo Build complete! Executable is in the build-standalone\bdo_vulkan_manager.dist folder.
echo This folder contains the .exe and all dependencies.
echo.
echo This standalone build typically has MUCH fewer antivirus false positives
echo than the single-file --onefile build.
pause
