# bdo_vulkan_manager.py
import ctypes, os, sys, shutil, string, logging, subprocess
from pathlib import Path
import configparser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import base64

# ==========================
# BUILD-TIME SWITCH
# ==========================
BUNDLED = True   # <<< SET THIS: True = bundle assets via --add-data, False = use local ./BDO_Vulkan_API

# ==========================
# Runtime context & paths
# ==========================
FROZEN = getattr(sys, "frozen", False)
APP_DIR   = (Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent)
MEIPASS_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR)).resolve()  # where PyInstaller unpacks data

CONFIG_FILE = APP_DIR / "bdovulkan_config.ini"
CACHE_FILE  = APP_DIR / "bdovulkan_installs.txt"
ICON_FILE   = "BlackDesert.ico"  # searched in APP_DIR and MEIPASS_DIR

SOURCE_ROOT = APP_DIR / "BDO_Vulkan_API"   # used when BUNDLED=False
ASSETS_NORMAL_REL = Path("assets/Normal")  # used when BUNDLED=True
ASSETS_POTATO_REL = Path("assets/Potato")  # used when BUNDLED=True

GAME_EXE = "BlackDesert64.exe"
APP_TITLE = "Black Desert Online Vulkan Utility — by KarmaPanda"

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
            CONFIG_FILE.write_text("[general]\ndebug = false\n", encoding="utf-8")
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

# ==========================
# Icon utilities (robust for bundled & non-bundled)
# ==========================
# Small fallback icon (64x64 PNG) encoded as base64 so wm_iconphoto always has something.
ICON_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAAsSAAALEgHS3X78"
    "AAABX0lEQVR4nO3YwUrDQBQF4N8m1gK2hCw0Qw0b2GqQ0Q2mEJg0y7p9J7JgGq3l1r6O3q4g3n"
    "cQy9w8w2mL5u5b9cO5c0m+1gYhIhIhIhIhIhIhIhIhIhK/4n3iS1wO2G1f9zWJ3gR0x4pD9K1b"
    "6w4mWQm2w6v5lfr1w6p2n1G9fQ6vls2qv7qj3w0x0b9l6D4a4X8S4Yxkq+g7G5J2n8Wc7oP1nA"
    "8WwQ1kqH8zjE3qv7p7C7c1h3sJ5Xy1xH0yQzq6g8Jb8b8yq0lQ3kq9Q4oZ9J6w2W4cGFiYmJgY"
    "GBgYGBgYGBgYGBgYGBgYGBgYGBg4H+QyQm8B0yQy9F3bCq3mH4r2gZy4m2w9m0c8m0Y8m0Y8m0"
    "c8m0Zf4+o0Ff4a3xg9jDF3Q7z0nC6bq5m7mJmZl/8BRl4L3e0k7nQAAAABJRU5ErkJggg=="
)

_APP_ICON_PHOTO = None  # keep a global reference so it doesn't get GC'd

def _find_ico_path() -> Path | None:
    # 1) Next to exe/script
    p = APP_DIR / ICON_FILE
    if p.exists():
        return p
    # 2) In MEIPASS (when you do --add-data "BlackDesert.ico;.")
    p = MEIPASS_DIR / ICON_FILE
    if p.exists():
        return p
    return None

def _load_photo_from_b64_png():
    global _APP_ICON_PHOTO
    try:
        _APP_ICON_PHOTO = tk.PhotoImage(data=ICON_PNG_B64)
        return _APP_ICON_PHOTO
    except Exception:
        return None

def setup_app_icon(win: tk.Misc):
    """Set both iconbitmap (.ico) and wm_iconphoto (PNG) safely."""
    ico = _find_ico_path()
    if ico is not None:
        try:
            win.iconbitmap(default=str(ico.resolve()))
        except Exception:
            pass
    photo = _load_photo_from_b64_png()
    if photo is not None:
        try:
            win.wm_iconphoto(True, photo)
        except Exception:
            pass

def new_window(title: str, geometry: tuple[int, int] | None = None) -> tk.Toplevel:
    w = tk.Toplevel(ROOT)
    setup_app_icon(w)
    w.title(title)
    if geometry:
        width, height = geometry
        w.update_idletasks()
        x = w.winfo_screenwidth() // 2 - width // 2
        y = w.winfo_screenheight() // 2 - height // 2
        w.geometry(f"{width}x{height}+{x}+{y}")
    return w

