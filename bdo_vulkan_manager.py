# bdo_vulkan_manager.py
import ctypes
import json
import os
import sys
import shutil
import string
import logging
import subprocess
from pathlib import Path
import configparser
from urllib import request, error
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QMessageBox, QPushButton, QProgressDialog, QSlider, QVBoxLayout,
    QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
import base64
import tempfile
import atexit
import re

# ==========================
# Runtime context & paths
# ==========================
# Detect if running as compiled executable (Nuitka uses __compiled__, PyInstaller uses frozen)
FROZEN = getattr(sys, "frozen", False) or "__compiled__" in globals()
APP_DIR = (Path(sys.executable).resolve(
).parent if FROZEN else Path(__file__).resolve().parent)
# For Nuitka: resources are typically next to exe; for PyInstaller: in _MEIPASS
MEIPASS_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR)).resolve()

# ==========================
# Build/runtime bundle mode
# ==========================


def resolve_bundle_mode() -> bool:
    """Resolve the asset mode automatically, with an explicit env override.

    Supported overrides: BDO_VULKAN_BUNDLED=1/true/yes or 0/false/no.
    If no override is supplied, use the project layout that is actually present at runtime.
    """
    override = os.environ.get("BDO_VULKAN_BUNDLED")
    if override is not None:
        return override.strip().lower() not in {"0", "false", "no", "off"}

    # Prefer the asset layout that exists in the current runtime directory.
    runtime_dir = APP_DIR
    bundled_dir = runtime_dir / "assets"
    nonbundled_dir = runtime_dir / "BDO_Vulkan_API"

    if bundled_dir.exists() and any(bundled_dir.iterdir()):
        return True
    if nonbundled_dir.exists() and any(nonbundled_dir.iterdir()):
        return False

    # Fallback for compiled single-file builds that extract assets into the executable folder.
    return True


# Determine the active bundle mode at runtime so the app does not require a code edit
# for bundled vs non-bundled variants.
BUNDLED = resolve_bundle_mode()

CONFIG_FILE = APP_DIR / "bdovulkan_config.ini"
CACHE_FILE = APP_DIR / "bdovulkan_installs.txt"
ICON_FILE = "BlackDesert.ico"  # searched in APP_DIR and MEIPASS_DIR

SOURCE_ROOT = APP_DIR / "BDO_Vulkan_API"   # used when BUNDLED=False
ASSETS_ROOT_REL = Path("assets")  # used when BUNDLED=True

GAME_EXE = "BlackDesert64.exe"
APP_VERSION = "1.0.1"
APP_TITLE = f"Black Desert Online Vulkan Utility — by KarmaPanda v{APP_VERSION}"
GITHUB_REPO_OWNER = "KarmaPanda"
GITHUB_REPO_NAME = "Black-Desert-DXVK-Utility"
GITHUB_RELEASES_PAGE_URL = (
    f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases"
)
DEFAULT_GITHUB_RELEASES_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"
)
UPDATER_MANIFEST_URL = os.environ.get(
    "BDO_VULKAN_UPDATE_MANIFEST_URL",
    DEFAULT_GITHUB_RELEASES_URL,
)

COMMON_RELATIVE_PATHS = [
    r"\BlackDesert",
    r"\PearlAbyss",
    r"\Program Files\BlackDesert",
    r"\Program Files (x86)\BlackDesert",
    r"\Program Files\PearlAbyss",
    r"\Program Files (x86)\PearlAbyss",
    r"\Program Files\Steam\steamapps\common\Black Desert Online",
    r"\Program Files (x86)\Steam\steamapps\common\Black Desert Online",
    r"\Games\BlackDesert",
]

# ==========================
# Config (debug) + console
# ==========================


def load_config():
    cfg = configparser.ConfigParser()
    cfg["general"] = {"debug": "false"}
    if CONFIG_FILE.exists():
        try:
            cfg.read(CONFIG_FILE, encoding="utf-8")
        except Exception:
            pass
    else:
        try:
            CONFIG_FILE.write_text(
                "[general]\ndebug = false\n", encoding="utf-8")
        except Exception:
            pass
    return cfg


CFG = load_config()
DEBUG = CFG.getboolean("general", "debug", fallback=False)


def _attach_debug_console_if_needed():
    if not DEBUG:
        return
    # If already running from a console, skip.
    if ctypes.windll.kernel32.GetConsoleWindow():
        return
    if ctypes.windll.kernel32.AllocConsole():
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        try:
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
            sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        except Exception:
            pass


_attach_debug_console_if_needed()

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("BDO-Vulkan")


