pyinstaller --onefile --windowed ^
  --icon BlackDesert.ico ^
  --add-data "assets/Normal;assets/Normal" ^
  --add-data "assets/Potato;assets/Potato" ^
  --add-data "BlackDesert.ico;." ^
  --name "BDOVulkanUtility" ^
  bdo_vulkan_manager.py
  
pause