# ==========================
# Single hidden root
# ==========================
ROOT = tk.Tk()
ROOT.withdraw()
ROOT.title(APP_TITLE)
setup_app_icon(ROOT)

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
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}" {params}', None, 1)

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
        # Make a small topmost dialog to ensure it's seen
        messagebox.showerror(
            "Game is Running",
            f"{GAME_EXE} appears to be running.\n\nPlease close Black Desert Online before using this utility.",
            parent=ROOT
        )
        sys.exit(0)

# ==========================
# Progress dialog
# ==========================
class ProgressDialog:
    def __init__(self, title="Scanning...", initial="Starting..."):
        self.cancelled = False
        self.win = new_window(title, geometry=(520, 140))
        self.win.resizable(False, False)
        self.label = tk.Label(self.win, text=initial, width=62, anchor="w", justify="left")
        self.label.pack(padx=14, pady=(12, 6))
        self.pb = ttk.Progressbar(self.win, mode="indeterminate", length=440)
        self.pb.pack(padx=14, pady=(0, 8))
        self.pb.start(40)
        tk.Button(self.win, text="Cancel", width=12, command=self._on_cancel).pack(pady=(0, 10))
        self.win.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_cancel(self): self.cancelled = True
    def update_status(self, text: str): self.label.config(text=text); self.win.update()
    def close(self):
        try: self.pb.stop()
        except Exception: pass
        try: self.win.destroy()
        except Exception: pass

# ==========================
# Asset handling (bundled vs non-bundled)
# ==========================
def _bundle_path(rel: Path) -> Path:
    return (MEIPASS_DIR / rel).resolve()

def copy_tree(src: Path, dst: Path):
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        for f in files:
            s = Path(root) / f
            d = dst / rel / f
            try:
                shutil.copy2(s, d)
            except Exception as e:
                log.debug(f"[ASSETS] Copy failed {s} -> {d}: {e}")

def ensure_source_for_mode(mode: str) -> str | None:
    """
    Returns source folder path for selected mode.
    - BUNDLED=True: copy from bundled assets (assets/<Mode>) into ./BDO_Vulkan_API/<Mode> if empty/missing.
    - BUNDLED=False: use ./BDO_Vulkan_API/<Mode>; if empty/missing, prompt user to pick.
    """
    target_dir = SOURCE_ROOT / mode
    target_dir.mkdir(parents=True, exist_ok=True)

    if BUNDLED:
        rel = ASSETS_NORMAL_REL if mode.lower() == "normal" else ASSETS_POTATO_REL
        bundled_src = _bundle_path(rel)
        has_files = any(target_dir.rglob("*"))
        if not has_files:
            if bundled_src.exists():
                log.debug(f"[ASSETS] Extracting bundled {mode} -> {target_dir}")
                copy_tree(bundled_src, target_dir)
            else:
                messagebox.showinfo(
                    "Source Missing",
                    f"No embedded files found for '{mode}'.\n\nSelect the source folder manually.",
                    parent=ROOT
                )
                chosen = filedialog.askdirectory(parent=ROOT, title="Select the SOURCE folder (files to manage)", mustexist=True)
                return chosen or None
        return str(target_dir)
    else:
        has_files = any(target_dir.rglob("*"))
        if has_files:
            return str(target_dir)
        messagebox.showinfo(
            "Source Missing",
            f"Default source not found or empty:\n{target_dir}\n\nPlease select the source folder manually.",
            parent=ROOT
        )
        chosen = filedialog.askdirectory(parent=ROOT, title="Select the SOURCE folder (files to manage)", mustexist=True)
        return chosen or None

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
    skip_dirs = {"System Volume Information", "$Recycle.Bin", "Windows", "Recovery", "PerfLogs"}
    scanned_dirs = 0
    for root, dirs, files in os.walk(drive_root, topdown=True, followlinks=False):
        if dlg and dlg.cancelled:
            break
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        scanned_dirs += 1
        if dlg and scanned_dirs % 100 == 0:
            dlg.update_status(f"Scanning {drive_root} (deep)\nDirs scanned: {scanned_dirs}")
        if GAME_EXE in files:
            log.debug(f"[DEEP] Found at {root}")
            found.append(root)
    if dlg and not dlg.cancelled:
        dlg.update_status(f"Scanning {drive_root} (deep) complete\nDirs scanned: {scanned_dirs}")
    return found