def _resource_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()

    candidates = [
        Path(getattr(sys, "_MEIPASS", "")).resolve(
        ) if getattr(sys, "_MEIPASS", "") else None,
        Path(sys.executable).resolve().parent if getattr(
            sys, "executable", None) else None,
        APP_DIR,
        MEIPASS_DIR,
        Path.cwd().resolve(),
        Path(tempfile.gettempdir()).resolve(),
        Path.home().resolve(),
    ]

    if getattr(sys, "executable", None):
        exe_path = Path(sys.executable).resolve()
        for parent in [exe_path.parent, *exe_path.parent.parents[:4]]:
            candidates.append(parent)

    for candidate in candidates:
        if candidate is None:
            continue
        try:
            candidate = candidate.resolve()
        except Exception:
            pass
        if candidate in seen:
            continue
        seen.add(candidate)
        roots.append(candidate)

    return roots


def _find_ico_path() -> Path | None:
    for base in _resource_roots():
        candidate = (base / ICON_FILE).resolve()
        if candidate.exists() and candidate.is_file():
            return candidate
        # Fall back to immediate children only; avoid scanning unrelated Windows temp/download folders.
        for child in base.iterdir():
            if child.name == ICON_FILE and child.is_file():
                return child.resolve()
    return None


# ==========================
# Qt-only app helpers
# ==========================

def ensure_qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def qt_info(title: str, message: str):
    ensure_qt_app()
    QMessageBox.information(None, title, message)


def qt_error(title: str, message: str):
    ensure_qt_app()
    QMessageBox.critical(None, title, message)


def qt_warning(title: str, message: str):
    ensure_qt_app()
    QMessageBox.warning(None, title, message)


def qt_yes_no(title: str, message: str) -> bool:
    ensure_qt_app()
    result = QMessageBox.question(None, title, message)
    return result == QMessageBox.StandardButton.Yes


def qt_directory_prompt(title: str) -> str:
    ensure_qt_app()
    path = QFileDialog.getExistingDirectory(
        None, title, options=QFileDialog.Option.ShowDirsOnly)
    return path or ""


def set_window_icon(widget, icon_path: Path | None = None):
    ico = icon_path or _find_ico_path()
    if ico is not None:
        try:
            from PyQt6.QtGui import QIcon
            widget.setWindowIcon(QIcon(str(ico.resolve())))
        except Exception:
            pass


def get_windows_scale_factor() -> float:
    if os.name != "nt":
        return 1.0
    try:
        return max(1.0, ctypes.windll.user32.GetDpiForSystem() / 96.0)
    except Exception:
        return 1.0


def ui_font(size: int = 9, family: str = "Segoe UI") -> tuple[str, int]:
    scale = get_windows_scale_factor()
    scaled_size = max(8, min(16, int(round(size * scale))))
    return (family, scaled_size)


def enable_dpi_awareness():
    if os.name != "nt":
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(0x00001000)
        return
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


enable_dpi_awareness()

