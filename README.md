# Black Desert Online Vulkan Utility — by KarmaPanda

A Windows desktop utility to easily copy and replace Vulkan translation-layer files into the **Black Desert Online (BDO)** folder.  
This tool provides a simple GUI for choosing either DXVK (DX11) or VKD3D-Proton (DX12), adjusting DXVK sampler LOD bias when applicable, and copying the selected payload into your Black Desert installation.

---

## ✨ Features

- **LOD bias control**: Use a slider/input to set `d3d11.samplerLodBias` from negative to positive values.
- **Persistent LOD bias**: The selected sampler bias is saved to config and restored on the next launch.
- **Translation layer selector**: Choose DXVK (for DX11) or VKD3D-Proton (for DX12).
- **Automatic detection**: Scans all available drives for Black Desert installations.
- **Multiple installs**: Supports managing files across multiple game folders.
- **Copy / Remove**: Copy or replace Vulkan files, or remove them, all from one program.
- **UAC-aware**: Prompts for administrator rights when the game is installed in protected directories.
- **Safety check**: Refuses to run if Black Desert (`BlackDesert64.exe`) is currently running.
- **Cache**: Remembers previously detected installations to avoid rescanning every time.
- **Portable state**: Configuration and install cache are kept in `%LOCALAPPDATA%\KarmaPanda\BDO_Vulkan_Utility` so builds/folders can share the same saved settings.
- **Legacy migration**: If older local config/cache files are found, the app prompts to import them into AppData and delete the legacy copies.
- **Debug mode**: Toggle debug logging and console output via the AppData config file.

---

## 📦 Installation

1. Download the latest release or build it yourself (see **Build** section).
2. Place the utility in a folder of your choice.
3. (Optional) Place your consolidated [DXVK](https://github.com/doitsujin/DXVK) files under `assets` for non-bundled mode.

---

## 🚀 Usage

1. **Close Black Desert Online** (the tool will refuse to run if the game is open).
2. Run the utility.
3. Choose the **translation layer**:

- **DXVK (DX11 -> Vulkan)**
- **VKD3D-Proton (DX12 -> Vulkan)**

4. If DXVK is selected, adjust the **sampler LOD bias** with the slider or number box. The value is saved automatically and restored on the next launch.
5. Select one or more detected BDO installation folders:
   - Use **Copy/Replace** to apply the Vulkan files.
   - Use **Remove** to delete them.
6. Done!

---

## ⚙️ Bundled vs Non-Bundled Mode

The application can run in two modes:

### 🔹 Non-Bundled Mode

- The Vulkan files are expected in a source folder such as `assets`, or profile subfolders such as:

```
./assets/dxvk
./assets/vkd3d-proton
```

- Backward compatibility is preserved: a flat `assets` folder is still supported.

or another custom folder you select manually.

- You manage the contents of that folder manually.
- Files remain on disk between runs.

### 🔹 Bundled Mode

- Vulkan files are **embedded directly into the application** during build from the single `assets` directory.
- At runtime, the files are **extracted to a temporary folder** (e.g.  
  `C:\Users\<User>\AppData\Local\Temp\bdo_vulkan_assets_xxxxxx\`).
- The temporary folder is **automatically deleted** when the application exits.
- This keeps the application directory clean with no leftover assets.

> Switch between bundled and non-bundled mode by editing the `BUNDLED` flag at the top of `bdo_vulkan_manager.py`.

## 🧩 Asset Layout For DX12 Prep

Recommended structure to support both current DX11 and upcoming DX12 paths:

```text
assets/
├── dxvk/
│   ├── d3d11.dll
│   ├── dxgi.dll
│   └── dxvk.conf
└── vkd3d-proton/
  ├── d3d12.dll
  ├── d3d12core.dll (optional, include when provided)
  └── dxgi.dll (optional depending on your chosen package)
```

If your package ships files differently, place the VKD3D-Proton DLLs in any folder and select that folder manually when prompted.

---

## ⚙️ Build

This project targets **Windows** and expects a Python 3.12 environment with the following build dependencies available in the local virtual environment:

- `PyQt6`
- `PyInstaller`
- `nuitka`

The repo includes a build helper that creates or reuses `venv-py312` automatically and installs missing dependencies before compiling.

### Build helper

From the project root, run:

```bat
build.bat
```

or use one of the supported commands directly:

```bat
build.bat bundled
build.bat bundled-pyinstaller
build.bat bundled-nuitka
build.bat nonbundled
build.bat nonbundled-pyinstaller
build.bat nonbundled-nuitka
```

The helper script writes output to the `dist` folder and cleans temporary build artifacts after completion.

### Manual PyInstaller examples

#### Non-bundled build

```bash
pyinstaller --onefile --windowed --icon BlackDesert.ico \
  --distpath dist \
  --workpath build \
  --specpath build \
  --name BDOVulkanUtility \
  bdo_vulkan_manager.py
```

#### Bundled build

```bash
pyinstaller --onefile --windowed --icon BlackDesert.ico \
  --distpath dist \
  --workpath build \
  --specpath build \
  --add-data "assets;assets" \
  --add-data "BlackDesert.ico;." \
  --name BDOVulkanUtility \
  bdo_vulkan_manager.py
```

> The bundled build embeds the `assets` folder into the executable, while the non-bundled build expects the `assets` directory to remain available next to the app or in a selected custom location.

### Notes

- The app uses `%LOCALAPPDATA%\KarmaPanda\BDO_Vulkan_Utility` for persistent config and install cache, so builds in different folders do not wipe the user state.
- If older local config files are detected, the app offers to migrate them into the AppData folder automatically.

---

## 🛠 Configuration

The tool stores persistent settings in a stable AppData folder so settings can survive different build locations or updates:

```text
%LOCALAPPDATA%\KarmaPanda\BDO_Vulkan_Utility\
├── bdovulkan_config.ini
└── bdovulkan_installs.txt
```

The config is generated automatically:

```ini
[general]
debug = false
lod_bias = 0.0
```

Set `debug = true` to enable detailed logging and a visible console window.

If older local copies of `bdovulkan_config.ini` or `bdovulkan_installs.txt` are found in the program folder, the application will prompt to import them into AppData and delete the legacy copies.

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

Installation Detection

![Installation Detection](/screenshots/installation_detection.png?raw=true "Installation Detection")

Source Scanning

![Source Scanning](/screenshots/scan_source.png?raw=true "Source Scanning")

Select Installation Menu

![Select Installation Menu](/screenshots/select_installation_menu.png?raw=true "Select Installation Menu")

Copy/Replace Confirmation

![Copy/Replace Confirmation](/screenshots/copy_confirmation.png?raw=true "Copy/Replace Confirmation")

Remove Confirmation

![Remove Confirmation](/screenshots/remove_confirmation.png?raw=true "Remove Confirmation")
