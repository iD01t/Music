from __future__ import annotations  # defer evaluation of type hints
import os
import webbrowser
import json
import shlex
import platform
import subprocess
from pathlib import Path
from typing import Optional

try:
    import tkinter as _tk
    from tkinter import ttk as _ttk, messagebox as _messagebox
except Exception:
    _tk = None
    _ttk = None
    _messagebox = None

# It's better to get this from a central place, but for now, we'll keep it here.
APP_VERSION = "1.0.0"

DOWNLOADS_BASE = "https://id01t.store"
DOWNLOADS_LANDING_URL = f"{DOWNLOADS_BASE}/musicforge"
DOWNLOAD_LINKS = [
    (
        "Windows (x64) Installer",
        f"{DOWNLOADS_BASE}/dl/musicforge/MusicForgePro_Win_x64_{APP_VERSION}.exe",
    ),
    (
        "macOS (Universal) .dmg",
        f"{DOWNLOADS_BASE}/dl/musicforge/MusicForgePro_macOS_{APP_VERSION}.dmg",
    ),
    (
        "Linux (AppImage)",
        f"{DOWNLOADS_BASE}/dl/musicforge/MusicForgePro_{APP_VERSION}.AppImage",
    ),
    (
        "Python Source (.py)",
        f"{DOWNLOADS_BASE}/dl/musicforge/musicforge_pro_onepager_final_{APP_VERSION}.py",
    ),
    ("User Guide", f"{DOWNLOADS_BASE}/musicforge/docs"),
]

FFMPEG_URLS = {
    "windows": "https://ffmpeg.org/download.html#build-windows",
    "darwin": "https://ffmpeg.org/download.html#build-mac",
    "linux": "https://ffmpeg.org/download.html#build-linux",
}

_EULA_TITLE = "End User License Agreement"
_EULA_FILE = os.path.expanduser("~/.musicforge_pro_eula.txt")
_EULA_ACCEPT_FLAG = os.path.expanduser("~/.musicforge_pro_eula.accepted")


def _get_embedded_eula_text():
    return """MusicForge Pro — End User License Agreement (EULA)
Version: {ver}

IMPORTANT—READ CAREFULLY: By installing or using this software, you agree to be bound by the terms of this EULA.

1. LICENSE GRANT
The Licensor grants you a personal, non-exclusive, non-transferable license to install and use the Software for commercial or personal purposes. You may not sublicense, rent, lease, or distribute the Software except as expressly allowed in this EULA.

2. OWNERSHIP
The Software is licensed, not sold. All rights, title, and interest remain with the Licensor.

3. RESTRICTIONS
You may not reverse engineer, decompile, or disassemble the Software except to the extent such activity is expressly permitted by applicable law.

4. THIRD-PARTY COMPONENTS
This Software interacts with third-party tools such as FFmpeg. You are responsible for complying with third-party licenses. If you redistribute FFmpeg with your product, you must comply with the applicable LGPL/GPL licensing requirements.

5. WARRANTY DISCLAIMER
THE SOFTWARE IS PROVIDED “AS IS” WITHOUT WARRANTY OF ANY KIND. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE SOFTWARE IS WITH YOU.

6. LIMITATION OF LIABILITY
IN NO EVENT SHALL THE LICENSOR BE LIABLE FOR ANY DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.

7. UPDATES & TELEMETRY
The Software may check for updates. No personal data is collected without your consent.

8. TERMINATION
This EULA is effective until terminated. Your rights will terminate automatically if you fail to comply with any term.

9. GOVERNING LAW
This EULA shall be governed by the laws of your jurisdiction unless local law requires otherwise.

By selecting “I Agree” or by using the Software, you acknowledge that you have read and understood this EULA and agree to be bound by its terms.
""".format(
        ver=APP_VERSION
    )