# ==========================
# UAC helpers
# ==========================


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin():
    params = " ".join([f'"{p}"' for p in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{__file__}" {params}', None, 1)

# ==========================
# Game-running guard
# ==========================


def is_process_running(image_name: str) -> bool:
    """
    Uses 'tasklist' to detect a running process by image name (e.g., BlackDesert64.exe).
    Avoids external deps like psutil.
    """
    try:
        res = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}"],
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        out = res.stdout or ""
        # tasklist returns a table where the image name appears if running
        return image_name.lower() in out.lower()
    except Exception as e:
        log.debug(f"[PROC] tasklist failed: {e}")
        return False


def guard_game_not_running_or_exit():
    if is_process_running(GAME_EXE):
        qt_error(
            "Game is Running",
            f"{GAME_EXE} appears to be running.\n\nPlease close Black Desert Online before importing or removing DXVK files.",
        )
        sys.exit(0)


def ensure_game_closed_for_mutation(action_label: str):
    if is_process_running(GAME_EXE):
        if not qt_yes_no(
            "Game is Running",
            f"{GAME_EXE} is currently running.\n\nPlease close Black Desert Online before {action_label}.\n\nWould you like to retry after closing it?",
        ):
            return False
        qt_error(
            "Game is Running",
            f"{GAME_EXE} is still running.\n\n{action_label} was cancelled.",
        )
        return False
    return True

# ==========================
# Progress dialog
# ==========================


class ProgressDialog:
    def __init__(self, title="Scanning...", initial="Starting..."):
        self.cancelled = False
        self.dialog = QProgressDialog(initial, "Cancel", 0, 0)
        self.dialog.setWindowTitle(title)
        self.dialog.setAutoClose(False)
        self.dialog.setAutoReset(False)
        self.dialog.setMinimumDuration(0)
        self.dialog.canceled.connect(self._on_cancel)
        self.dialog.setValue(0)
        self.dialog.show()

    def _on_cancel(self):
        self.cancelled = True

    def update_status(self, text: str):
        self.dialog.setLabelText(text)
        QApplication.processEvents()

    def close(self):
        try:
            self.dialog.close()
        except Exception:
            pass

# ==========================
# Asset handling (bundled vs non-bundled)
# ==========================


def _bundle_path(rel: Path) -> Path:
    return (MEIPASS_DIR / rel).resolve()


def _looks_like_asset_dir(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    if not any(path.iterdir()):
        return False
    names = {p.name.lower() for p in path.iterdir() if p.is_file()}
    return bool(names & {"dxvk.conf", "d3d11.dll", "dxgi.dll"}) or bool(names)


def _find_asset_directory_in_root(root: Path) -> Path | None:
    if not root.exists():
        return None

    for relative_name in [ASSETS_ROOT_REL, Path("BDO_Vulkan_API")]:
        candidate = (root / relative_name).resolve()
        if _looks_like_asset_dir(candidate):
            return candidate

    assets_dir = (root / "assets").resolve()
    if _looks_like_asset_dir(assets_dir):
        return assets_dir

    # Onefile bundle extraction may put the payload in a temp folder that is not directly
    # named "assets"; scan for the key DXVK files anywhere under the runtime root.
    for marker in ["dxvk.conf", "d3d11.dll", "dxgi.dll"]:
        matches = list(root.rglob(marker))
        if matches:
            return matches[0].parent

    if any((root / name).exists() for name in ["dxvk.conf", "d3d11.dll", "dxgi.dll"]):
        return root

    return None


def resolve_assets_root() -> Path | None:
    """Return the active assets directory for bundled or source execution.

    For onefile builds, the extracted resource directory is usually either the exe folder
    or the active _MEIPASS temp extraction root. Search only those runtime roots to avoid
    accidentally matching unrelated Windows directories named "assets".
    """
    roots = _resource_roots()

    for root in roots:
        found = _find_asset_directory_in_root(root)
        if found is not None:
            return found

    return None


TEMP_ASSET_ROOT = APP_DIR / ".bdo_vulkan_tmp"
TEMP_ASSET_FOLDERS: list[Path] = []


def cleanup_temp_asset_folders():
    for temp_dir in list(TEMP_ASSET_FOLDERS):
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
                log.debug(f"[ASSETS] Cleaned up temp dir {temp_dir}")
        except Exception as e:
            log.debug(f"[ASSETS] Failed to clean temp dir {temp_dir}: {e}")
        finally:
            if temp_dir in TEMP_ASSET_FOLDERS:
                TEMP_ASSET_FOLDERS.remove(temp_dir)


atexit.register(cleanup_temp_asset_folders)


def _register_temp_asset_dir(temp_dir: Path):
    temp_dir = temp_dir.resolve()
    if temp_dir not in TEMP_ASSET_FOLDERS:
        TEMP_ASSET_FOLDERS.append(temp_dir)
    return temp_dir


def copy_dxvk_conf(src: Path, dst_dir: Path):
    dst_dir = _register_temp_asset_dir(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_conf = dst_dir / "dxvk.conf"
    if src.exists():
        shutil.copy2(src, dst_conf)
    else:
        dst_conf.write_text(
            "# Generated by Black Desert Vulkan Utility\n"
            "# Preserve the full DXVK config and only override samplerLodBias when needed.\n"
            "d3d11.samplerLodBias = 0.0\n"
            "d3d9.samplerLodBias = 0.0\n",
            encoding="utf-8",
        )
    return dst_conf


def copy_all_asset_files(src_root: Path, dst_dir: Path) -> list[Path]:
    """Copy the full DXVK asset payload into a temp working directory."""
    dst_dir = _register_temp_asset_dir(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = []

    if not src_root.exists():
        return copied

    for src in src_root.iterdir():
        dst = dst_dir / src.name
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        copied.append(dst)

    return copied


def patch_sampler_lod_bias(file_path: Path, bias: float):
    """Update only the samplerLodBias entry while preserving the rest of the DXVK config."""
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            "# Generated by Black Desert Vulkan Utility\n"
            "# Preserve the full DXVK config and only override samplerLodBias when needed.\n"
            f"d3d11.samplerLodBias = {bias}\n"
            "d3d9.samplerLodBias = 0.0\n",
            encoding="utf-8",
        )
        return

    lines = file_path.read_text(encoding="utf-8").splitlines()
    updated = False

    for idx, line in enumerate(lines):
        if re.match(r"^\s*#?\s*(?:d3d11|d3d9)\.samplerLodBias\s*=", line):
            value_part = re.search(r"=(\s*[-+]?(?:\d+\.\d+|\d+))", line)
            if value_part:
                line = line[:value_part.start(
                    1)] + str(float(bias)) + line[value_part.end(1):]
            else:
                line = line.rstrip() + f" = {float(bias)}"
            lines[idx] = line
            updated = True

    if not updated:
        lines.append(f"d3d11.samplerLodBias = {bias}")

    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_dxvk_conf(source_path: Path) -> Path:
    """Return the target dxvk.conf path, creating a default file when absent."""
    candidate = source_path / "dxvk.conf"
    if candidate.exists():
        return candidate

    matches = list(source_path.rglob("dxvk.conf"))
    if matches:
        return matches[0]

    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text(
        "# Generated by Black Desert Vulkan Utility\n"
        "d3d11.samplerLodBias = 0.0\n"
        "d3d9.samplerLodBias = 0.0\n",
        encoding="utf-8",
    )
    return candidate


def ensure_source_for_mode(mode: str) -> str | None:
    """Resolve the active asset directory for bundled or source execution."""
    if BUNDLED:
        bundled_src = resolve_assets_root()
        if bundled_src is None or not bundled_src.exists():
            qt_info(
                "Source Missing",
                "No embedded or sidecar files found under 'assets'.\n\nSelect the source folder manually.",
            )
            chosen = qt_directory_prompt(
                "Select the SOURCE folder (files to manage)")
            return chosen or None

        TEMP_ASSET_ROOT.mkdir(parents=True, exist_ok=True)
        tempdir = _register_temp_asset_dir(
            TEMP_ASSET_ROOT / f"bdo_vulkan_assets_{os.getpid()}_{len(TEMP_ASSET_FOLDERS)}")
        tempdir.mkdir(parents=True, exist_ok=True)
        copied = copy_all_asset_files(bundled_src, tempdir)
        if not copied:
            src_conf = ensure_dxvk_conf(bundled_src)
            copy_dxvk_conf(src_conf, tempdir)
        log.debug(
            f"[ASSETS] Copied temp DXVK payload -> {tempdir} ({len(copied)} files)")
        return str(tempdir)

    target_dir = resolve_assets_root() or SOURCE_ROOT
    if not target_dir.exists() or not any(target_dir.rglob("*")):
        qt_info(
            "Source Missing",
            f"Default source not found or empty:\n{target_dir}\n\nPlease select the source folder manually.",
        )
        chosen = qt_directory_prompt(
            "Select the SOURCE folder (files to manage)")
        return chosen or None

    tempdir = _register_temp_asset_dir(
        APP_DIR / ".bdo_vulkan_tmp" / f"source_{os.getpid()}_{len(TEMP_ASSET_FOLDERS)}")
    tempdir.mkdir(parents=True, exist_ok=True)
    copied = copy_all_asset_files(target_dir, tempdir)
    if not copied:
        src_conf = ensure_dxvk_conf(target_dir)
        copy_dxvk_conf(src_conf, tempdir)
    log.debug(
        f"[ASSETS] Copied temp DXVK payload from source -> {tempdir} ({len(copied)} files)")
    return str(tempdir)


def ensure_source_for_lod_bias(lod_bias: float) -> str | None:
    """Build a source directory from the consolidated assets root and patch the sampler LOD bias."""
    source = ensure_source_for_mode("Assets")
    if source is None:
        return None

    source_path = Path(source)
    dxvk_conf = ensure_dxvk_conf(source_path)
    patch_sampler_lod_bias(dxvk_conf, lod_bias)
    return str(source_path)


# ==========================
# Drive discovery & scan
# ==========================
def get_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate(string.ascii_uppercase):
        if bitmask & (1 << i):
            root = f"{letter}:\\"
            try:
                if os.path.isdir(root):
                    drives.append(root)
            except Exception:
                pass
    if not drives:
        drives = ["C:\\"]
    log.debug(f"Detected drives: {drives}")
    return drives


def quick_search_on_drive(drive_root: str, dlg: ProgressDialog | None = None):
    found = []
    for rel in COMMON_RELATIVE_PATHS:
        if dlg and dlg.cancelled:
            break
        candidate = Path(drive_root + rel)
        if dlg:
            dlg.update_status(f"Scanning {drive_root} (quick)\n{candidate}")
        try:
            if (candidate / GAME_EXE).exists():
                log.debug(f"[QUICK] Found at {candidate}")
                found.append(str(candidate))
        except PermissionError:
            log.debug(f"[QUICK] Permission denied: {candidate}")
        except Exception as e:
            log.debug(f"[QUICK] Error at {candidate}: {e}")
    return found


def deep_scan_drive(drive_root: str, dlg: ProgressDialog | None = None):
    found = []
    skip_dirs = {"System Volume Information",
                 "$Recycle.Bin", "Windows", "Recovery", "PerfLogs"}
    scanned_dirs = 0
    for root, dirs, files in os.walk(drive_root, topdown=True, followlinks=False):
        if dlg and dlg.cancelled:
            break
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        scanned_dirs += 1
        if dlg and scanned_dirs % 100 == 0:
            dlg.update_status(
                f"Scanning {drive_root} (deep)\nDirs scanned: {scanned_dirs}")
        if GAME_EXE in files:
            log.debug(f"[DEEP] Found at {root}")
            found.append(root)
    if dlg and not dlg.cancelled:
        dlg.update_status(
            f"Scanning {drive_root} (deep) complete\nDirs scanned: {scanned_dirs}")
    return found


def scan_all_installs_with_progress():
    dlg = ProgressDialog(title="Scanning for Black Desert",
                         initial="Detecting drives...")
    installs, seen = [], set()
    try:
        for drv in get_drives():
            if dlg.cancelled:
                break
            dlg.update_status(f"Scanning {drv} (quick)")
            for p in quick_search_on_drive(drv, dlg):
                if p not in seen:
                    installs.append(p)
                    seen.add(p)
            if not any(str(p).startswith(drv) for p in installs):
                if dlg.cancelled:
                    break
                dlg.update_status(
                    f"Scanning {drv} (deep)\nThis may take a while…")
                for p in deep_scan_drive(drv, dlg):
                    if p not in seen:
                        installs.append(p)
                        seen.add(p)
            else:
                log.debug(
                    f"[SCAN] Skipping deep scan on {drv}: found in quick pass.")
    finally:
        dlg.close()
    log.debug(f"Scan complete. Found installs: {installs}")
    return installs

# ==========================
# Cache
# ==========================


def load_cache():
    paths = []
    if CACHE_FILE.exists():
        try:
            for line in CACHE_FILE.read_text(encoding="utf-8").splitlines():
                p = line.strip().strip('"')
                if p and (Path(p) / GAME_EXE).exists():
                    paths.append(p)
                else:
                    log.debug(f"[CACHE] Invalid or missing exe: {p}")
        except Exception as e:
            log.debug(f"[CACHE] Error reading cache: {e}")
    log.debug(f"[CACHE] Loaded: {paths}")
    return paths


def write_cache(paths):
    try:
        uniq = sorted(dict.fromkeys(paths))
        CACHE_FILE.write_text("\n".join(uniq), encoding="utf-8")
        log.debug(f"[CACHE] Wrote {len(uniq)} path(s) to {CACHE_FILE}")
    except Exception as e:
        log.debug(f"[CACHE] Write failed: {e}")

# ==========================
# UI helpers
# ==========================


def create_lod_bias_controls(parent_widget):
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    title = QLabel("DXVK sampler LOD bias:")
    title.setStyleSheet("font-size: 11pt; font-family: 'Segoe UI';")
    layout.addWidget(title)

    desc = QLabel(
        "Positive = less details / higher value removes more foliage, trees, etc from game\nNegative = more details / sharper textures and increases level of detail in game")
    desc.setWordWrap(True)
    layout.addWidget(desc)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(-300, 1600)
    slider.setValue(0)

    spinbox = QDoubleSpinBox()
    spinbox.setRange(-3.0, 16.0)
    spinbox.setSingleStep(0.1)
    spinbox.setDecimals(1)
    spinbox.setValue(0.0)

    def sync_slider_from_spin():
        value = float(spinbox.value())
        slider.setValue(int(round(value * 100.0)))

    def sync_spin_from_slider(value: int):
        spinbox.setValue(value / 100.0)

    slider.valueChanged.connect(sync_spin_from_slider)
    spinbox.valueChanged.connect(sync_slider_from_spin)

    layout.addWidget(slider)
    layout.addWidget(spinbox)
    parent_widget.addLayout(layout)
    return slider, spinbox


def choose_source_mode_qt():
    ensure_qt_app()
    dialog = QDialog()
    dialog.setWindowTitle("Adjust samplerLodBias")
    set_window_icon(dialog)
    dialog.resize(500, 220)
    dialog.setModal(True)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)
    _, spinbox = create_lod_bias_controls(layout)

    buttons = QHBoxLayout()
    ok_btn = QPushButton("Apply")
    cancel_btn = QPushButton("Cancel")
    buttons.addWidget(ok_btn)
    buttons.addWidget(cancel_btn)
    layout.addLayout(buttons)

    result = {"value": 0.0}

    def on_ok():
        result["value"] = float(spinbox.value())
        dialog.accept()

    ok_btn.clicked.connect(on_ok)
    cancel_btn.clicked.connect(dialog.reject)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return result["value"]


def choose_source_mode():
    return choose_source_mode_qt()


def browse_folder(prompt: str):
    path = qt_directory_prompt(prompt)
    if path:
        log.debug(f"[UI] Folder chosen: {path}")
    return path


def select_installs_dialog(paths):
    ensure_qt_app()
    dialog = QDialog()
    dialog.setWindowTitle("Select Black Desert Installation(s)")
    set_window_icon(dialog)
    dialog.resize(840, 520)
    dialog.setModal(True)

    layout = QVBoxLayout(dialog)

    version_label = QLabel(f"Version: {APP_VERSION}")
    version_label.setStyleSheet(
        "font-size: 10pt; font-family: 'Segoe UI'; color: #666666;")
    layout.addWidget(version_label)

    _, spinbox = create_lod_bias_controls(layout)

    label = QLabel("Select one or more installations:")
    label.setStyleSheet("font-size: 11pt; font-family: 'Segoe UI';")
    layout.addWidget(label)

    list_widget = QListWidget()
    list_widget.setSelectionMode(list_widget.SelectionMode.MultiSelection)
    for p in sorted(paths):
        list_widget.addItem(p)
    layout.addWidget(list_widget)

    warning_label = QLabel(
        "WARNING: Close Black Desert Online before Copy/Replace or Remove.\n"
        "The game must be closed before any DXVK files are changed."
    )
    warning_label.setWordWrap(True)
    warning_label.setStyleSheet(
        "color: #b45f06; font-size: 10pt; font-family: 'Segoe UI'; font-weight: bold;"
    )
    layout.addWidget(warning_label)

    buttons = QHBoxLayout()
    select_all_btn = QPushButton("Select All")
    clear_btn = QPushButton("Clear")
    check_updates_btn = QPushButton("Check for Updates")
    copy_btn = QPushButton("Copy/Replace")
    remove_btn = QPushButton("Remove")
    rescan_btn = QPushButton("Rescan")
    buttons.addWidget(select_all_btn)
    buttons.addWidget(clear_btn)
    buttons.addWidget(check_updates_btn)
    buttons.addWidget(copy_btn)
    buttons.addWidget(remove_btn)
    buttons.addWidget(rescan_btn)
    layout.addLayout(buttons)

    state = {"mode": None, "selected": [], "lod_bias": 0.0}

    def set_mode(mode):
        selected = [list_widget.item(i).text() for i in range(
            list_widget.count()) if list_widget.item(i).isSelected()]
        if mode in ("COPY", "REMOVE") and not selected:
            QMessageBox.information(
                dialog, "No selection", "Please select at least one installation.")
            return
        if mode in ("COPY", "REMOVE") and is_process_running(GAME_EXE):
            QMessageBox.warning(
                dialog,
                "Close Black Desert First",
                f"{GAME_EXE} is currently running.\n\nPlease close Black Desert Online before using Copy/Replace or Remove.",
            )
            return
        state["mode"] = mode
        state["selected"] = selected
        state["lod_bias"] = float(spinbox.value())
        dialog.accept()

    select_all_btn.clicked.connect(lambda: list_widget.selectAll())
    clear_btn.clicked.connect(list_widget.clearSelection)
    check_updates_btn.clicked.connect(lambda: check_for_updates())
    copy_btn.clicked.connect(lambda: set_mode("COPY"))
    remove_btn.clicked.connect(lambda: set_mode("REMOVE"))
    rescan_btn.clicked.connect(lambda: set_mode("RESCAN"))

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return (None, [], 0.0)

    return (state["mode"], state["selected"], state["lod_bias"])

# ==========================
# Actions
# ==========================


def ensure_uac_for_paths(paths):
    needs_elev = False
    for p in paths:
        test = Path(p) / ".__bdo_uac_test.tmp"
        try:
            with open(test, "w", encoding="utf-8") as f:
                f.write("test")
            test.unlink(missing_ok=True)
        except Exception:
            needs_elev = True
            log.debug(f"[UAC] Write test failed at {p}")
            break

    if needs_elev and not is_admin():
        if qt_yes_no(
            "Administrator Permission Required",
            "Some selected installations are in protected locations and require administrator\n"
            "permission to modify.\n\nRelaunch with UAC elevation now?",
        ):
            log.debug("[UAC] Relaunching elevated...")
            relaunch_as_admin()
            sys.exit(0)
        else:
            qt_warning(
                "Continuing without elevation",
                "Continuing without elevation. Some actions may fail due to permissions.",
            )
            log.debug("[UAC] User chose to continue without elevation.")


def parse_version(value: str) -> tuple[int, int, int, str]:
    text = str(value or "0.0.0").strip().lower().lstrip("vV")
    match = re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[.-]?(.*))?", text)
    if not match:
        return (0, 0, 0, "")
    major = int(match.group(1) or 0)
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    suffix = match.group(4) or ""
    return (major, minor, patch, suffix)


def version_is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


def load_update_manifest_from_file(path: Path | str | None) -> dict | None:
    if path is None:
        return None
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return None
    try:
        with p.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, dict):
            return payload
    except Exception as exc:
        log.debug(f"[UPDATE] Failed to read manifest from {p}: {exc}")
    return None


