@echo off
REM Build BDO Vulkan Utility with Nuitka (non-bundled mode)
REM This requires BDO_Vulkan_API folder to be present alongside the executable

REM Activate Python 3.12 virtual environment
call venv-py312\Scripts\activate.bat

python -m nuitka ^
  --onefile ^
  --windows-console-mode=disable ^
  --enable-plugin=tk-inter ^
  --mingw64 ^
  --windows-icon-from-ico=BlackDesert.ico ^
  --include-data-files=BlackDesert.ico=BlackDesert.ico ^
  --output-filename=BDOVulkanUtility.exe ^
  --company-name=KarmaPanda ^
  --product-name="Black Desert Vulkan Utility" ^
  --file-version=1.0.0.0 ^
  --product-version=1.0.0.0 ^
  --file-description="Black Desert Online Vulkan/DXVK Manager" ^
  --disable-ccache ^
  --lto=no ^
  bdo_vulkan_manager.py

echo.
echo Build complete! Executable is in the current directory.
echo Remember to distribute the BDO_Vulkan_API folder with the executable.
pause
