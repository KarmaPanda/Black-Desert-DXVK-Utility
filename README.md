# Black Desert Online Vulkan Utility — by KarmaPanda

A Windows desktop utility to easily copy and replace DXVK files into the **Black Desert Online (BDO)** folder.  
This tool provides a simple GUI for copying or removing files such as **Normal** or **Potato Graphics** mode Vulkan files into your Black Desert installation.

---

## ✨ Features

- **Mode selection**: Choose between **Normal** and **Potato** presets.
- **Automatic detection**: Scans all available drives for Black Desert installations.
- **Multiple installs**: Supports managing files across multiple game folders.
- **Copy / Remove**: Copy or replace Vulkan files, or remove them, all from one program.
- **UAC-aware**: Prompts for administrator rights when the game is installed in protected directories.
- **Safety check**: Refuses to run if Black Desert (`BlackDesert64.exe`) is currently running.
- **Cache**: Remembers previously detected installations to avoid rescanning every time.
- **Debug mode**: Toggle debug logging and console output via `bdovulkan_config.ini`.

---

## 📦 Installation

1. Download the latest release or build it yourself (see **Build** section).
2. Place the utility in a folder of your choice.
3. (Optional) Place your Vulkan files under `BDO_Vulkan_API/Normal` or `BDO_Vulkan_API/Potato` if using non-bundled mode.

---

## 🚀 Usage

1. **Close Black Desert Online** (the tool will refuse to run if the game is open).
2. Run the utility.
3. Choose the source mode:
   - **Normal** or **Potato**
4. Select one or more detected BDO installation folders:
   - Use **Copy/Replace** to apply the Vulkan files.
   - Use **Remove** to delete them.
5. Done!

---

## ⚙️ Bundled vs Non-Bundled Mode

The application can run in two modes:

### 🔹 Non-Bundled Mode
- The Vulkan files are expected in a folder structure:
```
./BDO_Vulkan_API/Normal
./BDO_Vulkan_API/Potato
```
- You manage the contents of these folders manually.
- Files remain on disk between runs.

### 🔹 Bundled Mode
- Vulkan files are **embedded directly into the application** during build.
- At runtime, the files are **extracted to a temporary folder** (e.g.  
`C:\Users\<User>\AppData\Local\Temp\bdo_vulkan_normal_xxxxxx\`).
- The temporary folder is **automatically deleted** when the application exits.
- This keeps the application directory clean with no leftover assets.

> Switch between bundled and non-bundled mode by editing the `BUNDLED` flag at the top of `bdo_vulkan_manager.py`.

---

## ⚙️ Build

This project uses **Python 3.11+** and **Tkinter** (comes with Python).

Dependencies:
- None beyond the Python standard library.

### Use the included .bat files to compile (if you're on Windows)
```
build-bundled.bat
build-non-bundled.bat 
```

or DIY

### Non-bundled build (expects local `BDO_Vulkan_API` folders):
```bash
pyinstaller --onefile --windowed --icon BlackDesert.ico \
  --add-data "BlackDesert.ico;." \
  bdo_vulkan_manager.py
```

### Bundled build (includes Normal/Potato assets inside the exe):
```bash
pyinstaller --onefile --windowed --icon BlackDesert.ico \
  --add-data "BlackDesert.ico;." \
  --add-data "assets/Normal;assets/Normal" \
  --add-data "assets/Potato;assets/Potato" \
  bdo_vulkan_manager.py
```

---

## 🛠 Configuration

The tool generates bdovulkan_config.ini automatically:

```ini
[general]
debug = false
```

Set debug = true to enable detailed logging and a visible console window.

---

## 🖼 Icon

The utility uses the Black Desert Online icon for both the executable and the window title bar.
If you are building from source, ensure BlackDesert.ico is available or bundled.

---

## 👤 Credits

Developed by KarmaPanda

Inspired by the need for an easy Vulkan installation for Black Desert Online and to easily toggle between the two modes without the need of Nvidia Profile Inspector.

---

## 📸 Screenshots

Source/Mode Selection

![Source/Mode Selection](/screenshots/select_source.png?raw=true "Source/Mode Selection")

Installation Detection

![Installation Detection](/screenshots/installation_detection.png?raw=true "Installation Detection")

Select Installation Menu

![Select Installation Menu](/screenshots/select_installation_menu.png?raw=true "Select Installation Menu")

Copy/Replace Confirmation

![Copy/Replace Confirmation](/screenshots/copy_confirmation.png?raw=true "Copy/Replace Confirmation")

Remove Confirmation

![Remove Confirmation](/screenshots/remove_confirmation.png?raw=true "Remove Confirmation")