def ensure_eula_accepted(cli_accept=False):
    """Ensure EULA acceptance once per user. Stores a small flag in home dir."""
    if os.path.exists(_EULA_ACCEPT_FLAG):
        return True
    if cli_accept or _tk is None:
        try:
            os.makedirs(os.path.dirname(_EULA_ACCEPT_FLAG), exist_ok=True)
            with open(_EULA_FILE, "w", encoding="utf-8") as f:
                f.write(_get_embedded_eula_text())
            with open(_EULA_ACCEPT_FLAG, "w", encoding="utf-8") as f:
                f.write("accepted\n")
            return True
        except Exception:
            return True
    try:
        root = _tk.Tk()
        root.withdraw()
        dlg = _tk.Toplevel(root)
        dlg.title(_EULA_TITLE)
        dlg.geometry("700x500")
        frm = _ttk.Frame(dlg, padding=10)
        frm.pack(fill="both", expand=True)
        txt = _tk.Text(frm, wrap="word")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", _get_embedded_eula_text())
        txt.configure(state="disabled")
        btns = _ttk.Frame(frm)
        btns.pack(fill="x", pady=(10, 0))
        agreed = {"ok": False}

        def _ok():
            agreed["ok"] = True
            dlg.destroy()

        def _cancel():
            dlg.destroy()

        _ttk.Button(btns, text="I Agree", command=_ok).pack(side="right", padx=6)
        _ttk.Button(btns, text="Cancel", command=_cancel).pack(side="right")
        dlg.transient(root)
        dlg.grab_set()
        root.wait_window(dlg)
        root.destroy()
        if agreed["ok"]:
            os.makedirs(os.path.dirname(_EULA_ACCEPT_FLAG), exist_ok=True)
            with open(_EULA_FILE, "w", encoding="utf-8") as f:
                f.write(_get_embedded_eula_text())
            with open(_EULA_ACCEPT_FLAG, "w", encoding="utf-8") as f:
                f.write("accepted\n")
            return True
        return False
    except Exception:
        return True


def open_url(url: str) -> None:
    """Attempt to open a URL in the user's browser; fall back to printing it."""
    try:
        if not webbrowser.open(url, new=2):
            raise RuntimeError("webbrowser.open returned False")
    except Exception:
        print(f"Open this link in your browser:\n{url}")


def attach_downloads_ui(app_or_root):
    """Attach a 'Get Downloads' button and Help menu item if possible."""
    try:
        root = getattr(app_or_root, "root", app_or_root)
        bar = getattr(app_or_root, "bottom_bar", None) or getattr(
            app_or_root, "toolbar", None
        )

        def _open_url(url):
            open_url(url)

        def _show_downloads():
            if _tk is None:
                open_url(DOWNLOADS_LANDING_URL)
                return
            dlg = _tk.Toplevel(root)
            dlg.title("Download MusicForge Pro")
            frm = _ttk.Frame(dlg, padding=12)
            frm.pack(fill="both", expand=True)
            _ttk.Label(
                frm, text="Choose a download:", font=("TkDefaultFont", 11, "bold")
            ).pack(anchor="w", pady=(0, 6))
            for label, url in DOWNLOAD_LINKS:
                row = _ttk.Frame(frm)
                row.pack(fill="x", pady=2)
                _ttk.Label(row, text=label).pack(side="left")
                _ttk.Button(row, text="Open", command=lambda u=url: _open_url(u)).pack(
                    side="right"
                )
            _ttk.Button(frm, text="Close", command=dlg.destroy).pack(
                anchor="e", pady=(8, 0)
            )

        if bar is not None and _ttk is not None:
            try:
                _ttk.Button(
                    bar,
                    text="Get Downloads",
                    command=_show_downloads,
                    style="Primary.TButton",
                ).pack(side="right", padx=6)
            except Exception:
                _ttk.Button(bar, text="Get Downloads", command=_show_downloads).pack(
                    side="right", padx=6
                )
            try:
                _ttk.Button(
                    bar,
                    text="Download FFmpeg",
                    command=open_ffmpeg_download_page,
                    style="Primary.TButton",
                ).pack(side="right", padx=6)
            except Exception:
                _ttk.Button(
                    bar, text="Download FFmpeg", command=open_ffmpeg_download_page
                ).pack(side="right", padx=6)
        menubar = getattr(app_or_root, "menubar", None)
        if menubar is not None and hasattr(menubar, "add_cascade"):
            try:
                help_menu = _tk.Menu(menubar, tearoff=0)
                help_menu.add_command(label="Download Links…", command=_show_downloads)
                help_menu.add_command(
                    label="Download FFmpeg…", command=open_ffmpeg_download_page
                )

                def _show_eula():
                    if _tk is None:
                        return
                    _messagebox.showinfo("EULA", _get_embedded_eula_text())

                help_menu.add_command(label="View EULA…", command=_show_eula)
                menubar.add_cascade(label="Help", menu=help_menu)
                if hasattr(root, "config"):
                    root.config(menu=menubar)
            except Exception:
                pass
    except Exception as e:
        try:
            print(f"attach_downloads_ui failed: {e}")
        except Exception:
            pass


