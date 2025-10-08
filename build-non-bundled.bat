pyinstaller --onefile --windowed ^
  --icon BlackDesert.ico ^
  --add-data "BlackDesert.ico;." ^
  --name "BDOVulkanUtility" ^
  bdo_vulkan_manager.py

pause