def scan_all_installs_with_progress():
    dlg = ProgressDialog(title="Scanning for Black Desert", initial="Detecting drives...")
    installs, seen = [], set()
    try:
        for drv in get_drives():
            if dlg.cancelled:
                break
            dlg.update_status(f"Scanning {drv} (quick)")
            for p in quick_search_on_drive(drv, dlg):
                if p not in seen:
                    installs.append(p); seen.add(p)
            if not any(str(p).startswith(drv) for p in installs):
                if dlg.cancelled:
                    break
                dlg.update_status(f"Scanning {drv} (deep)\nThis may take a while…")
                for p in deep_scan_drive(drv, dlg):
                    if p not in seen:
                        installs.append(p); seen.add(p)
            else:
                log.debug(f"[SCAN] Skipping deep scan on {drv}: found in quick pass.")
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
def choose_source_mode():
    win = new_window("Select Source Mode", geometry=(420, 150))
    # Extra insurance: re-apply the icon here (addresses rare cases on some systems)
    setup_app_icon(win)
    win.resizable(False, False)

    state = {"mode": None, "cancelled": False}

    def on_cancel():
        state["cancelled"] = True
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_cancel)
    win.bind("<Escape>", lambda e: on_cancel())

    tk.Label(win, text="Choose which source to use:").pack(padx=14, pady=(12, 6))

    btns = tk.Frame(win); btns.pack(pady=(6, 2))
    def set_mode(m): state["mode"] = m; win.destroy()
    tk.Button(btns, text="Normal", width=14, command=lambda: set_mode("Normal")).pack(side="left", padx=8)
    tk.Button(btns, text="Potato", width=14, command=lambda: set_mode("Potato")).pack(side="left", padx=8)

    # footer credits
    foot = tk.Frame(win); foot.pack(pady=(2, 8), fill="x")
    tk.Label(foot, text=APP_TITLE, anchor="w").pack(side="left", padx=12)

    win.grab_set(); win.wait_window()

    if state["cancelled"]:
        return None
    return state["mode"] or "Normal"

def browse_folder(prompt: str):
    path = filedialog.askdirectory(parent=ROOT, title=prompt, mustexist=True)
    if path:
        log.debug(f"[UI] Folder chosen: {path}")
    return path or ""