def open_ffmpeg_download_page() -> None:
    """Open the official FFmpeg downloads page based on the current operating system."""
    try:
        sysname = platform.system().lower()
        if "windows" in sysname:
            url = FFMPEG_URLS["windows"]
        elif "darwin" in sysname or "mac" in sysname:
            url = FFMPEG_URLS["darwin"]
        else:
            url = FFMPEG_URLS["linux"]
        open_url(url)
    except Exception as e:
        try:
            open_url("https://ffmpeg.org/download.html")
        except Exception:
            print(f"Unable to open FFmpeg download page: {e}")


def ensure_ffmpeg_present_or_prompt(root: Optional[object] = None) -> bool:
    """Check whether FFmpeg and FFprobe are available on the PATH."""
    from .core import FFMPEG  # late import to avoid circular dependency

    try:
        if FFMPEG.is_available():
            return True
    except Exception:
        pass
    try:
        import shutil as _shutil

        ff = _shutil.which("ffmpeg")
        fp = _shutil.which("ffprobe")
        if ff and fp:
            return True
    except Exception:
        pass
    if root is None:
        print(
            "FFmpeg/ffprobe not found. Use 'Download FFmpeg…' from the GUI or add FFmpeg to your PATH."
        )
        return False
    try:
        from tkinter import messagebox as _mb

        if _mb.askyesno(
            "FFmpeg Required",
            "FFmpeg/ffprobe not found.\n\nWould you like to open the official download page?",
        ):
            open_ffmpeg_download_page()
    except Exception:
        try:
            open_ffmpeg_download_page()
        except Exception:
            pass
    return False


def guided_ffmpeg_install() -> None:
    """Provide a simple guided workflow for downloading and extracting FFmpeg."""
    try:
        import tkinter.filedialog as fd
        from tkinter import messagebox as _mb

        folder = fd.askdirectory(title="Choose a folder to store FFmpeg")
        open_ffmpeg_download_page()
        if folder:
            try:
                sysname = platform.system().lower()
                if "windows" in sysname:
                    os.startfile(folder)
                elif "darwin" in sysname:
                    subprocess.run(["open", folder], check=False)
                else:
                    subprocess.run(["xdg-open", folder], check=False)
            except Exception:
                pass
        try:
            _mb.showinfo(
                "Guided FFmpeg Install",
                "1) Download a prebuilt FFmpeg package in your browser.\n2) Extract/unzip it into the folder you chose.\n3) In Music Forge, use ‘Find FFmpeg…’ to select the ffmpeg executable inside the bin/ directory.",
            )
        except Exception:
            pass
    except Exception:
        try:
            print(
                "Please download a prebuilt FFmpeg package from ffmpeg.org, extract it to a folder, and add the 'bin' directory to your PATH."
            )
        except Exception:
            pass


def hard_guard_samefile(src_path, dst_path, overwrite=False):
    """Refuse accidental in-place overwrite even if overwrite=True."""
    try:
        if os.path.exists(dst_path):
            if not overwrite:
                return False, "exists"
        try:
            if os.path.samefile(src_path, dst_path):
                return (
                    False,
                    "Refusing to overwrite source; adjust --output/--template.",
                )
        except FileNotFoundError:
            pass
        return True, ""
    except Exception as e:
        return False, f"filesystem check failed: {e}"


def inline_validate_settings(s):
    """Fallback validation when external validator is unavailable."""
    try:
        if not (-36.0 <= s.lufs <= -8.0):
            raise ValueError("--lufs must be between -36 and -8")
        if s.tp > -1.0:
            raise ValueError("--tp must be ≤ -1.0 dBTP")
        if s.lra < 0:
            raise ValueError("--lra must be ≥ 0")
        if s.bit_depth not in (16, 24, 32):
            raise ValueError("--bit-depth must be 16/24/32")
        if s.sr not in (22050, 32000, 44100, 48000, 88200, 96000):
            raise ValueError("--sr invalid")
        if not (1 <= s.ch <= 8):
            raise ValueError("--ch must be 1..8")
    except Exception as e:
        raise


def ensure_progress_flags(cmd_list, helper_used=False):
    """When not using improved runner, ensure structured progress for parsers."""
    if helper_used:
        return cmd_list
    text = " " + " ".join(cmd_list) + " "
    if " -progress " not in text:
        cmd_list.extend(["-progress", "pipe:1", "-nostats", "-v", "error"])
    return cmd_list


def ffprobe_duration(path: Path) -> float:
    """
    Legacy wrapper for probing a media file's duration.
    """
    from .core import FFMPEG  # late import to avoid circular dependency

    try:
        return FFMPEG.probe_duration(str(path))
    except Exception:
        return 0.0