def normalize_github_release_manifest(payload: dict) -> dict | None:
    if not isinstance(payload, dict):
        return None

    tag_name = str(payload.get("tag_name")
                   or payload.get("version") or "").strip()
    assets = payload.get("assets") or []
    download_url = ""
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name") or "").lower()
            url = str(asset.get("browser_download_url")
                      or asset.get("download_url") or "").strip()
            if url and (name.endswith(".exe") or "bdovulkanutility" in name.lower() or "blackdesert" in name.lower()):
                download_url = url
                break
    if not download_url:
        download_url = str(payload.get("download_url") or payload.get(
            "browser_download_url") or "").strip()

    if not tag_name and not download_url:
        return None

    normalized = dict(payload)
    normalized["version"] = tag_name
    normalized["download_url"] = download_url
    return normalized


def fetch_update_manifest() -> dict | None:
    candidates = []
    if UPDATER_MANIFEST_URL and UPDATER_MANIFEST_URL != "https://example.invalid/version.json":
        candidates.append(UPDATER_MANIFEST_URL)
    local_manifest = APP_DIR / "version.json"
    if local_manifest.exists():
        candidates.append(str(local_manifest))
    for candidate in candidates:
        try:
            if candidate.startswith("http://") or candidate.startswith("https://"):
                req = request.Request(
                    candidate,
                    headers={
                        "User-Agent": f"BDO-Vulkan-Utility/{APP_VERSION}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                with request.urlopen(req, timeout=15) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    if isinstance(payload, dict):
                        manifest = normalize_github_release_manifest(payload)
                        if manifest:
                            return manifest
                        return payload
            else:
                manifest = load_update_manifest_from_file(candidate)
                if manifest:
                    return manifest
        except Exception as exc:
            log.debug(f"[UPDATE] Manifest fetch failed for {candidate}: {exc}")
    return None


def download_file_to_path(url: str, destination: Path) -> bool:
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        req = request.Request(
            url,
            headers={"User-Agent": f"BDO-Vulkan-Utility/{APP_VERSION}"},
        )
        with request.urlopen(req, timeout=30) as resp, destination.open("wb") as fh:
            shutil.copyfileobj(resp, fh)
        return destination.exists() and destination.stat().st_size > 0
    except Exception as exc:
        log.debug(f"[UPDATE] Download failed: {exc}")
        return False


def schedule_executable_swap(new_exe: Path, current_exe: Path) -> bool:
    try:
        temp_dir = Path(tempfile.gettempdir()) / "bdo_vulkan_update"
        temp_dir.mkdir(parents=True, exist_ok=True)
        batch_path = temp_dir / "bdo_vulkan_replace.bat"
        script = (
            "@echo off\r\n"
            "setlocal\r\n"
            "set \"NEW=%~1\"\r\n"
            "set \"OLD=%~2\"\r\n"
            "timeout /t 2 /nobreak >nul\r\n"
            "copy /Y \"%NEW%\" \"%OLD%\" >nul\r\n"
            "start \"\" \"%OLD%\"\r\n"
            "del /f /q \"%~f0\"\r\n"
        )
        batch_path.write_text(script, encoding="utf-8")
        subprocess.Popen(
            ["cmd", "/c", str(batch_path), str(new_exe), str(current_exe)],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except Exception as exc:
        log.debug(f"[UPDATE] Failed to schedule replacement: {exc}")
        return False


def check_for_updates(show_if_up_to_date: bool = True) -> bool:
    manifest = fetch_update_manifest()
    if not manifest:
        qt_info(
            "Update Check",
            "Unable to check for updates right now.\n\nThe GitHub release feed could not be reached.",
        )
        return False

    latest_version = str(manifest.get("version")
                         or manifest.get("tag_name") or "").strip()
    if not latest_version:
        qt_info(
            "Update Check",
            "The release manifest did not include a version number.",
        )
        return False

    if not version_is_newer(latest_version, APP_VERSION):
        if show_if_up_to_date:
            qt_info(
                "Up to Date",
                f"You are running version {APP_VERSION}.\n\nThe latest release is {latest_version}.",
            )
        return False

    message = (
        f"Version {latest_version} is available.\n\n"
        "Because the project publishes multiple variants (bundled vs. non-bundled and PyInstaller vs. Nuitka), "
        "you must download the correct build from the GitHub Releases page."
    )

    if not qt_yes_no("Update Available", message + "\n\nOpen the releases page now?"):
        return False

    try:
        QDesktopServices.openUrl(QUrl(GITHUB_RELEASES_PAGE_URL))
    except Exception:
        qt_info("Update Available", message +
                f"\n\nOpen this page: {GITHUB_RELEASES_PAGE_URL}")
    return True


def copy_replace(source_root: str, dest_paths: list[str]):
    copied = 0
    for root, _, files in os.walk(source_root):
        for name in files:
            src = Path(root) / name
            for dest in dest_paths:
                try:
                    shutil.copy2(src, Path(dest) / name)
                    log.debug(f"[COPY] {name} -> {dest}")
                    copied += 1
                except Exception as e:
                    log.debug(f"[COPY] Failed {name} -> {dest}: {e}")
    return copied


def remove_matching(source_root: str, dest_paths: list[str]):
    removed = 0
    for root, _, files in os.walk(source_root):
        for name in files:
            for dest in dest_paths:
                target = Path(dest) / name
                if target.exists():
                    try:
                        target.unlink()
                        log.debug(f"[REMOVE] {name} x {dest}")
                        removed += 1
                    except Exception as e:
                        log.debug(f"[REMOVE] Failed {name} x {dest}: {e}")
    return removed

# ==========================
# Main
# ==========================


def main():
    # 0) Check for an app update before doing any work.
    try:
        check_for_updates(show_if_up_to_date=False)
    except Exception as exc:
        log.debug(f"[UPDATE] Automatic check failed: {exc}")

    # 1) The app may be opened while the game is running; only mutation actions require it to be closed.

    # 2) Load cache or scan
    installs = load_cache()
    if not installs:
        if qt_yes_no("Scan for Installations",
                     "No cached Black Desert installations found.\n\nScan all drives now?"):
            installs = scan_all_installs_with_progress()
            if installs:
                write_cache(installs)
            else:
                if qt_yes_no("Not Found",
                             "No installations found automatically.\n\nSelect the game folder manually?"):
                    manual = qt_directory_prompt(
                        "Select your Black Desert Online folder (must contain BlackDesert64.exe)")
                    if not manual:
                        return
                    if not (Path(manual) / GAME_EXE).exists():
                        qt_error("Invalid Folder",
                                 f"BlackDesert64.exe not found in:\n{manual}")
                        return
                    installs = [manual]
                    write_cache(installs)
                else:
                    return
        else:
            manual = qt_directory_prompt(
                "Select your Black Desert Online folder (must contain BlackDesert64.exe)")
            if not manual:
                return
            if not (Path(manual) / GAME_EXE).exists():
                qt_error("Invalid Folder",
                         f"BlackDesert64.exe not found in:\n{manual}")
                return
            installs = [manual]
            write_cache(installs)

    # 4) Selection loop
    while True:
        mode_action, selected, lod_bias = select_installs_dialog(installs)
        if mode_action == "RESCAN":
            if qt_yes_no("Rescan", "Rescan all drives now? (This may take a while)"):
                installs = scan_all_installs_with_progress()
                if installs:
                    write_cache(installs)
                else:
                    try:
                        if CACHE_FILE.exists():
                            CACHE_FILE.unlink()
                    except Exception:
                        pass
            continue

        if not mode_action:
            return
        if not selected:
            qt_info("No Selection", "No installations selected.")
            continue

        # validate & prune cache
        bad = [p for p in selected if not (Path(p) / GAME_EXE).exists()]
        if bad:
            qt_error("Invalid Selection",
                     "These paths do not contain BlackDesert64.exe:\n\n" + "\n".join(bad))
            installs = [p for p in installs if p not in bad]
            write_cache(installs)
            continue

        source = ensure_source_for_lod_bias(float(lod_bias))
        if not source:
            continue
        log.debug(f"[MAIN] Source = {source} | samplerLodBias = {lod_bias}")

        if mode_action in ("COPY", "REMOVE"):
            if not ensure_game_closed_for_mutation("importing DXVK files" if mode_action == "COPY" else "removing DXVK files"):
                continue

        # UAC check + confirm
        ensure_uac_for_paths(selected)
        if not qt_yes_no(
            "Confirm",
            f"Source:\n{source}\n\nAction: {mode_action}\n\nDestinations:\n" +
                "\n".join(selected),
        ):
            continue

        # Execute
        if mode_action == "COPY":
            total = copy_replace(source, selected)
            qt_info("Done", f"Copied/Replaced: {total}")
        else:
            total = remove_matching(source, selected)
            qt_info("Done", f"Removed: {total}")
        continue


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    try:
        ico = _find_ico_path()
        if ico is not None:
            try:
                from PyQt6.QtGui import QIcon
                app.setWindowIcon(QIcon(str(ico)))
            except Exception:
                pass
        main()
    finally:
        app.quit()