def select_installs_dialog(paths):
    win = new_window("Select Black Desert Installation(s)", geometry=(840, 520))
    tk.Label(win, text="Select one or more installations:").pack(padx=12, pady=8, anchor="w")

    lb = tk.Listbox(win, selectmode=tk.MULTIPLE, exportselection=False, font=("Consolas", 10))
    lb.pack(fill="both", expand=True, padx=12)
    for p in sorted(paths):
        lb.insert(tk.END, p)

    state = {"mode": None, "sel_idx": []}
    bar = tk.Frame(win); bar.pack(pady=10)

    def select_all(): lb.select_set(0, tk.END)
    def clear_sel(): lb.select_clear(0, tk.END)
    def ensure_sel():
        if not lb.curselection():
            messagebox.showinfo("No selection", "Please select at least one installation.", parent=win)
            return False
        return True
    def set_mode_and_close(m):
        if m in ("COPY","REMOVE") and not ensure_sel():
            return
        state["mode"] = m
        state["sel_idx"] = list(lb.curselection())
        win.destroy()

    tk.Button(bar, text="Select All",   width=14, command=select_all).pack(side="left", padx=6)
    tk.Button(bar, text="Clear",        width=14, command=clear_sel).pack(side="left", padx=6)
    tk.Button(bar, text="Copy/Replace", width=16, command=lambda: set_mode_and_close("COPY")).pack(side="left", padx=6)
    tk.Button(bar, text="Remove",       width=14, command=lambda: set_mode_and_close("REMOVE")).pack(side="left", padx=6)
    tk.Button(bar, text="Rescan",       width=14, command=lambda: set_mode_and_close("RESCAN")).pack(side="left", padx=6)

    # footer credits
    foot = tk.Frame(win); foot.pack(pady=(0,8), fill="x")
    tk.Label(foot, text=APP_TITLE, anchor="w").pack(side="left", padx=12)

    win.grab_set(); win.wait_window()
    mode = state["mode"]
    sel_paths = [paths[i] for i in state["sel_idx"]] if mode in ("COPY","REMOVE") else []
    log.debug(f"[UI] Mode: {mode}; Selected: {sel_paths}")
    return (mode, sel_paths)

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
        if messagebox.askyesno("Administrator Permission Required",
                               "Some selected installations are in protected locations and require administrator\n"
                               "permission to modify.\n\nRelaunch with UAC elevation now?",
                               parent=ROOT):
            log.debug("[UAC] Relaunching elevated...")
            relaunch_as_admin()
            sys.exit(0)
        else:
            messagebox.showwarning("Continuing without elevation",
                                   "Continuing without elevation. Some actions may fail due to permissions.",
                                   parent=ROOT)
            log.debug("[UAC] User chose to continue without elevation.")

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
    # 0) Guard: exit if Black Desert is running
    guard_game_not_running_or_exit()

    # 1) Mode selection
    mode = choose_source_mode()
    if mode is None:
        return  # user canceled

    # 2) Resolve source based on bundling mode
    source = ensure_source_for_mode(mode)
    if not source:
        return
    log.debug(f"[MAIN] Source = {source}")

    # 3) Load cache or scan
    installs = load_cache()
    if not installs:
        if messagebox.askyesno("Scan for Installations",
                               "No cached Black Desert installations found.\n\nScan all drives now?",
                               parent=ROOT):
            installs = scan_all_installs_with_progress()
            if installs:
                write_cache(installs)
            else:
                if messagebox.askyesno("Not Found",
                                       "No installations found automatically.\n\nSelect the game folder manually?",
                                       parent=ROOT):
                    manual = filedialog.askdirectory(parent=ROOT, title="Select your Black Desert Online folder (must contain BlackDesert64.exe)", mustexist=True)
                    if not manual:
                        return
                    if not (Path(manual) / GAME_EXE).exists():
                        messagebox.showerror("Invalid Folder",
                                             f"BlackDesert64.exe not found in:\n{manual}",
                                             parent=ROOT)
                        return
                    installs = [manual]
                    write_cache(installs)
                else:
                    return
        else:
            manual = filedialog.askdirectory(parent=ROOT, title="Select your Black Desert Online folder (must contain BlackDesert64.exe)", mustexist=True)
            if not manual:
                return
            if not (Path(manual) / GAME_EXE).exists():
                messagebox.showerror("Invalid Folder",
                                     f"BlackDesert64.exe not found in:\n{manual}",
                                     parent=ROOT)
                return
            installs = [manual]
            write_cache(installs)

    # 4) Selection loop
    while True:
        mode_action, selected = select_installs_dialog(installs)
        if mode_action == "RESCAN":
            if messagebox.askyesno("Rescan", "Rescan all drives now? (This may take a while)", parent=ROOT):
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
            messagebox.showinfo("No Selection", "No installations selected.", parent=ROOT)
            return

        # validate & prune cache
        bad = [p for p in selected if not (Path(p) / GAME_EXE).exists()]
        if bad:
            messagebox.showerror("Invalid Selection",
                                 "These paths do not contain BlackDesert64.exe:\n\n" + "\n".join(bad),
                                 parent=ROOT)
            installs = [p for p in installs if p not in bad]
            write_cache(installs)
            continue

        # UAC check + confirm
        ensure_uac_for_paths(selected)
        if not messagebox.askyesno(
            "Confirm",
            f"Source:\n{source}\n\nAction: {mode_action}\n\nDestinations:\n" + "\n".join(selected),
            parent=ROOT
        ):
            return

        # Execute
        if mode_action == "COPY":
            total = copy_replace(source, selected)
            messagebox.showinfo("Done", f"Copied/Replaced: {total}", parent=ROOT)
        else:
            total = remove_matching(source, selected)
            messagebox.showinfo("Done", f"Removed: {total}", parent=ROOT)
        return

if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            ROOT.destroy()
        except Exception:
            pass
