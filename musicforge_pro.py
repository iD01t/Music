
from __future__ import annotations  # defer evaluation of type hints
import os
from pathlib import Path

def ffprobe_duration(path: Path) -> float:
    """
    Legacy wrapper for probing a media file's duration.  Rather than
    shelling out via ``ffprobe`` directly, delegate to the central
    :class:`FFmpegManager` instance.  This ensures consistent behaviour
    between builds and avoids stale global state.  If probing fails
    (e.g., FFmpeg is unavailable or the file is invalid) return
    ``0.0``.

    Parameters
    ----------
    path: Path
        Path to the media file whose duration is to be probed.

    Returns
    -------
    float
        The duration in seconds, or ``0.0`` on failure.
    """
    try:
        # ``FFMPEG`` is defined later in this module and looked up at runtime
        return FFMPEG.probe_duration(str(path))  # type: ignore[name-defined]
    except Exception:
        return 0.0

# --- Release add-ons (EULA, Downloads, Validation, Progress) ---
import webbrowser, json, shlex
try:
    import tkinter as _tk
    from tkinter import ttk as _ttk, messagebox as _messagebox
except Exception:
    _tk = None
    _ttk = None
    _messagebox = None
# --- end add-ons imports ---

# === Release Helpers (non-invasive) ============================================
APP_VERSION = globals().get("APP_VERSION", "1.0.0")

# ==== App identity & download endpoints (id01t.store) ====
# Define a base host for all product downloads.  Changing this string will
# automatically update all download links exposed in the GUI and help menu.
DOWNLOADS_BASE = "https://id01t.store"
DOWNLOADS_LANDING_URL = f"{DOWNLOADS_BASE}/musicforge"
DOWNLOAD_LINKS = [
    ("Windows (x64) Installer", f"{DOWNLOADS_BASE}/dl/musicforge/MusicForgePro_Win_x64_{APP_VERSION}.exe"),
    ("macOS (Universal) .dmg",  f"{DOWNLOADS_BASE}/dl/musicforge/MusicForgePro_macOS_{APP_VERSION}.dmg"),
    ("Linux (AppImage)",        f"{DOWNLOADS_BASE}/dl/musicforge/MusicForgePro_{APP_VERSION}.AppImage"),
    ("Python Source (.py)",     f"{DOWNLOADS_BASE}/dl/musicforge/musicforge_pro_onepager_final_{APP_VERSION}.py"),
    ("User Guide",              f"{DOWNLOADS_BASE}/musicforge/docs"),
]

# Official FFmpeg download URLs per operating system.  Used by the GUI's
# toolbar/help menu to direct users to the appropriate section of the
# official FFmpeg download page.  Customize these as needed for your
# distribution or platform preferences.
FFMPEG_URLS = {
    "windows": "https://ffmpeg.org/download.html#build-windows",
    "darwin":  "https://ffmpeg.org/download.html#build-mac",
    "linux":   "https://ffmpeg.org/download.html#build-linux",
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
""".format(ver=APP_VERSION)

def ensure_eula_accepted(cli_accept=False):
    """Ensure EULA acceptance once per user. Stores a small flag in home dir."""
    if os.path.exists(_EULA_ACCEPT_FLAG):
        return True
    # if CLI-only or flag passed, accept silently
    if cli_accept or _tk is None:
        # Write the EULA text and flag without prompting.  Ensure the
        # parent directory exists so the writes do not fail on
        # non-existent directories.  If an error occurs during writing,
        # we still proceed to avoid blocking CLI automation.
        try:
            # Ensure parent directory for the accept flag exists
            os.makedirs(os.path.dirname(_EULA_ACCEPT_FLAG), exist_ok=True)
            with open(_EULA_FILE, "w", encoding="utf-8") as f:
                f.write(_get_embedded_eula_text())
            with open(_EULA_ACCEPT_FLAG, "w", encoding="utf-8") as f:
                f.write("accepted\n")
            return True
        except Exception:
            return True  # don't block execution on I/O issues
    # show a modal dialog
    try:
        root = _tk.Tk()
        root.withdraw()
        dlg = _tk.Toplevel(root)
        dlg.title(_EULA_TITLE)
        dlg.geometry("700x500")
        frm = _ttk.Frame(dlg, padding=10); frm.pack(fill="both", expand=True)
        txt = _tk.Text(frm, wrap="word"); txt.pack(fill="both", expand=True)
        txt.insert("1.0", _get_embedded_eula_text())
        txt.configure(state="disabled")
        btns = _ttk.Frame(frm); btns.pack(fill="x", pady=(10,0))
        agreed = {"ok": False}
        def _ok():
            agreed["ok"] = True; dlg.destroy()
        def _cancel():
            dlg.destroy()
        _ttk.Button(btns, text="I Agree", command=_ok).pack(side="right", padx=6)
        _ttk.Button(btns, text="Cancel", command=_cancel).pack(side="right")
        dlg.transient(root); dlg.grab_set(); root.wait_window(dlg)
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
        return True  # don't block on GUI errors

# -----------------------------------------------------------------------------
# Safe URL opener
#
# In sandboxed or restricted environments, opening a URL via the standard
# ``webbrowser`` module may silently fail.  This helper attempts to open a
# URL in the user's default browser and, if that fails, prints the URL
# so the user can copy/paste it manually.  Use this instead of
# ``webbrowser.open`` or ``webbrowser.open_new_tab``.
def open_url(url: str) -> None:
    """Attempt to open a URL in the user's browser; fall back to printing it."""
    try:
        import webbrowser as _wb
        # new=2 requests a new tab if possible.  Return value is False if the
        # operation was unsuccessful.
        if not _wb.open(url, new=2):
            raise RuntimeError("webbrowser.open returned False")
    except Exception:
        # As a last resort, print the URL for the user to copy/paste.
        print(f"Open this link in your browser:\n{url}")

def attach_downloads_ui(app_or_root):
    """Attach a 'Get Downloads' button and Help menu item if possible."""
    try:
        root = getattr(app_or_root, "root", app_or_root)
        # toolbar/bottom: add a simple button if a container exists
        bar = getattr(app_or_root, "bottom_bar", None) or getattr(app_or_root, "toolbar", None)
        def _open_url(url): open_url(url)
        def _show_downloads():
            if _tk is None:
                open_url(DOWNLOADS_LANDING_URL)
                return
            dlg = _tk.Toplevel(root); dlg.title("Download MusicForge Pro")
            frm = _ttk.Frame(dlg, padding=12); frm.pack(fill="both", expand=True)
            _ttk.Label(frm, text="Choose a download:", font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(0,6))
            for label, url in DOWNLOAD_LINKS:
                row = _ttk.Frame(frm); row.pack(fill="x", pady=2)
                _ttk.Label(row, text=label).pack(side="left")
                _ttk.Button(row, text="Open", command=lambda u=url: _open_url(u)).pack(side="right")
            _ttk.Button(frm, text="Close", command=dlg.destroy).pack(anchor="e", pady=(8,0))
        if bar is not None and _ttk is not None:
            # Add a button to open the main downloads dialog.  Use the primary
            # button style so that it visually stands out as a call to action.
            try:
                _ttk.Button(bar, text="Get Downloads", command=_show_downloads, style="Primary.TButton").pack(side="right", padx=6)
            except Exception:
                # Fallback: if the style isn't defined yet, omit the style arg.
                _ttk.Button(bar, text="Get Downloads", command=_show_downloads).pack(side="right", padx=6)
            # Add a button to go directly to the FFmpeg download page.  Use the
            # same primary style for consistency with other CTAs.
            try:
                _ttk.Button(bar, text="Download FFmpeg", command=open_ffmpeg_download_page, style="Primary.TButton").pack(side="right", padx=6)
            except Exception:
                _ttk.Button(bar, text="Download FFmpeg", command=open_ffmpeg_download_page).pack(side="right", padx=6)
        # menu
        menubar = getattr(app_or_root, "menubar", None)
        help_menu = None
        if menubar is not None and hasattr(menubar, "add_cascade"):
            try:
                help_menu = _tk.Menu(menubar, tearoff=0)
                help_menu.add_command(label="Download Links…", command=_show_downloads)
                # Additional command: open the official FFmpeg download page
                help_menu.add_command(label="Download FFmpeg…", command=open_ffmpeg_download_page)
                def _show_eula():
                    if _tk is None: return
                    _messagebox.showinfo("EULA", _get_embedded_eula_text())
                help_menu.add_command(label="View EULA…", command=_show_eula)
                menubar.add_cascade(label="Help", menu=help_menu)
                if hasattr(root, "config"): root.config(menu=menubar)
            except Exception:
                pass
    except Exception as e:
        # Log any unexpected errors during UI attachment.  Fail open so
        # that absence of a downloads button does not crash the app.
        try:
            print(f"attach_downloads_ui failed: {e}")
        except Exception:
            pass

# ----------------------- FFmpeg Download Helper ------------------------
def open_ffmpeg_download_page() -> None:
    """
    Open the official FFmpeg downloads page based on the current operating
    system.  This is used by the GUI to direct users to an appropriate
    download page when they need to install FFmpeg/FFprobe.  If called
    in a non-GUI context, it simply opens the page in the default browser.
    """
    try:
        import platform
        sysname = platform.system().lower()
        if "windows" in sysname:
            url = FFMPEG_URLS["windows"]
        elif "darwin" in sysname or "mac" in sysname:
            url = FFMPEG_URLS["darwin"]
        else:
            url = FFMPEG_URLS["linux"]
        open_url(url)
    except Exception as e:
        # Fall back to the generic landing page on any error
        try:
            open_url("https://ffmpeg.org/download.html")
        except Exception:
            print(f"Unable to open FFmpeg download page: {e}")

# ----------------------- FFmpeg Setup Helpers ------------------------

def ensure_ffmpeg_present_or_prompt(root: Optional[object] = None) -> bool:
    """
    Check whether FFmpeg and FFprobe are available on the PATH.  If they are
    missing and a GUI root and messagebox are available, prompt the user
    to open the official FFmpeg download page.  This helper returns
    ``True`` if FFmpeg is present and ``False`` otherwise.

    This function is intended to be called once at startup in GUI mode
    to proactively guide non‑technical users through installing FFmpeg.
    In headless contexts or when a messagebox is unavailable, it
    silently prints a hint instead of raising.
    """
    try:
        # If FFmpeg is already available, simply return True
        if FFMPEG.is_available():
            return True
    except Exception:
        # In case FFMPEG manager is unavailable, fall back to shutil check
        pass
    try:
        import shutil as _shutil
        ff = _shutil.which("ffmpeg")
        fp = _shutil.which("ffprobe")
        if ff and fp:
            return True
    except Exception:
        pass
    # FFmpeg is not present; decide how to notify the user
    if root is None:
        # headless/CLI: print a hint to the console.  Use a single line
        # message to avoid syntax errors if this code is minified or reflowed.
        print(
            "FFmpeg/ffprobe not found. Use 'Download FFmpeg…' from the GUI or "
            "add FFmpeg to your PATH."
        )
        return False
    # If we have a GUI root and a messagebox, ask the user whether to open
    # the official download page.  Avoid crashing if messagebox is missing.
    try:
        from tkinter import messagebox as _mb  # type: ignore
        if _mb.askyesno(
            "FFmpeg Required",
            "FFmpeg/ffprobe not found.\n\nWould you like to open the official download page?"
        ):
            open_ffmpeg_download_page()
    except Exception:
        # As a last resort, just attempt to open the page
        try:
            open_ffmpeg_download_page()
        except Exception:
            pass
    return False


def guided_ffmpeg_install() -> None:
    """
    Provide a simple guided workflow for downloading and extracting FFmpeg.
    This helper opens the official download page in the user's browser,
    prompts the user to select a folder for extraction, attempts to open
    that folder in the platform's file manager, and displays clear
    instructions on next steps.  All operations are best‑effort and
    failures are silently ignored to avoid disrupting the user experience.
    """
    try:
        # Lazily import tkinter modules so this function works in CLI mode
        import tkinter.filedialog as fd  # type: ignore
        from tkinter import messagebox as _mb  # type: ignore
        import platform
        import os
        import subprocess
        # Ask the user to pick a folder (may be empty if they cancel)
        folder = fd.askdirectory(title="Choose a folder to store FFmpeg")
        # Open the official FFmpeg download page in the default browser
        open_ffmpeg_download_page()
        # If a folder was chosen, attempt to open it in the OS file explorer
        if folder:
            try:
                sysname = platform.system().lower()
                if "windows" in sysname:
                    os.startfile(folder)  # type: ignore[attr-defined]
                elif "darwin" in sysname:
                    subprocess.run(["open", folder], check=False)
                else:
                    subprocess.run(["xdg-open", folder], check=False)
            except Exception:
                pass
        # Provide step‑by‑step guidance to the user
        try:
            _mb.showinfo(
                "Guided FFmpeg Install",
                "1) Download a prebuilt FFmpeg package in your browser.\n"
                "2) Extract/unzip it into the folder you chose.\n"
                "3) In Music Forge, use ‘Find FFmpeg…’ to select the ffmpeg executable inside the bin/ directory."
            )
        except Exception:
            pass
    except Exception:
        # In non‑GUI contexts, fall back to a simple console message
        try:
            print(
                "Please download a prebuilt FFmpeg package from ffmpeg.org,"
                " extract it to a folder, and add the 'bin' directory to your PATH."
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
                return False, "Refusing to overwrite source; adjust --output/--template."
        except FileNotFoundError:
            pass
        return True, ""
    except Exception as e:
        # Fail closed on unexpected filesystem errors.  Returning True here
        # would allow potentially unsafe overwrites to proceed silently.
        return False, f"filesystem check failed: {e}"

def inline_validate_settings(s):
    """Fallback validation when external validator is unavailable."""
    try:
        if not (-36.0 <= s.lufs <= -8.0): raise ValueError("--lufs must be between -36 and -8")
        if s.tp > -1.0: raise ValueError("--tp must be ≤ -1.0 dBTP")
        if s.lra < 0: raise ValueError("--lra must be ≥ 0")
        if s.bit_depth not in (16,24,32): raise ValueError("--bit-depth must be 16/24/32")
        if s.sr not in (22050,32000,44100,48000,88200,96000): raise ValueError("--sr invalid")
        # Ensure channel count is between 1 and 8 inclusive.  A previous
        # typo surfaced as "1.8" which is confusing; use a double dot to
        # clearly denote the range boundaries.
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
        cmd_list.extend(["-progress","pipe:1","-nostats","-v","error"])
    return cmd_list
# === End Release Helpers =======================================================
# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# type: ignore
"""
MusicForge Pro — All‑in‑One Batch Audio Studio (Single‑File Edition)
====================================================================
This is a production‑ready, *batteries‑included* rewrite of MusicForge aimed at
creators, podcasters, streamers, and studios who need reliable, fast, and
repeatable batch processing of audio assets using FFmpeg/FFprobe — all in a
single Python file that ships cleanly.

Why this version?
- **Two UIs in one**: full desktop GUI (Tkinter) *and* a powerful CLI.
- **Two‑pass loudness normalization** (EBU R128) with one‑pass fallback.
- **Metadata authoring**: Title/Artist/Album/Year/Genre/Comment with templating.
- **Filename templates** (e.g., `{artist} - {title} ({index:02}).{ext}`).
- **Folder Watch**: poll a folder and auto‑ingest new audio files to the queue.
- **Parallel workers**: configurable threading with fair progress.
- **Session restore**: auto‑save and restore last run settings and window state.
- **Presets**: built‑in & user‑defined JSON presets; export/import.
- **Report export**: CSV with full run details + error summary.
- **Zero external dependencies** (optional extras gracefully disabled).
- **Extensive inline docs** & defensive programming for easier maintenance.

Supported Formats
Input: Almost anything FFmpeg can read (wav, mp3, flac, aac, m4a, ogg, aiff, wma, mka, opus, etc.).
Output: `wav`, `mp3`, `flac`, `aac (m4a container)`, `ogg (vorbis)`.

Usage (CLI)
Examples:

  # Convert a folder to WAV @ 48kHz stereo with 24‑bit depth
  music_forge_pro_max.py --input "/path/in" --output "/path/out" \
      --format wav --bit-depth 24 --sr 48000 --ch 2

  # Normalize to -16 LUFS with -1.5 dBTP ceiling using two‑pass loudnorm
  music_forge_pro_max.py -i in -o out -f mp3 --normalize --mode two-pass \
      --lufs -16 --tp -1.5 --lra 11 --quality V2

  # Apply metadata and filename template
  music_forge_pro_max.py -i in -o out -f m4a --meta artist="iD01t" title="{stem}" \
      --template "{artist} - {title}.{ext}"

  # Watch a folder and process new files as they appear (poll every 10s)
  music_forge_pro_max.py --watch "/incoming" --output "/processed" -f flac --normalize --poll 10

Run `music_forge_pro_max.py --help` for the full CLI reference.

GUI
Simply run `python music_forge_pro_max.py` to launch the desktop app.

License: Commercial — © iD01t Productions
Python: 3.9+
"""


import argparse
import csv
import json
import logging
import os
import queue
import shlex
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# Import the improved FFmpeg runner
ffmpeg_runner_available: bool = False
run_ffmpeg: Optional[Callable[..., Tuple[int, str, str]]] = None  # type: ignore
try:
    from ffmpeg_runner_improved import run_ffmpeg
    ffmpeg_runner_available = True
except ImportError:
    pass

# Import settings validator
settings_validator_available: bool = False
validate_settings: Optional[Callable[[ProcessingSettings], None]] = None  # type: ignore
try:
    from settings_validator import validate_settings
    settings_validator_available = True
except ImportError:
    pass

# --- Tkinter (GUI) ---
tk_available: bool = False
tk: Optional[Any] = None
ttk: Optional[Any] = None
filedialog: Optional[Any] = None
messagebox: Optional[Any] = None
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    tk_available = True
except Exception:
    pass

APP_NAME = "Music Forge Pro Max"


def _ensure_tkinter() -> None:
    """Ensure tkinter is available and raise an error if not."""
    if not tk_available or tk is None or ttk is None or filedialog is None or messagebox is None:
        raise RuntimeError("Tkinter is not available")

# Helper functions for tkinter type safety (unused but kept for potential future use)
def _ensure_tk() -> Any:  # type: ignore
    if tk is None:
        raise RuntimeError("tkinter is not available")
    return tk

def _ensure_ttk() -> Any:  # type: ignore
    if ttk is None:
        raise RuntimeError("tkinter.ttk is not available")
    return ttk

def _ensure_filedialog() -> Any:  # type: ignore
    if filedialog is None:
        raise RuntimeError("tkinter.filedialog is not available")
    return filedialog

def _ensure_messagebox() -> Any:  # type: ignore
    if messagebox is None:
        raise RuntimeError("tkinter.messagebox is not available")
    return messagebox


# --- In‑App User Manual (displayable from GUI and CLI) ---
USER_MANUAL = r"""
===============================================================================
MUSICFORGE PRO — OFFICIAL USER MANUAL
===============================================================================

Welcome! This guide walks you through everything you can do with MusicForge Pro.

TABLE OF CONTENTS
1) Quick Start
2) Concepts & Terminology
3) Desktop App Walkthrough
4) Loudness Normalization (EBU R128) — Two‑Pass Explained
5) Metadata & Filename Templating
6) Folder Watch — Hands‑Free Pipelines
7) Presets — Built‑in & User Presets
8) Session Restore & Logs
9) Troubleshooting
10) Power User Tips
11) Changelog Summary

1) QUICK START
Getting Started:
  - Launch the application from your desktop or start menu
  - Add files/folder → choose output folder → tweak settings → Start
  - Export report from the toolbar to CSV

First Time Setup:
  - Ensure FFmpeg is installed on your system
  - Choose your preferred output format and quality settings
  - Set up metadata templates for consistent tagging

2) CONCEPTS & TERMINOLOGY
- Sample Rate (Hz): Audio samples per second. Common: 44100 (CD) / 48000 (video).
- Channels: 1=mono, 2=stereo. Higher values supported if the source has them.
- Bit Depth (WAV): 16/24/32 bit integer PCM target depth for WAV encoding.
- Normalization: Bringing levels to targets. MusicForge uses EBU R128 loudnorm.
- Two‑Pass Loudnorm: Measures first, applies correction second for accuracy.
- True Peak (TP): Peak level approximated by oversampling; recommended ≤ -1.0 dBTP.

3) DESKTOP APP WALKTHROUGH
🎵 Batch Processor Tab
  • File Queue: Shows each file's format, duration, size, status, error, and output path
  • Processing Settings:
      - Format: Choose output format (WAV, MP3, FLAC, AAC, M4A, OGG, Opus)
      - Quality: Format-specific quality settings (V0-V4 for MP3, bitrates for AAC/Opus)
      - WAV Settings: Bit depth (16/24/32), sample rate, channels
      - Loudness Normalization: Two-pass or one-pass with LUFS/TP/LRA targets
      - Effects: Fade in/out duration, parallel worker count
      - Output: Destination folder and filename template
  • Actions: Add Files, Add Folder, Clear Queue, Export Report, Start/Stop Processing

🏷️ Metadata Tab
  • Tag Templates: Enter templates for Artist, Title, Album, Year, Genre, Comment
  • Placeholders: Use {stem}, {ext}, {index}, {artist}, {title} in templates
  • Auto-fill: Templates automatically populate from filename and metadata

⚙️ Presets Tab
  • Built-in Presets: Load common configurations (Podcast, Music, Archive)
  • User Presets: Save your custom settings for reuse
  • Import/Export: Share presets between installations

👁️ Folder Watch Tab
  • Auto-Ingest: Watch a folder and automatically process new audio files
  • Polling: Set interval for checking new files (1-3600 seconds)
  • Real-time: Perfect for automated workflows and batch processing

🔧 Diagnostics Tab
  • FFmpeg Info: View FFmpeg and FFprobe versions and installation paths
  • System Check: Verify all components are working correctly
  • Troubleshooting: Get detailed information for support

📋 Log Tab
  • Live Log: Real-time view of processing events and errors
  • Detailed Info: Complete processing history and diagnostics
  • Export: Save logs for troubleshooting or record keeping

4) LOUDNESS NORMALIZATION — TWO‑PASS
Two‑pass loudnorm performs a measurement pass to obtain input_I/input_TP/input_LRA/
input_thresh/target_offset and then feeds those into a second pass for precise
conformance. If accuracy is less critical, use one‑pass.

Recommendations:
  • Music/Streaming: I=-16 LUFS, TP=-1.5 dBTP, LRA=11 LU (typical)
  • Podcasts/Voice: I=-16 LUFS, TP=-2.0 dBTP, LRA=7..11 LU (content‑dependent)

5) METADATA & FILENAME TEMPLATING
Placeholders available in both metadata template values and filename templates:
  {stem} = filename without extension
  {ext}  = output extension
  {index}= index in batch (CLI) or 1 (GUI)
  {artist},{title} = metadata template fields (can themselves use placeholders)

6) FOLDER WATCH
Folder Watch polls for new files and enqueues them into the batch queue. Great
for automated ‘hot folder’ workflows or ingest pipelines.

7) PRESETS
Built‑in presets cover common workflows. Save your exact setup as a user preset
(JSON) for easy reuse across projects.

8) SESSION RESTORE & LOGS
Your last used settings and window geometry are saved to ~/.musicforge_pro_session.json.
Logs are written to ~/.musicforge_pro.log

9) TROUBLESHOOTING
• “FFmpeg Missing” — Install FFmpeg & FFprobe and ensure they are on PATH.
• “File exists, skipping” — Disable overwrite or change output folder/template.
• “Would overwrite source” — Output template must not resolve to source path.
• Silence/level issues — Try two‑pass normalize for accuracy.

10) POWER USER TIPS
• Use --preset with CLI or load from the Presets tab in GUI.
• Templates can include fixed prefixes/suffixes and placeholders together.
• Increase parallel workers to saturate CPU for short files; for long files
  balance between thermal limits and speed.

11) CHANGELOG SUMMARY
v1.0.0 — First public Pro release: Modern GUI, two‑pass normalization, metadata 
templating, presets, folder watch, session restore, enhanced CSV exports, 
improved logging, and comprehensive input validation.

End of manual.
===============================================================================
"""
# Minimal localization dictionary (future expansion)
LOCALE = {
  "en": {
    "add_files": "Add Files…",
    "add_folder": "Add Folder…",
    "start": "Start",
    "stop": "Stop",
    "clear": "Clear",
    "export_report": "Export Report…",
    "user_manual": "User Manual",
    "show_manual": "Show Manual"
  },
  "fr": {
    "add_files": "Ajouter des fichiers…",
    "add_folder": "Ajouter un dossier…",
    "start": "Démarrer",
    "stop": "Arrêter",
    "clear": "Vider",
    "export_report": "Exporter le rapport…",
    "user_manual": "Manuel d’utilisateur",
    "show_manual": "Afficher le manuel"
  }
}

# Large reference blocks for offline help
POWER_GUIDE = """
(See Help ▸ Power Guide in the GUI or --power-guide in CLI)
This guide includes advanced encoding notes and extended tips.
"""

COOKBOOK = """
FFmpeg Cookbook — 1200 Example Lines
0001: ffmpeg -i in1.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1.wav\n0002: ffmpeg -i in2.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out2.wav\n0003: ffmpeg -i in3.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out3.wav\n0004: ffmpeg -i in4.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out4.wav\n0005: ffmpeg -i in5.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out5.wav\n0006: ffmpeg -i in6.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out6.wav\n0007: ffmpeg -i in7.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out7.wav\n0008: ffmpeg -i in8.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out8.wav\n0009: ffmpeg -i in9.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out9.wav\n0010: ffmpeg -i in10.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out10.wav\n0011: ffmpeg -i in11.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out11.wav\n0012: ffmpeg -i in12.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out12.wav\n0013: ffmpeg -i in13.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out13.wav\n0014: ffmpeg -i in14.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out14.wav\n0015: ffmpeg -i in15.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out15.wav\n0016: ffmpeg -i in16.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out16.wav\n0017: ffmpeg -i in17.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out17.wav\n0018: ffmpeg -i in18.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out18.wav\n0019: ffmpeg -i in19.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out19.wav\n0020: ffmpeg -i in20.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out20.wav\n0021: ffmpeg -i in21.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out21.wav\n0022: ffmpeg -i in22.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out22.wav\n0023: ffmpeg -i in23.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out23.wav\n0024: ffmpeg -i in24.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out24.wav\n0025: ffmpeg -i in25.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out25.wav\n0026: ffmpeg -i in26.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out26.wav\n0027: ffmpeg -i in27.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out27.wav\n0028: ffmpeg -i in28.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out28.wav\n0029: ffmpeg -i in29.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out29.wav\n0030: ffmpeg -i in30.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out30.wav\n0031: ffmpeg -i in31.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out31.wav\n0032: ffmpeg -i in32.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out32.wav\n0033: ffmpeg -i in33.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out33.wav\n0034: ffmpeg -i in34.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out34.wav\n0035: ffmpeg -i in35.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out35.wav\n0036: ffmpeg -i in36.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out36.wav\n0037: ffmpeg -i in37.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out37.wav\n0038: ffmpeg -i in38.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out38.wav\n0039: ffmpeg -i in39.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out39.wav\n0040: ffmpeg -i in40.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out40.wav\n0041: ffmpeg -i in41.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out41.wav\n0042: ffmpeg -i in42.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out42.wav\n0043: ffmpeg -i in43.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out43.wav\n0044: ffmpeg -i in44.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out44.wav\n0045: ffmpeg -i in45.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out45.wav\n0046: ffmpeg -i in46.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out46.wav\n0047: ffmpeg -i in47.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out47.wav\n0048: ffmpeg -i in48.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out48.wav\n0049: ffmpeg -i in49.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out49.wav\n0050: ffmpeg -i in50.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out50.wav\n0051: ffmpeg -i in51.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out51.wav\n0052: ffmpeg -i in52.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out52.wav\n0053: ffmpeg -i in53.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out53.wav\n0054: ffmpeg -i in54.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out54.wav\n0055: ffmpeg -i in55.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out55.wav\n0056: ffmpeg -i in56.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out56.wav\n0057: ffmpeg -i in57.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out57.wav\n0058: ffmpeg -i in58.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out58.wav\n0059: ffmpeg -i in59.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out59.wav\n0060: ffmpeg -i in60.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out60.wav\n0061: ffmpeg -i in61.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out61.wav\n0062: ffmpeg -i in62.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out62.wav\n0063: ffmpeg -i in63.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out63.wav\n0064: ffmpeg -i in64.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out64.wav\n0065: ffmpeg -i in65.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out65.wav\n0066: ffmpeg -i in66.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out66.wav\n0067: ffmpeg -i in67.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out67.wav\n0068: ffmpeg -i in68.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out68.wav\n0069: ffmpeg -i in69.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out69.wav\n0070: ffmpeg -i in70.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out70.wav\n0071: ffmpeg -i in71.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out71.wav\n0072: ffmpeg -i in72.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out72.wav\n0073: ffmpeg -i in73.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out73.wav\n0074: ffmpeg -i in74.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out74.wav\n0075: ffmpeg -i in75.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out75.wav\n0076: ffmpeg -i in76.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out76.wav\n0077: ffmpeg -i in77.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out77.wav\n0078: ffmpeg -i in78.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out78.wav\n0079: ffmpeg -i in79.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out79.wav\n0080: ffmpeg -i in80.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out80.wav\n0081: ffmpeg -i in81.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out81.wav\n0082: ffmpeg -i in82.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out82.wav\n0083: ffmpeg -i in83.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out83.wav\n0084: ffmpeg -i in84.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out84.wav\n0085: ffmpeg -i in85.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out85.wav\n0086: ffmpeg -i in86.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out86.wav\n0087: ffmpeg -i in87.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out87.wav\n0088: ffmpeg -i in88.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out88.wav\n0089: ffmpeg -i in89.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out89.wav\n0090: ffmpeg -i in90.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out90.wav\n0091: ffmpeg -i in91.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out91.wav\n0092: ffmpeg -i in92.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out92.wav\n0093: ffmpeg -i in93.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out93.wav\n0094: ffmpeg -i in94.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out94.wav\n0095: ffmpeg -i in95.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out95.wav\n0096: ffmpeg -i in96.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out96.wav\n0097: ffmpeg -i in97.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out97.wav\n0098: ffmpeg -i in98.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out98.wav\n0099: ffmpeg -i in99.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out99.wav\n0100: ffmpeg -i in100.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out100.wav\n0101: ffmpeg -i in101.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out101.wav\n0102: ffmpeg -i in102.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out102.wav\n0103: ffmpeg -i in103.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out103.wav\n0104: ffmpeg -i in104.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out104.wav\n0105: ffmpeg -i in105.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out105.wav\n0106: ffmpeg -i in106.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out106.wav\n0107: ffmpeg -i in107.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out107.wav\n0108: ffmpeg -i in108.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out108.wav\n0109: ffmpeg -i in109.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out109.wav\n0110: ffmpeg -i in110.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out110.wav\n0111: ffmpeg -i in111.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out111.wav\n0112: ffmpeg -i in112.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out112.wav\n0113: ffmpeg -i in113.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out113.wav\n0114: ffmpeg -i in114.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out114.wav\n0115: ffmpeg -i in115.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out115.wav\n0116: ffmpeg -i in116.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out116.wav\n0117: ffmpeg -i in117.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out117.wav\n0118: ffmpeg -i in118.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out118.wav\n0119: ffmpeg -i in119.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out119.wav\n0120: ffmpeg -i in120.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out120.wav\n0121: ffmpeg -i in121.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out121.wav\n0122: ffmpeg -i in122.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out122.wav\n0123: ffmpeg -i in123.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out123.wav\n0124: ffmpeg -i in124.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out124.wav\n0125: ffmpeg -i in125.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out125.wav\n0126: ffmpeg -i in126.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out126.wav\n0127: ffmpeg -i in127.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out127.wav\n0128: ffmpeg -i in128.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out128.wav\n0129: ffmpeg -i in129.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out129.wav\n0130: ffmpeg -i in130.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out130.wav\n0131: ffmpeg -i in131.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out131.wav\n0132: ffmpeg -i in132.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out132.wav\n0133: ffmpeg -i in133.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out133.wav\n0134: ffmpeg -i in134.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out134.wav\n0135: ffmpeg -i in135.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out135.wav\n0136: ffmpeg -i in136.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out136.wav\n0137: ffmpeg -i in137.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out137.wav\n0138: ffmpeg -i in138.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out138.wav\n0139: ffmpeg -i in139.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out139.wav\n0140: ffmpeg -i in140.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out140.wav\n0141: ffmpeg -i in141.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out141.wav\n0142: ffmpeg -i in142.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out142.wav\n0143: ffmpeg -i in143.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out143.wav\n0144: ffmpeg -i in144.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out144.wav\n0145: ffmpeg -i in145.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out145.wav\n0146: ffmpeg -i in146.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out146.wav\n0147: ffmpeg -i in147.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out147.wav\n0148: ffmpeg -i in148.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out148.wav\n0149: ffmpeg -i in149.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out149.wav\n0150: ffmpeg -i in150.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out150.wav\n0151: ffmpeg -i in151.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out151.wav\n0152: ffmpeg -i in152.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out152.wav\n0153: ffmpeg -i in153.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out153.wav\n0154: ffmpeg -i in154.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out154.wav\n0155: ffmpeg -i in155.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out155.wav\n0156: ffmpeg -i in156.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out156.wav\n0157: ffmpeg -i in157.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out157.wav\n0158: ffmpeg -i in158.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out158.wav\n0159: ffmpeg -i in159.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out159.wav\n0160: ffmpeg -i in160.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out160.wav\n0161: ffmpeg -i in161.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out161.wav\n0162: ffmpeg -i in162.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out162.wav\n0163: ffmpeg -i in163.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out163.wav\n0164: ffmpeg -i in164.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out164.wav\n0165: ffmpeg -i in165.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out165.wav\n0166: ffmpeg -i in166.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out166.wav\n0167: ffmpeg -i in167.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out167.wav\n0168: ffmpeg -i in168.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out168.wav\n0169: ffmpeg -i in169.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out169.wav\n0170: ffmpeg -i in170.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out170.wav\n0171: ffmpeg -i in171.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out171.wav\n0172: ffmpeg -i in172.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out172.wav\n0173: ffmpeg -i in173.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out173.wav\n0174: ffmpeg -i in174.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out174.wav\n0175: ffmpeg -i in175.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out175.wav\n0176: ffmpeg -i in176.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out176.wav\n0177: ffmpeg -i in177.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out177.wav\n0178: ffmpeg -i in178.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out178.wav\n0179: ffmpeg -i in179.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out179.wav\n0180: ffmpeg -i in180.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out180.wav\n0181: ffmpeg -i in181.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out181.wav\n0182: ffmpeg -i in182.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out182.wav\n0183: ffmpeg -i in183.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out183.wav\n0184: ffmpeg -i in184.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out184.wav\n0185: ffmpeg -i in185.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out185.wav\n0186: ffmpeg -i in186.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out186.wav\n0187: ffmpeg -i in187.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out187.wav\n0188: ffmpeg -i in188.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out188.wav\n0189: ffmpeg -i in189.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out189.wav\n0190: ffmpeg -i in190.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out190.wav\n0191: ffmpeg -i in191.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out191.wav\n0192: ffmpeg -i in192.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out192.wav\n0193: ffmpeg -i in193.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out193.wav\n0194: ffmpeg -i in194.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out194.wav\n0195: ffmpeg -i in195.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out195.wav\n0196: ffmpeg -i in196.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out196.wav\n0197: ffmpeg -i in197.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out197.wav\n0198: ffmpeg -i in198.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out198.wav\n0199: ffmpeg -i in199.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out199.wav\n0200: ffmpeg -i in200.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out200.wav\n0201: ffmpeg -i in201.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out201.wav\n0202: ffmpeg -i in202.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out202.wav\n0203: ffmpeg -i in203.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out203.wav\n0204: ffmpeg -i in204.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out204.wav\n0205: ffmpeg -i in205.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out205.wav\n0206: ffmpeg -i in206.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out206.wav\n0207: ffmpeg -i in207.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out207.wav\n0208: ffmpeg -i in208.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out208.wav\n0209: ffmpeg -i in209.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out209.wav\n0210: ffmpeg -i in210.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out210.wav\n0211: ffmpeg -i in211.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out211.wav\n0212: ffmpeg -i in212.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out212.wav\n0213: ffmpeg -i in213.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out213.wav\n0214: ffmpeg -i in214.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out214.wav\n0215: ffmpeg -i in215.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out215.wav\n0216: ffmpeg -i in216.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out216.wav\n0217: ffmpeg -i in217.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out217.wav\n0218: ffmpeg -i in218.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out218.wav\n0219: ffmpeg -i in219.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out219.wav\n0220: ffmpeg -i in220.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out220.wav\n0221: ffmpeg -i in221.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out221.wav\n0222: ffmpeg -i in222.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out222.wav\n0223: ffmpeg -i in223.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out223.wav\n0224: ffmpeg -i in224.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out224.wav\n0225: ffmpeg -i in225.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out225.wav\n0226: ffmpeg -i in226.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out226.wav\n0227: ffmpeg -i in227.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out227.wav\n0228: ffmpeg -i in228.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out228.wav\n0229: ffmpeg -i in229.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out229.wav\n0230: ffmpeg -i in230.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out230.wav\n0231: ffmpeg -i in231.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out231.wav\n0232: ffmpeg -i in232.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out232.wav\n0233: ffmpeg -i in233.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out233.wav\n0234: ffmpeg -i in234.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out234.wav\n0235: ffmpeg -i in235.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out235.wav\n0236: ffmpeg -i in236.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out236.wav\n0237: ffmpeg -i in237.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out237.wav\n0238: ffmpeg -i in238.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out238.wav\n0239: ffmpeg -i in239.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out239.wav\n0240: ffmpeg -i in240.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out240.wav\n0241: ffmpeg -i in241.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out241.wav\n0242: ffmpeg -i in242.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out242.wav\n0243: ffmpeg -i in243.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out243.wav\n0244: ffmpeg -i in244.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out244.wav\n0245: ffmpeg -i in245.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out245.wav\n0246: ffmpeg -i in246.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out246.wav\n0247: ffmpeg -i in247.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out247.wav\n0248: ffmpeg -i in248.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out248.wav\n0249: ffmpeg -i in249.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out249.wav\n0250: ffmpeg -i in250.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out250.wav\n0251: ffmpeg -i in251.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out251.wav\n0252: ffmpeg -i in252.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out252.wav\n0253: ffmpeg -i in253.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out253.wav\n0254: ffmpeg -i in254.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out254.wav\n0255: ffmpeg -i in255.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out255.wav\n0256: ffmpeg -i in256.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out256.wav\n0257: ffmpeg -i in257.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out257.wav\n0258: ffmpeg -i in258.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out258.wav\n0259: ffmpeg -i in259.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out259.wav\n0260: ffmpeg -i in260.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out260.wav\n0261: ffmpeg -i in261.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out261.wav\n0262: ffmpeg -i in262.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out262.wav\n0263: ffmpeg -i in263.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out263.wav\n0264: ffmpeg -i in264.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out264.wav\n0265: ffmpeg -i in265.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out265.wav\n0266: ffmpeg -i in266.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out266.wav\n0267: ffmpeg -i in267.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out267.wav\n0268: ffmpeg -i in268.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out268.wav\n0269: ffmpeg -i in269.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out269.wav\n0270: ffmpeg -i in270.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out270.wav\n0271: ffmpeg -i in271.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out271.wav\n0272: ffmpeg -i in272.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out272.wav\n0273: ffmpeg -i in273.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out273.wav\n0274: ffmpeg -i in274.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out274.wav\n0275: ffmpeg -i in275.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out275.wav\n0276: ffmpeg -i in276.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out276.wav\n0277: ffmpeg -i in277.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out277.wav\n0278: ffmpeg -i in278.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out278.wav\n0279: ffmpeg -i in279.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out279.wav\n0280: ffmpeg -i in280.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out280.wav\n0281: ffmpeg -i in281.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out281.wav\n0282: ffmpeg -i in282.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out282.wav\n0283: ffmpeg -i in283.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out283.wav\n0284: ffmpeg -i in284.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out284.wav\n0285: ffmpeg -i in285.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out285.wav\n0286: ffmpeg -i in286.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out286.wav\n0287: ffmpeg -i in287.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out287.wav\n0288: ffmpeg -i in288.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out288.wav\n0289: ffmpeg -i in289.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out289.wav\n0290: ffmpeg -i in290.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out290.wav\n0291: ffmpeg -i in291.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out291.wav\n0292: ffmpeg -i in292.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out292.wav\n0293: ffmpeg -i in293.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out293.wav\n0294: ffmpeg -i in294.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out294.wav\n0295: ffmpeg -i in295.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out295.wav\n0296: ffmpeg -i in296.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out296.wav\n0297: ffmpeg -i in297.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out297.wav\n0298: ffmpeg -i in298.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out298.wav\n0299: ffmpeg -i in299.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out299.wav\n0300: ffmpeg -i in300.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out300.wav\n0301: ffmpeg -i in301.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out301.wav\n0302: ffmpeg -i in302.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out302.wav\n0303: ffmpeg -i in303.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out303.wav\n0304: ffmpeg -i in304.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out304.wav\n0305: ffmpeg -i in305.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out305.wav\n0306: ffmpeg -i in306.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out306.wav\n0307: ffmpeg -i in307.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out307.wav\n0308: ffmpeg -i in308.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out308.wav\n0309: ffmpeg -i in309.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out309.wav\n0310: ffmpeg -i in310.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out310.wav\n0311: ffmpeg -i in311.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out311.wav\n0312: ffmpeg -i in312.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out312.wav\n0313: ffmpeg -i in313.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out313.wav\n0314: ffmpeg -i in314.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out314.wav\n0315: ffmpeg -i in315.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out315.wav\n0316: ffmpeg -i in316.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out316.wav\n0317: ffmpeg -i in317.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out317.wav\n0318: ffmpeg -i in318.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out318.wav\n0319: ffmpeg -i in319.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out319.wav\n0320: ffmpeg -i in320.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out320.wav\n0321: ffmpeg -i in321.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out321.wav\n0322: ffmpeg -i in322.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out322.wav\n0323: ffmpeg -i in323.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out323.wav\n0324: ffmpeg -i in324.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out324.wav\n0325: ffmpeg -i in325.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out325.wav\n0326: ffmpeg -i in326.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out326.wav\n0327: ffmpeg -i in327.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out327.wav\n0328: ffmpeg -i in328.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out328.wav\n0329: ffmpeg -i in329.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out329.wav\n0330: ffmpeg -i in330.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out330.wav\n0331: ffmpeg -i in331.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out331.wav\n0332: ffmpeg -i in332.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out332.wav\n0333: ffmpeg -i in333.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out333.wav\n0334: ffmpeg -i in334.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out334.wav\n0335: ffmpeg -i in335.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out335.wav\n0336: ffmpeg -i in336.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out336.wav\n0337: ffmpeg -i in337.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out337.wav\n0338: ffmpeg -i in338.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out338.wav\n0339: ffmpeg -i in339.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out339.wav\n0340: ffmpeg -i in340.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out340.wav\n0341: ffmpeg -i in341.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out341.wav\n0342: ffmpeg -i in342.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out342.wav\n0343: ffmpeg -i in343.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out343.wav\n0344: ffmpeg -i in344.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out344.wav\n0345: ffmpeg -i in345.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out345.wav\n0346: ffmpeg -i in346.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out346.wav\n0347: ffmpeg -i in347.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out347.wav\n0348: ffmpeg -i in348.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out348.wav\n0349: ffmpeg -i in349.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out349.wav\n0350: ffmpeg -i in350.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out350.wav\n0351: ffmpeg -i in351.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out351.wav\n0352: ffmpeg -i in352.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out352.wav\n0353: ffmpeg -i in353.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out353.wav\n0354: ffmpeg -i in354.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out354.wav\n0355: ffmpeg -i in355.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out355.wav\n0356: ffmpeg -i in356.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out356.wav\n0357: ffmpeg -i in357.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out357.wav\n0358: ffmpeg -i in358.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out358.wav\n0359: ffmpeg -i in359.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out359.wav\n0360: ffmpeg -i in360.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out360.wav\n0361: ffmpeg -i in361.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out361.wav\n0362: ffmpeg -i in362.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out362.wav\n0363: ffmpeg -i in363.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out363.wav\n0364: ffmpeg -i in364.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out364.wav\n0365: ffmpeg -i in365.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out365.wav\n0366: ffmpeg -i in366.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out366.wav\n0367: ffmpeg -i in367.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out367.wav\n0368: ffmpeg -i in368.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out368.wav\n0369: ffmpeg -i in369.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out369.wav\n0370: ffmpeg -i in370.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out370.wav\n0371: ffmpeg -i in371.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out371.wav\n0372: ffmpeg -i in372.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out372.wav\n0373: ffmpeg -i in373.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out373.wav\n0374: ffmpeg -i in374.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out374.wav\n0375: ffmpeg -i in375.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out375.wav\n0376: ffmpeg -i in376.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out376.wav\n0377: ffmpeg -i in377.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out377.wav\n0378: ffmpeg -i in378.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out378.wav\n0379: ffmpeg -i in379.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out379.wav\n0380: ffmpeg -i in380.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out380.wav\n0381: ffmpeg -i in381.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out381.wav\n0382: ffmpeg -i in382.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out382.wav\n0383: ffmpeg -i in383.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out383.wav\n0384: ffmpeg -i in384.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out384.wav\n0385: ffmpeg -i in385.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out385.wav\n0386: ffmpeg -i in386.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out386.wav\n0387: ffmpeg -i in387.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out387.wav\n0388: ffmpeg -i in388.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out388.wav\n0389: ffmpeg -i in389.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out389.wav\n0390: ffmpeg -i in390.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out390.wav\n0391: ffmpeg -i in391.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out391.wav\n0392: ffmpeg -i in392.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out392.wav\n0393: ffmpeg -i in393.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out393.wav\n0394: ffmpeg -i in394.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out394.wav\n0395: ffmpeg -i in395.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out395.wav\n0396: ffmpeg -i in396.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out396.wav\n0397: ffmpeg -i in397.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out397.wav\n0398: ffmpeg -i in398.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out398.wav\n0399: ffmpeg -i in399.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out399.wav\n0400: ffmpeg -i in400.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out400.wav\n0401: ffmpeg -i in401.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out401.wav\n0402: ffmpeg -i in402.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out402.wav\n0403: ffmpeg -i in403.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out403.wav\n0404: ffmpeg -i in404.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out404.wav\n0405: ffmpeg -i in405.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out405.wav\n0406: ffmpeg -i in406.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out406.wav\n0407: ffmpeg -i in407.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out407.wav\n0408: ffmpeg -i in408.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out408.wav\n0409: ffmpeg -i in409.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out409.wav\n0410: ffmpeg -i in410.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out410.wav\n0411: ffmpeg -i in411.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out411.wav\n0412: ffmpeg -i in412.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out412.wav\n0413: ffmpeg -i in413.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out413.wav\n0414: ffmpeg -i in414.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out414.wav\n0415: ffmpeg -i in415.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out415.wav\n0416: ffmpeg -i in416.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out416.wav\n0417: ffmpeg -i in417.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out417.wav\n0418: ffmpeg -i in418.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out418.wav\n0419: ffmpeg -i in419.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out419.wav\n0420: ffmpeg -i in420.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out420.wav\n0421: ffmpeg -i in421.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out421.wav\n0422: ffmpeg -i in422.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out422.wav\n0423: ffmpeg -i in423.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out423.wav\n0424: ffmpeg -i in424.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out424.wav\n0425: ffmpeg -i in425.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out425.wav\n0426: ffmpeg -i in426.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out426.wav\n0427: ffmpeg -i in427.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out427.wav\n0428: ffmpeg -i in428.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out428.wav\n0429: ffmpeg -i in429.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out429.wav\n0430: ffmpeg -i in430.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out430.wav\n0431: ffmpeg -i in431.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out431.wav\n0432: ffmpeg -i in432.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out432.wav\n0433: ffmpeg -i in433.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out433.wav\n0434: ffmpeg -i in434.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out434.wav\n0435: ffmpeg -i in435.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out435.wav\n0436: ffmpeg -i in436.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out436.wav\n0437: ffmpeg -i in437.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out437.wav\n0438: ffmpeg -i in438.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out438.wav\n0439: ffmpeg -i in439.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out439.wav\n0440: ffmpeg -i in440.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out440.wav\n0441: ffmpeg -i in441.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out441.wav\n0442: ffmpeg -i in442.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out442.wav\n0443: ffmpeg -i in443.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out443.wav\n0444: ffmpeg -i in444.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out444.wav\n0445: ffmpeg -i in445.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out445.wav\n0446: ffmpeg -i in446.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out446.wav\n0447: ffmpeg -i in447.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out447.wav\n0448: ffmpeg -i in448.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out448.wav\n0449: ffmpeg -i in449.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out449.wav\n0450: ffmpeg -i in450.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out450.wav\n0451: ffmpeg -i in451.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out451.wav\n0452: ffmpeg -i in452.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out452.wav\n0453: ffmpeg -i in453.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out453.wav\n0454: ffmpeg -i in454.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out454.wav\n0455: ffmpeg -i in455.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out455.wav\n0456: ffmpeg -i in456.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out456.wav\n0457: ffmpeg -i in457.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out457.wav\n0458: ffmpeg -i in458.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out458.wav\n0459: ffmpeg -i in459.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out459.wav\n0460: ffmpeg -i in460.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out460.wav\n0461: ffmpeg -i in461.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out461.wav\n0462: ffmpeg -i in462.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out462.wav\n0463: ffmpeg -i in463.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out463.wav\n0464: ffmpeg -i in464.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out464.wav\n0465: ffmpeg -i in465.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out465.wav\n0466: ffmpeg -i in466.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out466.wav\n0467: ffmpeg -i in467.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out467.wav\n0468: ffmpeg -i in468.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out468.wav\n0469: ffmpeg -i in469.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out469.wav\n0470: ffmpeg -i in470.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out470.wav\n0471: ffmpeg -i in471.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out471.wav\n0472: ffmpeg -i in472.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out472.wav\n0473: ffmpeg -i in473.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out473.wav\n0474: ffmpeg -i in474.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out474.wav\n0475: ffmpeg -i in475.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out475.wav\n0476: ffmpeg -i in476.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out476.wav\n0477: ffmpeg -i in477.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out477.wav\n0478: ffmpeg -i in478.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out478.wav\n0479: ffmpeg -i in479.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out479.wav\n0480: ffmpeg -i in480.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out480.wav\n0481: ffmpeg -i in481.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out481.wav\n0482: ffmpeg -i in482.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out482.wav\n0483: ffmpeg -i in483.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out483.wav\n0484: ffmpeg -i in484.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out484.wav\n0485: ffmpeg -i in485.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out485.wav\n0486: ffmpeg -i in486.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out486.wav\n0487: ffmpeg -i in487.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out487.wav\n0488: ffmpeg -i in488.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out488.wav\n0489: ffmpeg -i in489.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out489.wav\n0490: ffmpeg -i in490.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out490.wav\n0491: ffmpeg -i in491.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out491.wav\n0492: ffmpeg -i in492.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out492.wav\n0493: ffmpeg -i in493.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out493.wav\n0494: ffmpeg -i in494.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out494.wav\n0495: ffmpeg -i in495.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out495.wav\n0496: ffmpeg -i in496.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out496.wav\n0497: ffmpeg -i in497.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out497.wav\n0498: ffmpeg -i in498.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out498.wav\n0499: ffmpeg -i in499.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out499.wav\n0500: ffmpeg -i in500.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out500.wav\n0501: ffmpeg -i in501.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out501.wav\n0502: ffmpeg -i in502.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out502.wav\n0503: ffmpeg -i in503.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out503.wav\n0504: ffmpeg -i in504.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out504.wav\n0505: ffmpeg -i in505.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out505.wav\n0506: ffmpeg -i in506.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out506.wav\n0507: ffmpeg -i in507.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out507.wav\n0508: ffmpeg -i in508.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out508.wav\n0509: ffmpeg -i in509.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out509.wav\n0510: ffmpeg -i in510.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out510.wav\n0511: ffmpeg -i in511.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out511.wav\n0512: ffmpeg -i in512.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out512.wav\n0513: ffmpeg -i in513.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out513.wav\n0514: ffmpeg -i in514.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out514.wav\n0515: ffmpeg -i in515.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out515.wav\n0516: ffmpeg -i in516.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out516.wav\n0517: ffmpeg -i in517.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out517.wav\n0518: ffmpeg -i in518.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out518.wav\n0519: ffmpeg -i in519.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out519.wav\n0520: ffmpeg -i in520.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out520.wav\n0521: ffmpeg -i in521.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out521.wav\n0522: ffmpeg -i in522.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out522.wav\n0523: ffmpeg -i in523.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out523.wav\n0524: ffmpeg -i in524.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out524.wav\n0525: ffmpeg -i in525.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out525.wav\n0526: ffmpeg -i in526.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out526.wav\n0527: ffmpeg -i in527.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out527.wav\n0528: ffmpeg -i in528.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out528.wav\n0529: ffmpeg -i in529.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out529.wav\n0530: ffmpeg -i in530.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out530.wav\n0531: ffmpeg -i in531.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out531.wav\n0532: ffmpeg -i in532.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out532.wav\n0533: ffmpeg -i in533.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out533.wav\n0534: ffmpeg -i in534.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out534.wav\n0535: ffmpeg -i in535.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out535.wav\n0536: ffmpeg -i in536.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out536.wav\n0537: ffmpeg -i in537.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out537.wav\n0538: ffmpeg -i in538.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out538.wav\n0539: ffmpeg -i in539.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out539.wav\n0540: ffmpeg -i in540.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out540.wav\n0541: ffmpeg -i in541.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out541.wav\n0542: ffmpeg -i in542.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out542.wav\n0543: ffmpeg -i in543.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out543.wav\n0544: ffmpeg -i in544.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out544.wav\n0545: ffmpeg -i in545.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out545.wav\n0546: ffmpeg -i in546.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out546.wav\n0547: ffmpeg -i in547.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out547.wav\n0548: ffmpeg -i in548.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out548.wav\n0549: ffmpeg -i in549.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out549.wav\n0550: ffmpeg -i in550.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out550.wav\n0551: ffmpeg -i in551.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out551.wav\n0552: ffmpeg -i in552.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out552.wav\n0553: ffmpeg -i in553.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out553.wav\n0554: ffmpeg -i in554.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out554.wav\n0555: ffmpeg -i in555.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out555.wav\n0556: ffmpeg -i in556.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out556.wav\n0557: ffmpeg -i in557.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out557.wav\n0558: ffmpeg -i in558.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out558.wav\n0559: ffmpeg -i in559.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out559.wav\n0560: ffmpeg -i in560.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out560.wav\n0561: ffmpeg -i in561.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out561.wav\n0562: ffmpeg -i in562.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out562.wav\n0563: ffmpeg -i in563.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out563.wav\n0564: ffmpeg -i in564.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out564.wav\n0565: ffmpeg -i in565.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out565.wav\n0566: ffmpeg -i in566.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out566.wav\n0567: ffmpeg -i in567.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out567.wav\n0568: ffmpeg -i in568.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out568.wav\n0569: ffmpeg -i in569.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out569.wav\n0570: ffmpeg -i in570.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out570.wav\n0571: ffmpeg -i in571.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out571.wav\n0572: ffmpeg -i in572.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out572.wav\n0573: ffmpeg -i in573.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out573.wav\n0574: ffmpeg -i in574.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out574.wav\n0575: ffmpeg -i in575.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out575.wav\n0576: ffmpeg -i in576.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out576.wav\n0577: ffmpeg -i in577.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out577.wav\n0578: ffmpeg -i in578.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out578.wav\n0579: ffmpeg -i in579.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out579.wav\n0580: ffmpeg -i in580.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out580.wav\n0581: ffmpeg -i in581.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out581.wav\n0582: ffmpeg -i in582.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out582.wav\n0583: ffmpeg -i in583.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out583.wav\n0584: ffmpeg -i in584.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out584.wav\n0585: ffmpeg -i in585.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out585.wav\n0586: ffmpeg -i in586.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out586.wav\n0587: ffmpeg -i in587.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out587.wav\n0588: ffmpeg -i in588.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out588.wav\n0589: ffmpeg -i in589.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out589.wav\n0590: ffmpeg -i in590.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out590.wav\n0591: ffmpeg -i in591.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out591.wav\n0592: ffmpeg -i in592.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out592.wav\n0593: ffmpeg -i in593.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out593.wav\n0594: ffmpeg -i in594.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out594.wav\n0595: ffmpeg -i in595.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out595.wav\n0596: ffmpeg -i in596.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out596.wav\n0597: ffmpeg -i in597.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out597.wav\n0598: ffmpeg -i in598.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out598.wav\n0599: ffmpeg -i in599.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out599.wav\n0600: ffmpeg -i in600.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out600.wav\n0601: ffmpeg -i in601.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out601.wav\n0602: ffmpeg -i in602.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out602.wav\n0603: ffmpeg -i in603.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out603.wav\n0604: ffmpeg -i in604.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out604.wav\n0605: ffmpeg -i in605.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out605.wav\n0606: ffmpeg -i in606.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out606.wav\n0607: ffmpeg -i in607.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out607.wav\n0608: ffmpeg -i in608.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out608.wav\n0609: ffmpeg -i in609.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out609.wav\n0610: ffmpeg -i in610.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out610.wav\n0611: ffmpeg -i in611.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out611.wav\n0612: ffmpeg -i in612.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out612.wav\n0613: ffmpeg -i in613.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out613.wav\n0614: ffmpeg -i in614.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out614.wav\n0615: ffmpeg -i in615.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out615.wav\n0616: ffmpeg -i in616.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out616.wav\n0617: ffmpeg -i in617.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out617.wav\n0618: ffmpeg -i in618.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out618.wav\n0619: ffmpeg -i in619.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out619.wav\n0620: ffmpeg -i in620.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out620.wav\n0621: ffmpeg -i in621.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out621.wav\n0622: ffmpeg -i in622.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out622.wav\n0623: ffmpeg -i in623.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out623.wav\n0624: ffmpeg -i in624.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out624.wav\n0625: ffmpeg -i in625.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out625.wav\n0626: ffmpeg -i in626.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out626.wav\n0627: ffmpeg -i in627.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out627.wav\n0628: ffmpeg -i in628.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out628.wav\n0629: ffmpeg -i in629.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out629.wav\n0630: ffmpeg -i in630.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out630.wav\n0631: ffmpeg -i in631.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out631.wav\n0632: ffmpeg -i in632.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out632.wav\n0633: ffmpeg -i in633.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out633.wav\n0634: ffmpeg -i in634.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out634.wav\n0635: ffmpeg -i in635.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out635.wav\n0636: ffmpeg -i in636.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out636.wav\n0637: ffmpeg -i in637.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out637.wav\n0638: ffmpeg -i in638.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out638.wav\n0639: ffmpeg -i in639.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out639.wav\n0640: ffmpeg -i in640.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out640.wav\n0641: ffmpeg -i in641.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out641.wav\n0642: ffmpeg -i in642.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out642.wav\n0643: ffmpeg -i in643.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out643.wav\n0644: ffmpeg -i in644.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out644.wav\n0645: ffmpeg -i in645.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out645.wav\n0646: ffmpeg -i in646.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out646.wav\n0647: ffmpeg -i in647.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out647.wav\n0648: ffmpeg -i in648.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out648.wav\n0649: ffmpeg -i in649.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out649.wav\n0650: ffmpeg -i in650.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out650.wav\n0651: ffmpeg -i in651.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out651.wav\n0652: ffmpeg -i in652.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out652.wav\n0653: ffmpeg -i in653.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out653.wav\n0654: ffmpeg -i in654.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out654.wav\n0655: ffmpeg -i in655.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out655.wav\n0656: ffmpeg -i in656.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out656.wav\n0657: ffmpeg -i in657.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out657.wav\n0658: ffmpeg -i in658.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out658.wav\n0659: ffmpeg -i in659.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out659.wav\n0660: ffmpeg -i in660.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out660.wav\n0661: ffmpeg -i in661.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out661.wav\n0662: ffmpeg -i in662.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out662.wav\n0663: ffmpeg -i in663.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out663.wav\n0664: ffmpeg -i in664.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out664.wav\n0665: ffmpeg -i in665.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out665.wav\n0666: ffmpeg -i in666.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out666.wav\n0667: ffmpeg -i in667.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out667.wav\n0668: ffmpeg -i in668.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out668.wav\n0669: ffmpeg -i in669.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out669.wav\n0670: ffmpeg -i in670.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out670.wav\n0671: ffmpeg -i in671.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out671.wav\n0672: ffmpeg -i in672.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out672.wav\n0673: ffmpeg -i in673.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out673.wav\n0674: ffmpeg -i in674.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out674.wav\n0675: ffmpeg -i in675.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out675.wav\n0676: ffmpeg -i in676.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out676.wav\n0677: ffmpeg -i in677.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out677.wav\n0678: ffmpeg -i in678.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out678.wav\n0679: ffmpeg -i in679.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out679.wav\n0680: ffmpeg -i in680.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out680.wav\n0681: ffmpeg -i in681.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out681.wav\n0682: ffmpeg -i in682.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out682.wav\n0683: ffmpeg -i in683.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out683.wav\n0684: ffmpeg -i in684.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out684.wav\n0685: ffmpeg -i in685.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out685.wav\n0686: ffmpeg -i in686.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out686.wav\n0687: ffmpeg -i in687.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out687.wav\n0688: ffmpeg -i in688.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out688.wav\n0689: ffmpeg -i in689.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out689.wav\n0690: ffmpeg -i in690.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out690.wav\n0691: ffmpeg -i in691.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out691.wav\n0692: ffmpeg -i in692.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out692.wav\n0693: ffmpeg -i in693.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out693.wav\n0694: ffmpeg -i in694.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out694.wav\n0695: ffmpeg -i in695.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out695.wav\n0696: ffmpeg -i in696.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out696.wav\n0697: ffmpeg -i in697.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out697.wav\n0698: ffmpeg -i in698.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out698.wav\n0699: ffmpeg -i in699.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out699.wav\n0700: ffmpeg -i in700.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out700.wav\n0701: ffmpeg -i in701.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out701.wav\n0702: ffmpeg -i in702.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out702.wav\n0703: ffmpeg -i in703.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out703.wav\n0704: ffmpeg -i in704.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out704.wav\n0705: ffmpeg -i in705.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out705.wav\n0706: ffmpeg -i in706.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out706.wav\n0707: ffmpeg -i in707.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out707.wav\n0708: ffmpeg -i in708.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out708.wav\n0709: ffmpeg -i in709.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out709.wav\n0710: ffmpeg -i in710.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out710.wav\n0711: ffmpeg -i in711.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out711.wav\n0712: ffmpeg -i in712.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out712.wav\n0713: ffmpeg -i in713.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out713.wav\n0714: ffmpeg -i in714.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out714.wav\n0715: ffmpeg -i in715.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out715.wav\n0716: ffmpeg -i in716.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out716.wav\n0717: ffmpeg -i in717.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out717.wav\n0718: ffmpeg -i in718.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out718.wav\n0719: ffmpeg -i in719.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out719.wav\n0720: ffmpeg -i in720.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out720.wav\n0721: ffmpeg -i in721.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out721.wav\n0722: ffmpeg -i in722.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out722.wav\n0723: ffmpeg -i in723.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out723.wav\n0724: ffmpeg -i in724.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out724.wav\n0725: ffmpeg -i in725.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out725.wav\n0726: ffmpeg -i in726.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out726.wav\n0727: ffmpeg -i in727.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out727.wav\n0728: ffmpeg -i in728.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out728.wav\n0729: ffmpeg -i in729.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out729.wav\n0730: ffmpeg -i in730.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out730.wav\n0731: ffmpeg -i in731.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out731.wav\n0732: ffmpeg -i in732.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out732.wav\n0733: ffmpeg -i in733.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out733.wav\n0734: ffmpeg -i in734.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out734.wav\n0735: ffmpeg -i in735.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out735.wav\n0736: ffmpeg -i in736.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out736.wav\n0737: ffmpeg -i in737.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out737.wav\n0738: ffmpeg -i in738.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out738.wav\n0739: ffmpeg -i in739.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out739.wav\n0740: ffmpeg -i in740.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out740.wav\n0741: ffmpeg -i in741.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out741.wav\n0742: ffmpeg -i in742.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out742.wav\n0743: ffmpeg -i in743.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out743.wav\n0744: ffmpeg -i in744.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out744.wav\n0745: ffmpeg -i in745.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out745.wav\n0746: ffmpeg -i in746.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out746.wav\n0747: ffmpeg -i in747.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out747.wav\n0748: ffmpeg -i in748.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out748.wav\n0749: ffmpeg -i in749.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out749.wav\n0750: ffmpeg -i in750.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out750.wav\n0751: ffmpeg -i in751.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out751.wav\n0752: ffmpeg -i in752.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out752.wav\n0753: ffmpeg -i in753.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out753.wav\n0754: ffmpeg -i in754.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out754.wav\n0755: ffmpeg -i in755.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out755.wav\n0756: ffmpeg -i in756.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out756.wav\n0757: ffmpeg -i in757.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out757.wav\n0758: ffmpeg -i in758.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out758.wav\n0759: ffmpeg -i in759.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out759.wav\n0760: ffmpeg -i in760.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out760.wav\n0761: ffmpeg -i in761.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out761.wav\n0762: ffmpeg -i in762.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out762.wav\n0763: ffmpeg -i in763.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out763.wav\n0764: ffmpeg -i in764.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out764.wav\n0765: ffmpeg -i in765.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out765.wav\n0766: ffmpeg -i in766.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out766.wav\n0767: ffmpeg -i in767.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out767.wav\n0768: ffmpeg -i in768.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out768.wav\n0769: ffmpeg -i in769.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out769.wav\n0770: ffmpeg -i in770.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out770.wav\n0771: ffmpeg -i in771.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out771.wav\n0772: ffmpeg -i in772.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out772.wav\n0773: ffmpeg -i in773.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out773.wav\n0774: ffmpeg -i in774.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out774.wav\n0775: ffmpeg -i in775.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out775.wav\n0776: ffmpeg -i in776.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out776.wav\n0777: ffmpeg -i in777.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out777.wav\n0778: ffmpeg -i in778.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out778.wav\n0779: ffmpeg -i in779.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out779.wav\n0780: ffmpeg -i in780.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out780.wav\n0781: ffmpeg -i in781.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out781.wav\n0782: ffmpeg -i in782.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out782.wav\n0783: ffmpeg -i in783.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out783.wav\n0784: ffmpeg -i in784.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out784.wav\n0785: ffmpeg -i in785.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out785.wav\n0786: ffmpeg -i in786.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out786.wav\n0787: ffmpeg -i in787.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out787.wav\n0788: ffmpeg -i in788.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out788.wav\n0789: ffmpeg -i in789.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out789.wav\n0790: ffmpeg -i in790.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out790.wav\n0791: ffmpeg -i in791.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out791.wav\n0792: ffmpeg -i in792.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out792.wav\n0793: ffmpeg -i in793.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out793.wav\n0794: ffmpeg -i in794.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out794.wav\n0795: ffmpeg -i in795.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out795.wav\n0796: ffmpeg -i in796.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out796.wav\n0797: ffmpeg -i in797.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out797.wav\n0798: ffmpeg -i in798.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out798.wav\n0799: ffmpeg -i in799.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out799.wav\n0800: ffmpeg -i in800.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out800.wav\n0801: ffmpeg -i in801.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out801.wav\n0802: ffmpeg -i in802.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out802.wav\n0803: ffmpeg -i in803.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out803.wav\n0804: ffmpeg -i in804.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out804.wav\n0805: ffmpeg -i in805.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out805.wav\n0806: ffmpeg -i in806.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out806.wav\n0807: ffmpeg -i in807.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out807.wav\n0808: ffmpeg -i in808.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out808.wav\n0809: ffmpeg -i in809.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out809.wav\n0810: ffmpeg -i in810.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out810.wav\n0811: ffmpeg -i in811.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out811.wav\n0812: ffmpeg -i in812.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out812.wav\n0813: ffmpeg -i in813.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out813.wav\n0814: ffmpeg -i in814.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out814.wav\n0815: ffmpeg -i in815.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out815.wav\n0816: ffmpeg -i in816.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out816.wav\n0817: ffmpeg -i in817.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out817.wav\n0818: ffmpeg -i in818.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out818.wav\n0819: ffmpeg -i in819.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out819.wav\n0820: ffmpeg -i in820.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out820.wav\n0821: ffmpeg -i in821.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out821.wav\n0822: ffmpeg -i in822.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out822.wav\n0823: ffmpeg -i in823.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out823.wav\n0824: ffmpeg -i in824.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out824.wav\n0825: ffmpeg -i in825.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out825.wav\n0826: ffmpeg -i in826.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out826.wav\n0827: ffmpeg -i in827.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out827.wav\n0828: ffmpeg -i in828.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out828.wav\n0829: ffmpeg -i in829.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out829.wav\n0830: ffmpeg -i in830.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out830.wav\n0831: ffmpeg -i in831.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out831.wav\n0832: ffmpeg -i in832.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out832.wav\n0833: ffmpeg -i in833.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out833.wav\n0834: ffmpeg -i in834.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out834.wav\n0835: ffmpeg -i in835.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out835.wav\n0836: ffmpeg -i in836.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out836.wav\n0837: ffmpeg -i in837.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out837.wav\n0838: ffmpeg -i in838.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out838.wav\n0839: ffmpeg -i in839.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out839.wav\n0840: ffmpeg -i in840.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out840.wav\n0841: ffmpeg -i in841.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out841.wav\n0842: ffmpeg -i in842.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out842.wav\n0843: ffmpeg -i in843.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out843.wav\n0844: ffmpeg -i in844.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out844.wav\n0845: ffmpeg -i in845.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out845.wav\n0846: ffmpeg -i in846.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out846.wav\n0847: ffmpeg -i in847.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out847.wav\n0848: ffmpeg -i in848.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out848.wav\n0849: ffmpeg -i in849.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out849.wav\n0850: ffmpeg -i in850.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out850.wav\n0851: ffmpeg -i in851.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out851.wav\n0852: ffmpeg -i in852.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out852.wav\n0853: ffmpeg -i in853.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out853.wav\n0854: ffmpeg -i in854.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out854.wav\n0855: ffmpeg -i in855.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out855.wav\n0856: ffmpeg -i in856.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out856.wav\n0857: ffmpeg -i in857.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out857.wav\n0858: ffmpeg -i in858.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out858.wav\n0859: ffmpeg -i in859.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out859.wav\n0860: ffmpeg -i in860.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out860.wav\n0861: ffmpeg -i in861.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out861.wav\n0862: ffmpeg -i in862.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out862.wav\n0863: ffmpeg -i in863.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out863.wav\n0864: ffmpeg -i in864.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out864.wav\n0865: ffmpeg -i in865.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out865.wav\n0866: ffmpeg -i in866.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out866.wav\n0867: ffmpeg -i in867.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out867.wav\n0868: ffmpeg -i in868.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out868.wav\n0869: ffmpeg -i in869.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out869.wav\n0870: ffmpeg -i in870.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out870.wav\n0871: ffmpeg -i in871.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out871.wav\n0872: ffmpeg -i in872.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out872.wav\n0873: ffmpeg -i in873.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out873.wav\n0874: ffmpeg -i in874.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out874.wav\n0875: ffmpeg -i in875.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out875.wav\n0876: ffmpeg -i in876.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out876.wav\n0877: ffmpeg -i in877.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out877.wav\n0878: ffmpeg -i in878.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out878.wav\n0879: ffmpeg -i in879.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out879.wav\n0880: ffmpeg -i in880.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out880.wav\n0881: ffmpeg -i in881.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out881.wav\n0882: ffmpeg -i in882.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out882.wav\n0883: ffmpeg -i in883.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out883.wav\n0884: ffmpeg -i in884.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out884.wav\n0885: ffmpeg -i in885.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out885.wav\n0886: ffmpeg -i in886.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out886.wav\n0887: ffmpeg -i in887.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out887.wav\n0888: ffmpeg -i in888.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out888.wav\n0889: ffmpeg -i in889.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out889.wav\n0890: ffmpeg -i in890.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out890.wav\n0891: ffmpeg -i in891.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out891.wav\n0892: ffmpeg -i in892.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out892.wav\n0893: ffmpeg -i in893.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out893.wav\n0894: ffmpeg -i in894.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out894.wav\n0895: ffmpeg -i in895.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out895.wav\n0896: ffmpeg -i in896.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out896.wav\n0897: ffmpeg -i in897.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out897.wav\n0898: ffmpeg -i in898.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out898.wav\n0899: ffmpeg -i in899.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out899.wav\n0900: ffmpeg -i in900.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out900.wav\n0901: ffmpeg -i in901.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out901.wav\n0902: ffmpeg -i in902.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out902.wav\n0903: ffmpeg -i in903.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out903.wav\n0904: ffmpeg -i in904.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out904.wav\n0905: ffmpeg -i in905.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out905.wav\n0906: ffmpeg -i in906.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out906.wav\n0907: ffmpeg -i in907.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out907.wav\n0908: ffmpeg -i in908.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out908.wav\n0909: ffmpeg -i in909.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out909.wav\n0910: ffmpeg -i in910.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out910.wav\n0911: ffmpeg -i in911.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out911.wav\n0912: ffmpeg -i in912.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out912.wav\n0913: ffmpeg -i in913.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out913.wav\n0914: ffmpeg -i in914.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out914.wav\n0915: ffmpeg -i in915.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out915.wav\n0916: ffmpeg -i in916.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out916.wav\n0917: ffmpeg -i in917.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out917.wav\n0918: ffmpeg -i in918.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out918.wav\n0919: ffmpeg -i in919.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out919.wav\n0920: ffmpeg -i in920.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out920.wav\n0921: ffmpeg -i in921.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out921.wav\n0922: ffmpeg -i in922.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out922.wav\n0923: ffmpeg -i in923.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out923.wav\n0924: ffmpeg -i in924.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out924.wav\n0925: ffmpeg -i in925.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out925.wav\n0926: ffmpeg -i in926.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out926.wav\n0927: ffmpeg -i in927.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out927.wav\n0928: ffmpeg -i in928.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out928.wav\n0929: ffmpeg -i in929.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out929.wav\n0930: ffmpeg -i in930.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out930.wav\n0931: ffmpeg -i in931.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out931.wav\n0932: ffmpeg -i in932.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out932.wav\n0933: ffmpeg -i in933.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out933.wav\n0934: ffmpeg -i in934.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out934.wav\n0935: ffmpeg -i in935.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out935.wav\n0936: ffmpeg -i in936.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out936.wav\n0937: ffmpeg -i in937.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out937.wav\n0938: ffmpeg -i in938.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out938.wav\n0939: ffmpeg -i in939.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out939.wav\n0940: ffmpeg -i in940.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out940.wav\n0941: ffmpeg -i in941.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out941.wav\n0942: ffmpeg -i in942.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out942.wav\n0943: ffmpeg -i in943.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out943.wav\n0944: ffmpeg -i in944.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out944.wav\n0945: ffmpeg -i in945.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out945.wav\n0946: ffmpeg -i in946.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out946.wav\n0947: ffmpeg -i in947.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out947.wav\n0948: ffmpeg -i in948.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out948.wav\n0949: ffmpeg -i in949.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out949.wav\n0950: ffmpeg -i in950.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out950.wav\n0951: ffmpeg -i in951.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out951.wav\n0952: ffmpeg -i in952.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out952.wav\n0953: ffmpeg -i in953.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out953.wav\n0954: ffmpeg -i in954.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out954.wav\n0955: ffmpeg -i in955.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out955.wav\n0956: ffmpeg -i in956.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out956.wav\n0957: ffmpeg -i in957.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out957.wav\n0958: ffmpeg -i in958.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out958.wav\n0959: ffmpeg -i in959.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out959.wav\n0960: ffmpeg -i in960.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out960.wav\n0961: ffmpeg -i in961.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out961.wav\n0962: ffmpeg -i in962.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out962.wav\n0963: ffmpeg -i in963.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out963.wav\n0964: ffmpeg -i in964.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out964.wav\n0965: ffmpeg -i in965.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out965.wav\n0966: ffmpeg -i in966.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out966.wav\n0967: ffmpeg -i in967.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out967.wav\n0968: ffmpeg -i in968.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out968.wav\n0969: ffmpeg -i in969.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out969.wav\n0970: ffmpeg -i in970.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out970.wav\n0971: ffmpeg -i in971.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out971.wav\n0972: ffmpeg -i in972.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out972.wav\n0973: ffmpeg -i in973.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out973.wav\n0974: ffmpeg -i in974.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out974.wav\n0975: ffmpeg -i in975.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out975.wav\n0976: ffmpeg -i in976.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out976.wav\n0977: ffmpeg -i in977.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out977.wav\n0978: ffmpeg -i in978.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out978.wav\n0979: ffmpeg -i in979.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out979.wav\n0980: ffmpeg -i in980.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out980.wav\n0981: ffmpeg -i in981.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out981.wav\n0982: ffmpeg -i in982.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out982.wav\n0983: ffmpeg -i in983.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out983.wav\n0984: ffmpeg -i in984.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out984.wav\n0985: ffmpeg -i in985.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out985.wav\n0986: ffmpeg -i in986.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out986.wav\n0987: ffmpeg -i in987.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out987.wav\n0988: ffmpeg -i in988.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out988.wav\n0989: ffmpeg -i in989.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out989.wav\n0990: ffmpeg -i in990.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out990.wav\n0991: ffmpeg -i in991.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out991.wav\n0992: ffmpeg -i in992.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out992.wav\n0993: ffmpeg -i in993.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out993.wav\n0994: ffmpeg -i in994.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out994.wav\n0995: ffmpeg -i in995.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out995.wav\n0996: ffmpeg -i in996.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out996.wav\n0997: ffmpeg -i in997.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out997.wav\n0998: ffmpeg -i in998.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out998.wav\n0999: ffmpeg -i in999.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out999.wav\n1000: ffmpeg -i in1000.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1000.wav\n1001: ffmpeg -i in1001.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1001.wav\n1002: ffmpeg -i in1002.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1002.wav\n1003: ffmpeg -i in1003.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1003.wav\n1004: ffmpeg -i in1004.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1004.wav\n1005: ffmpeg -i in1005.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1005.wav\n1006: ffmpeg -i in1006.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1006.wav\n1007: ffmpeg -i in1007.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1007.wav\n1008: ffmpeg -i in1008.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1008.wav\n1009: ffmpeg -i in1009.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1009.wav\n1010: ffmpeg -i in1010.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1010.wav\n1011: ffmpeg -i in1011.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1011.wav\n1012: ffmpeg -i in1012.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1012.wav\n1013: ffmpeg -i in1013.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1013.wav\n1014: ffmpeg -i in1014.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1014.wav\n1015: ffmpeg -i in1015.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1015.wav\n1016: ffmpeg -i in1016.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1016.wav\n1017: ffmpeg -i in1017.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1017.wav\n1018: ffmpeg -i in1018.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1018.wav\n1019: ffmpeg -i in1019.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1019.wav\n1020: ffmpeg -i in1020.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1020.wav\n1021: ffmpeg -i in1021.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1021.wav\n1022: ffmpeg -i in1022.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1022.wav\n1023: ffmpeg -i in1023.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1023.wav\n1024: ffmpeg -i in1024.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1024.wav\n1025: ffmpeg -i in1025.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1025.wav\n1026: ffmpeg -i in1026.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1026.wav\n1027: ffmpeg -i in1027.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1027.wav\n1028: ffmpeg -i in1028.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1028.wav\n1029: ffmpeg -i in1029.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1029.wav\n1030: ffmpeg -i in1030.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1030.wav\n1031: ffmpeg -i in1031.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1031.wav\n1032: ffmpeg -i in1032.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1032.wav\n1033: ffmpeg -i in1033.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1033.wav\n1034: ffmpeg -i in1034.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1034.wav\n1035: ffmpeg -i in1035.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1035.wav\n1036: ffmpeg -i in1036.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1036.wav\n1037: ffmpeg -i in1037.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1037.wav\n1038: ffmpeg -i in1038.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1038.wav\n1039: ffmpeg -i in1039.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1039.wav\n1040: ffmpeg -i in1040.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1040.wav\n1041: ffmpeg -i in1041.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1041.wav\n1042: ffmpeg -i in1042.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1042.wav\n1043: ffmpeg -i in1043.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1043.wav\n1044: ffmpeg -i in1044.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1044.wav\n1045: ffmpeg -i in1045.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1045.wav\n1046: ffmpeg -i in1046.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1046.wav\n1047: ffmpeg -i in1047.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1047.wav\n1048: ffmpeg -i in1048.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1048.wav\n1049: ffmpeg -i in1049.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1049.wav\n1050: ffmpeg -i in1050.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1050.wav\n1051: ffmpeg -i in1051.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1051.wav\n1052: ffmpeg -i in1052.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1052.wav\n1053: ffmpeg -i in1053.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1053.wav\n1054: ffmpeg -i in1054.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1054.wav\n1055: ffmpeg -i in1055.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1055.wav\n1056: ffmpeg -i in1056.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1056.wav\n1057: ffmpeg -i in1057.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1057.wav\n1058: ffmpeg -i in1058.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1058.wav\n1059: ffmpeg -i in1059.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1059.wav\n1060: ffmpeg -i in1060.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1060.wav\n1061: ffmpeg -i in1061.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1061.wav\n1062: ffmpeg -i in1062.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1062.wav\n1063: ffmpeg -i in1063.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1063.wav\n1064: ffmpeg -i in1064.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1064.wav\n1065: ffmpeg -i in1065.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1065.wav\n1066: ffmpeg -i in1066.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1066.wav\n1067: ffmpeg -i in1067.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1067.wav\n1068: ffmpeg -i in1068.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1068.wav\n1069: ffmpeg -i in1069.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1069.wav\n1070: ffmpeg -i in1070.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1070.wav\n1071: ffmpeg -i in1071.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1071.wav\n1072: ffmpeg -i in1072.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1072.wav\n1073: ffmpeg -i in1073.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1073.wav\n1074: ffmpeg -i in1074.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1074.wav\n1075: ffmpeg -i in1075.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1075.wav\n1076: ffmpeg -i in1076.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1076.wav\n1077: ffmpeg -i in1077.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1077.wav\n1078: ffmpeg -i in1078.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1078.wav\n1079: ffmpeg -i in1079.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1079.wav\n1080: ffmpeg -i in1080.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1080.wav\n1081: ffmpeg -i in1081.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1081.wav\n1082: ffmpeg -i in1082.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1082.wav\n1083: ffmpeg -i in1083.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1083.wav\n1084: ffmpeg -i in1084.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1084.wav\n1085: ffmpeg -i in1085.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1085.wav\n1086: ffmpeg -i in1086.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1086.wav\n1087: ffmpeg -i in1087.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1087.wav\n1088: ffmpeg -i in1088.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1088.wav\n1089: ffmpeg -i in1089.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1089.wav\n1090: ffmpeg -i in1090.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1090.wav\n1091: ffmpeg -i in1091.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1091.wav\n1092: ffmpeg -i in1092.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1092.wav\n1093: ffmpeg -i in1093.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1093.wav\n1094: ffmpeg -i in1094.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1094.wav\n1095: ffmpeg -i in1095.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1095.wav\n1096: ffmpeg -i in1096.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1096.wav\n1097: ffmpeg -i in1097.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1097.wav\n1098: ffmpeg -i in1098.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1098.wav\n1099: ffmpeg -i in1099.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1099.wav\n1100: ffmpeg -i in1100.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1100.wav\n1101: ffmpeg -i in1101.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1101.wav\n1102: ffmpeg -i in1102.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1102.wav\n1103: ffmpeg -i in1103.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1103.wav\n1104: ffmpeg -i in1104.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1104.wav\n1105: ffmpeg -i in1105.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1105.wav\n1106: ffmpeg -i in1106.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1106.wav\n1107: ffmpeg -i in1107.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1107.wav\n1108: ffmpeg -i in1108.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1108.wav\n1109: ffmpeg -i in1109.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1109.wav\n1110: ffmpeg -i in1110.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1110.wav\n1111: ffmpeg -i in1111.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1111.wav\n1112: ffmpeg -i in1112.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1112.wav\n1113: ffmpeg -i in1113.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1113.wav\n1114: ffmpeg -i in1114.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1114.wav\n1115: ffmpeg -i in1115.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1115.wav\n1116: ffmpeg -i in1116.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1116.wav\n1117: ffmpeg -i in1117.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1117.wav\n1118: ffmpeg -i in1118.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1118.wav\n1119: ffmpeg -i in1119.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1119.wav\n1120: ffmpeg -i in1120.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1120.wav\n1121: ffmpeg -i in1121.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1121.wav\n1122: ffmpeg -i in1122.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1122.wav\n1123: ffmpeg -i in1123.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1123.wav\n1124: ffmpeg -i in1124.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1124.wav\n1125: ffmpeg -i in1125.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1125.wav\n1126: ffmpeg -i in1126.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1126.wav\n1127: ffmpeg -i in1127.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1127.wav\n1128: ffmpeg -i in1128.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1128.wav\n1129: ffmpeg -i in1129.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1129.wav\n1130: ffmpeg -i in1130.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1130.wav\n1131: ffmpeg -i in1131.wav -af "highpass=f=90,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1131.wav\n1132: ffmpeg -i in1132.wav -af "highpass=f=100,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1132.wav\n1133: ffmpeg -i in1133.wav -af "highpass=f=110,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1133.wav\n1134: ffmpeg -i in1134.wav -af "highpass=f=120,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1134.wav\n1135: ffmpeg -i in1135.wav -af "highpass=f=130,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1135.wav\n1136: ffmpeg -i in1136.wav -af "highpass=f=140,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1136.wav\n1137: ffmpeg -i in1137.wav -af "highpass=f=150,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1137.wav\n1138: ffmpeg -i in1138.wav -af "highpass=f=160,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1138.wav\n1139: ffmpeg -i in1139.wav -af "highpass=f=170,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1139.wav\n1140: ffmpeg -i in1140.wav -af "highpass=f=80,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1140.wav\n1141: ffmpeg -i in1141.wav -af "highpass=f=90,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1141.wav\n1142: ffmpeg -i in1142.wav -af "highpass=f=100,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1142.wav\n1143: ffmpeg -i in1143.wav -af "highpass=f=110,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1143.wav\n1144: ffmpeg -i in1144.wav -af "highpass=f=120,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1144.wav\n1145: ffmpeg -i in1145.wav -af "highpass=f=130,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1145.wav\n1146: ffmpeg -i in1146.wav -af "highpass=f=140,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1146.wav\n1147: ffmpeg -i in1147.wav -af "highpass=f=150,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1147.wav\n1148: ffmpeg -i in1148.wav -af "highpass=f=160,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1148.wav\n1149: ffmpeg -i in1149.wav -af "highpass=f=170,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1149.wav\n1150: ffmpeg -i in1150.wav -af "highpass=f=80,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1150.wav\n1151: ffmpeg -i in1151.wav -af "highpass=f=90,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1151.wav\n1152: ffmpeg -i in1152.wav -af "highpass=f=100,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1152.wav\n1153: ffmpeg -i in1153.wav -af "highpass=f=110,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1153.wav\n1154: ffmpeg -i in1154.wav -af "highpass=f=120,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1154.wav\n1155: ffmpeg -i in1155.wav -af "highpass=f=130,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1155.wav\n1156: ffmpeg -i in1156.wav -af "highpass=f=140,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1156.wav\n1157: ffmpeg -i in1157.wav -af "highpass=f=150,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1157.wav\n1158: ffmpeg -i in1158.wav -af "highpass=f=160,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1158.wav\n1159: ffmpeg -i in1159.wav -af "highpass=f=170,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1159.wav\n1160: ffmpeg -i in1160.wav -af "highpass=f=80,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1160.wav\n1161: ffmpeg -i in1161.wav -af "highpass=f=90,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1161.wav\n1162: ffmpeg -i in1162.wav -af "highpass=f=100,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1162.wav\n1163: ffmpeg -i in1163.wav -af "highpass=f=110,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1163.wav\n1164: ffmpeg -i in1164.wav -af "highpass=f=120,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1164.wav\n1165: ffmpeg -i in1165.wav -af "highpass=f=130,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1165.wav\n1166: ffmpeg -i in1166.wav -af "highpass=f=140,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1166.wav\n1167: ffmpeg -i in1167.wav -af "highpass=f=150,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1167.wav\n1168: ffmpeg -i in1168.wav -af "highpass=f=160,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1168.wav\n1169: ffmpeg -i in1169.wav -af "highpass=f=170,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1169.wav\n1170: ffmpeg -i in1170.wav -af "highpass=f=80,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1170.wav\n1171: ffmpeg -i in1171.wav -af "highpass=f=90,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1171.wav\n1172: ffmpeg -i in1172.wav -af "highpass=f=100,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1172.wav\n1173: ffmpeg -i in1173.wav -af "highpass=f=110,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1173.wav\n1174: ffmpeg -i in1174.wav -af "highpass=f=120,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1174.wav\n1175: ffmpeg -i in1175.wav -af "highpass=f=130,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1175.wav\n1176: ffmpeg -i in1176.wav -af "highpass=f=140,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1176.wav\n1177: ffmpeg -i in1177.wav -af "highpass=f=150,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1177.wav\n1178: ffmpeg -i in1178.wav -af "highpass=f=160,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1178.wav\n1179: ffmpeg -i in1179.wav -af "highpass=f=170,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1179.wav\n1180: ffmpeg -i in1180.wav -af "highpass=f=80,lowpass=f=14000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1180.wav\n1181: ffmpeg -i in1181.wav -af "highpass=f=90,lowpass=f=13500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1181.wav\n1182: ffmpeg -i in1182.wav -af "highpass=f=100,lowpass=f=13000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1182.wav\n1183: ffmpeg -i in1183.wav -af "highpass=f=110,lowpass=f=16000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1183.wav\n1184: ffmpeg -i in1184.wav -af "highpass=f=120,lowpass=f=15500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1184.wav\n1185: ffmpeg -i in1185.wav -af "highpass=f=130,lowpass=f=15000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1185.wav\n1186: ffmpeg -i in1186.wav -af "highpass=f=140,lowpass=f=14500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1186.wav\n1187: ffmpeg -i in1187.wav -af "highpass=f=150,lowpass=f=14000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1187.wav\n1188: ffmpeg -i in1188.wav -af "highpass=f=160,lowpass=f=13500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1188.wav\n1189: ffmpeg -i in1189.wav -af "highpass=f=170,lowpass=f=13000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1189.wav\n1190: ffmpeg -i in1190.wav -af "highpass=f=80,lowpass=f=16000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1190.wav\n1191: ffmpeg -i in1191.wav -af "highpass=f=90,lowpass=f=15500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1191.wav\n1192: ffmpeg -i in1192.wav -af "highpass=f=100,lowpass=f=15000,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1192.wav\n1193: ffmpeg -i in1193.wav -af "highpass=f=110,lowpass=f=14500,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1193.wav\n1194: ffmpeg -i in1194.wav -af "highpass=f=120,lowpass=f=14000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1194.wav\n1195: ffmpeg -i in1195.wav -af "highpass=f=130,lowpass=f=13500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1195.wav\n1196: ffmpeg -i in1196.wav -af "highpass=f=140,lowpass=f=13000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1196.wav\n1197: ffmpeg -i in1197.wav -af "highpass=f=150,lowpass=f=16000,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1197.wav\n1198: ffmpeg -i in1198.wav -af "highpass=f=160,lowpass=f=15500,dynaudnorm=f=1.5:p=0.9" -c:a pcm_s16le out1198.wav\n1199: ffmpeg -i in1199.wav -af "highpass=f=170,lowpass=f=15000,dynaudnorm=f=2.0:p=0.9" -c:a pcm_s16le out1199.wav\n1200: ffmpeg -i in1200.wav -af "highpass=f=80,lowpass=f=14500,dynaudnorm=f=1.0:p=0.9" -c:a pcm_s16le out1200.wav
"""


# ======================================================================================
# Utility / Constants
# ======================================================================================

AUDIO_EXTS = {
    ".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg", ".aiff", ".wma", ".mka", ".opus", ".mp2", ".mpa", ".ac3"
}

DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
    "Streaming WAV 48k/24b": {
        "output_format": "wav", "bit_depth": 24, "sample_rate": 48000,
        "channels": 2, "normalize_loudness": True, "normalize_mode": "two-pass",
        "target_i": -16.0, "target_tp": -1.5, "target_lra": 11.0
    },
    "Podcast MP3 (V2)": {
        "output_format": "mp3", "quality": "V2", "sample_rate": 48000,
        "channels": 2, "normalize_loudness": True, "normalize_mode": "one-pass",
        "target_i": -16.0, "target_tp": -1.5, "target_lra": 11.0
    },
    "Hi‑Fi FLAC (no normalize)": {
        "output_format": "flac", "sample_rate": 48000, "channels": 2,
        "normalize_loudness": False
    },
    "Mobile AAC 256k": {
        "output_format": "m4a", "quality": "256k", "sample_rate": 44100,
        "channels": 2, "normalize_loudness": False
    },
    "OGG Vorbis Q6": {
        "output_format": "ogg", "quality": "6", "sample_rate": 48000,
        "channels": 2, "normalize_loudness": True, "normalize_mode": "one-pass",
        "target_i": -16.0, "target_tp": -1.5, "target_lra": 11.0
    }
}

SESSION_FILE = Path.home() / ".musicforge_pro_session.json"
LOG_FILE = Path.home() / ".musicforge_pro.log"


# ======================================================================================
# Models
# ======================================================================================

class ProcessingStatus(Enum):
    QUEUED = "Queued"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    SKIPPED = "Skipped"
    FAILED = "Failed"


@dataclass
class MetadataTemplate:
    artist: str = ""
    title: str = "{stem}"
    album: str = ""
    year: str = ""
    genre: str = ""
    comment: str = ""

    def to_args(self, resolved: Dict[str, str]) -> List[str]:
        args: List[str] = []
        for k in ["artist", "title", "album", "year", "genre", "comment"]:
            v = getattr(self, k, "") or ""
            if v:
                # Substitute placeholders
                v2 = v.format(**resolved)
                args += ["-metadata", f"{k}={v2}"]
        return args


@dataclass
class AudioFile:
    path: str
    name: str
    size: int = 0
    duration: float = 0.0
    format: str = ""
    status: ProcessingStatus = ProcessingStatus.QUEUED
    error_message: Optional[str] = None
    output_path: Optional[str] = None
    measured_loudness: Optional[Dict[str, float]] = None


@dataclass
class ProcessingSettings:
    output_format: str = "wav"        # wav, mp3, flac, aac/m4a, ogg
    quality: str = "V2"               # mp3: V0..V4; aac/m4a: 192k..320k; ogg: 0..10
    bit_depth: int = 16               # WAV only: 16/24/32
    sample_rate: int = 48000          # Hz
    channels: int = 2                 # 1=mono, 2=stereo
    normalize_loudness: bool = False
    normalize_mode: str = "one-pass"  # "one-pass" | "two-pass"
    target_i: float = -16.0           # LUFS
    target_tp: float = -1.5           # dBTP
    target_lra: float = 11.0          # LU
    fade_in_sec: float = 0.0
    fade_out_sec: float = 0.0
    overwrite_existing: bool = False
    output_directory: Optional[str] = None
    parallelism: int = 1
    filename_template: str = "{stem}.{ext}"
    metadata: MetadataTemplate = field(default_factory=MetadataTemplate)

    def to_json(self) -> str:
        data = asdict(self)
        data["metadata"] = asdict(self.metadata)
        return json.dumps(data, indent=2)

    @staticmethod
    def from_json(s: str) -> "ProcessingSettings":
        data = json.loads(s)
        md: Dict[str, str] = data.get("metadata") or {}
        data["metadata"] = MetadataTemplate(**md)
        return ProcessingSettings(**data)


# ======================================================================================
# FFmpeg Manager
# ======================================================================================

class FFmpegManager:
    def __init__(self) -> None:
        self.ffmpeg_path = self._find_executable("ffmpeg")
        self.ffprobe_path = self._find_executable("ffprobe")
        self.libfdk_aac_available = self._check_libfdk_aac()

    def _find_executable(self, name: str) -> Optional[str]:
        for p in os.environ.get("PATH", "").split(os.pathsep):
            candidate = Path(p) / (name + (".exe" if os.name == "nt" else ""))
            if candidate.exists() and os.access(candidate, os.X_OK):
                return str(candidate)
        if os.name == "nt":
            candidates = [
                Path("C:/ffmpeg/bin") / f"{name}.exe",
                Path("C:/Program Files/ffmpeg/bin") / f"{name}.exe",
                Path("C:/Program Files (x86)/ffmpeg/bin") / f"{name}.exe",
            ]
            for c in candidates:
                if c.exists() and os.access(c, os.X_OK):
                    return str(c)
        return None

    def _check_libfdk_aac(self) -> bool:
        """Check if libfdk_aac encoder is available in FFmpeg."""
        if not self.ffmpeg_path:
            return False
        try:
            cmd = [self.ffmpeg_path, "-encoders"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
            return "libfdk_aac" in (result.stdout or "")
        except Exception:
            return False

    def is_available(self) -> bool:
        return bool(self.ffmpeg_path and self.ffprobe_path)

    def get_version_info(self) -> Dict[str, str]:
        info: Dict[str, str] = {}
        try:
            if self.ffmpeg_path:
                out = subprocess.run([self.ffmpeg_path, "-version"], capture_output=True, text=True, check=False)
                first = (out.stdout or "").splitlines()[0] if out.stdout else ""
                info["ffmpeg_version"] = first.replace("ffmpeg version", "").strip() or "Unknown"
        except Exception:
            info["ffmpeg_version"] = "Unknown"
        try:
            if self.ffprobe_path:
                out = subprocess.run([self.ffprobe_path, "-version"], capture_output=True, text=True, check=False)
                first = (out.stdout or "").splitlines()[0] if out.stdout else ""
                info["ffprobe_version"] = first.replace("ffprobe version", "").strip() or "Unknown"
        except Exception:
            info["ffprobe_version"] = "Unknown"
        info["ffmpeg_path"] = self.ffmpeg_path or "Not Found"
        info["ffprobe_path"] = self.ffprobe_path or "Not Found"
        info["libfdk_aac_available"] = "Yes" if self.libfdk_aac_available else "No"
        return info

    def probe_duration(self, path: str) -> float:
        if not self.ffprobe_path:
            return 0.0
        try:
            cmd = [
                self.ffprobe_path, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ]
            out = subprocess.run(cmd, capture_output=True, text=True, check=False)
            dur_str = (out.stdout or "").strip()
            return float(dur_str) if dur_str else 0.0
        except Exception:
            return 0.0


FFMPEG = FFmpegManager()


# ======================================================================================
# Audio Processor
# ======================================================================================

ProgressCallback = Callable[[str, float], None]  # kind, value (0..100)

class AudioProcessor:
    def __init__(self, ff: FFmpegManager) -> None:
        self.ff = ff

    def format_to_extension(self, fmt: str) -> str:
        return "m4a" if fmt.lower() in {"aac", "m4a"} else fmt.lower()

    # ---------- Filters / Codec ----------

    def build_filters(self, af: AudioFile, s: ProcessingSettings, measured: Optional[Dict[str, float]] = None) -> List[str]:
        filters: List[str] = []

        if s.normalize_loudness:
            if s.normalize_mode == "two-pass" and measured:
                filters.append(
                    "loudnorm="
                    f"I={s.target_i}:TP={s.target_tp}:LRA={s.target_lra}:"
                    f"measured_I={measured.get('input_i',0)}:"
                    f"measured_TP={measured.get('input_tp',0)}:"
                    f"measured_LRA={measured.get('input_lra',0)}:"
                    f"measured_thresh={measured.get('input_thresh',0)}:"
                    f"offset={measured.get('target_offset',0)}:"
                    "linear=true:print_format=summary"
                )
            else:
                filters.append(f"loudnorm=I={s.target_i}:TP={s.target_tp}:LRA={s.target_lra}:print_format=summary")

        if s.fade_in_sec and s.fade_in_sec > 0:
            filters.append(f"afade=t=in:st=0:d={float(s.fade_in_sec):g}")

        if s.fade_out_sec and s.fade_out_sec > 0 and af.duration and af.duration > 0:
            start = max(0.0, af.duration - float(s.fade_out_sec))
            filters.append(f"afade=t=out:st={start:g}:d={float(s.fade_out_sec):g}")

        return ["-af", ",".join(filters)] if filters else []

    def build_encoding_args(self, s: ProcessingSettings) -> List[str]:
        fmt = s.output_format.lower()
        if fmt == "wav":
            bit_fmt = {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_s32le"}.get(s.bit_depth, "pcm_s16le")
            return ["-c:a", bit_fmt]
        if fmt == "flac":
            return ["-c:a", "flac"]
        if fmt in {"aac", "m4a"}:
            br = s.quality if s.quality.endswith("k") else "256k"
            # Use libfdk_aac if available, fallback to built-in aac
            encoder = "libfdk_aac" if FFMPEG.libfdk_aac_available else "aac"
            return ["-c:a", encoder, "-b:a", br]
        if fmt == "mp3":
            qmap = {"V0": "0", "V1": "1", "V2": "2", "V3": "3", "V4": "4"}
            lame_q = qmap.get(str(s.quality).upper(), "2")
            return ["-c:a", "libmp3lame", "-qscale:a", lame_q]
        if fmt == "ogg":
            try:
                q = float(s.quality)
            except Exception:
                q = 6.0
            q = max(0.0, min(10.0, q))
            return ["-c:a", "libvorbis", "-qscale:a", str(q)]
        if fmt == "opus":
            # Opus defaults to 48kHz for best quality
            if not s.sample_rate:
                return ["-c:a", "libopus", "-b:a", "128k", "-ar", "48000"]
            else:
                return ["-c:a", "libopus", "-b:a", "128k"]
        return []

    # ---------- Two‑pass measurement ----------

    def measure_loudness(self, af: AudioFile, s: ProcessingSettings) -> Optional[Dict[str, float]]:
        if not self.ff.ffmpeg_path:
            return None
        cmd = [
            self.ff.ffmpeg_path, "-v", "error",
            "-i", af.path,
            "-af", f"loudnorm=I={s.target_i}:TP={s.target_tp}:LRA={s.target_lra}:print_format=json",
            "-f", "null", "-"
        ]
        try:
            # Dynamic timeout based on file duration: min 30s, max 300s, or 2x duration
            timeout = 30
            if af.duration and af.duration > 0:
                timeout = max(30, min(300, int(af.duration * 2)))
            
            p = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)
            stderr = p.stderr or ""
            start = stderr.find("{")
            end = stderr.rfind("}")
            if start != -1 and end != -1 and end > start:
                blob = json.loads(stderr[start:end+1])
                keys = ["input_i", "input_tp", "input_lra", "input_thresh", "target_offset"]
                return {k: float(blob.get(k, 0)) for k in keys}
        except subprocess.TimeoutExpired:
            # Timeout during loudness measurement - fall back to one-pass
            return None
        except Exception:
            return None
        return None

    # ---------- Command / Exec ----------

    def build_command(self, af: AudioFile, s: ProcessingSettings, output_path: Path,
                      resolved_md: Dict[str, str], measured: Optional[Dict[str, float]] = None) -> List[str]:
        assert self.ff.ffmpeg_path, "FFmpeg path not set"
        cmd: List[str] = [self.ff.ffmpeg_path, "-y" if s.overwrite_existing else "-n", "-v", "error", "-hide_banner"]
        cmd += ["-i", af.path]
        if s.sample_rate:
            cmd += ["-ar", str(s.sample_rate)]
        if s.channels:
            cmd += ["-ac", str(s.channels)]
        cmd += self.build_filters(af, s, measured)
        cmd += s.metadata.to_args(resolved_md)
        cmd += self.build_encoding_args(s)
        cmd += ["-progress", "pipe:1", "-nostats", "-v", "error"]
        ext = self.format_to_extension(s.output_format)
        if ext in {"m4a", "aac"}:
            cmd += ["-f", "mp4"]
        cmd += [str(output_path)]
        return cmd

    def process_file(self, af: AudioFile, s: ProcessingSettings, output_path: Path,
                     progress_callback: Optional[ProgressCallback] = None,
                     stop_event: Optional[threading.Event] = None) -> Tuple[bool, Optional[str]]:
        try:
            if not af.duration or af.duration <= 0:
                af.duration = FFMPEG.probe_duration(af.path)

            # Build metadata placeholders
            resolved = {
                "stem": Path(af.path).stem,
                "ext": self.format_to_extension(s.output_format),
                "name": af.name,
                "size_mb": f"{af.size/(1024*1024):.1f}",
                "duration_s": f"{af.duration:.1f}" if af.duration else ""
            }

            measured = None
            if s.normalize_loudness and s.normalize_mode == "two-pass":
                measured = self.measure_loudness(af, s)
                af.measured_loudness = measured

            cmd = self.build_command(af, s, output_path, resolved_md=resolved, measured=measured)
            
            # Log command for debugging (at debug level)
            logging.debug(f"FFmpeg command: {' '.join(cmd)}")

            # Use improved FFmpeg runner if available
            if ffmpeg_runner_available and run_ffmpeg is not None:
                def progress_wrapper(out_time_ms: Optional[float] = None, speed: Optional[float] = None, percent: Optional[float] = None, eta_sec: Optional[float] = None) -> None:
                    if progress_callback:
                        if percent is not None:
                            progress_callback("progress", percent)
                        if eta_sec is not None:
                            progress_callback("eta", eta_sec)
                
                # Use the improved runner
                rc, _, last = run_ffmpeg(
                    cmd, 
                    on_progress=progress_wrapper,
                    duration_sec=af.duration,
                    timeout=None
                )
                
                if rc == 0:
                    return True, None
                else:
                    # Log the full ffmpeg command on failures
                    logging.error("ffmpeg failed (%s)\nCMD: %s\nLAST: %s", rc, shlex.join(cmd), last)
                    return False, last or f"ffmpeg exited with {rc}"
            else:
                # Fallback to original implementation
                return self._process_file_original(af, s, output_path, progress_callback, stop_event, cmd)
        except Exception as e:
            return False, str(e)
    
    def _process_file_original(self, af: AudioFile, _s: ProcessingSettings, output_path: Path,
                              progress_callback: Optional[ProgressCallback] = None,
                              stop_event: Optional[threading.Event] = None, cmd: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
        """Original process_file implementation as fallback"""
        try:
            if cmd is None:
                return False, "No command provided"
                
            # Windows process group for proper CTRL_BREAK_EVENT handling
            kwargs: Dict[str, Any] = {}
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True, **kwargs
            )

            # Initialize progress tracking variables
            out_ms = 0.0
            speed = 1.0

            while True:
                if stop_event and stop_event.is_set():
                    try:
                        if os.name == "nt":
                            # Use CTRL_BREAK_EVENT for proper Windows process termination
                            import ctypes
                            ctypes.windll.kernel32.GenerateConsoleCtrlEvent(1, proc.pid)  # CTRL_BREAK_EVENT
                            # Give it a moment to terminate gracefully
                            try:
                                proc.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                proc.kill()
                        else:
                            proc.send_signal(signal.SIGINT)
                    except Exception:
                        # Fallback to terminate if CTRL_BREAK_EVENT fails
                        try:
                            proc.terminate()
                            proc.wait(timeout=1)
                        except:
                            proc.kill()
                    return False, "Cancelled"

                if proc.stdout is None:
                    break
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.02)
                    continue
                line = line.strip()
                if line.startswith("out_time_ms="):
                    try:
                        out_ms = float(line.split("=", 1)[1])
                        if af.duration and af.duration > 0:
                            pct = min(100.0, (out_ms / 1_000_000.0) / af.duration * 100.0)
                            if progress_callback:
                                progress_callback("progress", pct)
                    except Exception:
                        pass
                elif line.startswith("speed="):
                    try:
                        speed = float(line.split("=", 1)[1])
                        if af.duration and af.duration > 0 and speed > 0 and out_ms > 0:
                            remaining_time = (af.duration - (out_ms / 1_000_000.0)) / speed
                            if progress_callback:
                                progress_callback("eta", remaining_time)
                    except Exception:
                        pass
                elif line.startswith("progress=") and "end" in line:
                    if progress_callback:
                        progress_callback("progress", 100.0)

            err = (proc.stderr.read().strip() if proc.stderr else "")
            ret = proc.wait()
            if ret == 0:
                return True, None
            
            # Log the full ffmpeg command on failures (low-noise, high-value debug)
            stderr_lines = err.splitlines() if err else []
            last = (stderr_lines[-1] if stderr_lines else "").strip()
            logging.error("ffmpeg failed (%s)\nCMD: %s\nLAST: %s", ret, shlex.join(cmd), last)
            return False, last or f"FFmpeg exited with code {ret}"
        except Exception as e:
            return False, str(e)


# ======================================================================================
# Preset / Session management
# ======================================================================================

class PresetManager:
    def __init__(self) -> None:
        self.user_dir = Path.home() / ".musicforge_pro"
        self.user_dir.mkdir(parents=True, exist_ok=True)

    def list_builtin(self) -> List[str]:
        return list(DEFAULT_PRESETS.keys())

    def load_builtin(self, name: str) -> ProcessingSettings:
        base = DEFAULT_PRESETS.get(name, {})
        merged: Dict[str, Any] = {**ProcessingSettings().__dict__, **base}
        return ProcessingSettings(**merged)

    def save_user_preset(self, name: str, settings: ProcessingSettings) -> Path:
        path = self.user_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(settings.to_json())
        return path

    def list_user_presets(self) -> List[str]:
        return [p.stem for p in self.user_dir.glob("*.json")]

    def load_user_preset(self, name: str) -> ProcessingSettings:
        path = self.user_dir / f"{name}.json"
        with open(path, "r", encoding="utf-8") as fp:
            js = fp.read()
        return ProcessingSettings.from_json(js)


class SessionStore:
    def __init__(self, session_file: Path = SESSION_FILE) -> None:
        self.path = session_file

    def save(self, settings: ProcessingSettings, geometry: Optional[str] = None) -> None:
        data = {
            "settings": json.loads(settings.to_json()),
            "geometry": geometry or ""
        }
        with open(self.path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2)

    def load(self) -> Tuple[Optional[ProcessingSettings], Optional[str]]:
        if not self.path.exists():
            return None, None
        try:
            with open(self.path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            s = ProcessingSettings.from_json(json.dumps(data.get("settings", {})))
            geo = data.get("geometry") or None
            return s, geo
        except Exception:
            return None, None


# ======================================================================================
# Folder Watch (polling)
# ======================================================================================

class FolderWatcher(threading.Thread):
    def __init__(self, folder: Path, poll_seconds: int, on_new: Callable[[List[str]], None]) -> None:
        super().__init__(daemon=True)
        self.folder = folder
        self.poll_seconds = max(1, int(poll_seconds))
        self.on_new = on_new
        self._stop = threading.Event()
        self._seen: set[str] = set()

    def run(self) -> None:
        while not self._stop.is_set():
            if self.folder.exists():
                fresh: List[str] = []
                for root, _, files in os.walk(self.folder):
                    for fn in files:
                        p = str(Path(root) / fn)
                        if Path(p).suffix.lower() in AUDIO_EXTS and p not in self._seen:
                            self._seen.add(p)
                            fresh.append(p)
                if fresh:
                    self.on_new(fresh)
            time.sleep(self.poll_seconds)

    def stop(self) -> None:
        self._stop.set()


# ======================================================================================
# CLI
# ======================================================================================

def build_cli_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="music_forge_pro_max.py", description=f"{APP_NAME} {APP_VERSION} — FFmpeg batch audio studio")
    p.add_argument("--gui", action="store_true", help="Force launch GUI even if CLI args are present")
    p.add_argument("--input", "-i", help="Input file or folder (for CLI mode)")
    p.add_argument("--output", "-o", help="Output folder (CLI mode)")
    p.add_argument("--format", "-f", dest="fmt", choices=["wav","mp3","flac","aac","m4a","ogg","opus"], help="Output format")
    p.add_argument("--quality", "-q", help="Quality (mp3: V0..V4, aac/m4a: e.g., 256k, ogg: 0..10)")
    p.add_argument("--bit-depth", type=int, default=None, help="WAV bit depth: 16/24/32")
    p.add_argument("--sr", "--sample-rate", type=int, default=None, help="Sample rate Hz")
    p.add_argument("--ch", "--channels", type=int, default=None, help="Number of audio channels")
    p.add_argument("--normalize", action="store_true", help="Enable loudness normalization")
    p.add_argument("--mode", choices=["one-pass","two-pass"], default=None, help="Normalization mode")
    p.add_argument("--lufs", type=float, default=None, help="Target integrated loudness, e.g., -16.0")
    p.add_argument("--tp", type=float, default=None, help="True peak ceiling, e.g., -1.5")
    p.add_argument("--lra", type=float, default=None, help="Target loudness range, e.g., 11.0")
    p.add_argument("--fade-in", type=float, default=None, help="Fade-in duration seconds")
    p.add_argument("--fade-out", type=float, default=None, help="Fade-out duration seconds")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    p.add_argument("--template", help="Filename template, e.g., '{artist} - {title}.{ext}'")
    p.add_argument("--meta", nargs="*", help="Metadata k=v pairs, e.g., artist='Name' title='{stem}'")
    p.add_argument("--parallel", type=int, default=1, help="Parallel workers")
    p.add_argument("--watch", help="Watch a folder and auto-process new files (polling)")
    p.add_argument("--poll", type=int, default=10, help="Watch polling seconds")
    p.add_argument("--preset", help="Use a built-in preset by name")
    p.add_argument("--report", help="CSV report output path")
    p.add_argument("--manual", action="store_true", help="Print the in-app user manual and exit")
    p.add_argument("--power-guide", action="store_true", help="Print the power user guide & cookbook and exit")
    p.add_argument("--dry-run", action="store_true", help="Print planned outputs and settings without processing")
    p.add_argument("--preset-list", action="store_true", help="List available presets and exit")
    p.add_argument("--test-progress", action="store_true", help="Test progress parsing with simulated ffmpeg output")
    # Allow non-interactive EULA acceptance in headless/CI environments.
    p.add_argument("--accept-eula", action="store_true",
                   help="Accept the EULA non-interactively (useful for headless/CI runs).")
    return p


def _validate_settings(s: ProcessingSettings) -> ProcessingSettings:
    """Centralize and enforce argument ranges (so ffmpeg doesn't fail late)"""
    # Use centralized validator if available
    if settings_validator_available and validate_settings is not None:
        try:
            validate_settings(s)
            return s
        except ValueError as e:
            raise ValueError(f"Settings validation failed: {e}")
    
    # Fallback validation (original logic)
    # loudness
    if not (-36.0 <= s.target_i <= -8.0):
        raise ValueError(f"--lufs must be between -36 and -8, got {s.target_i}")
    if s.target_tp > -1.0:
        raise ValueError(f"--tp must be ≤ -1.0 dBTP, got {s.target_tp}")
    if s.target_lra < 0:
        raise ValueError(f"--lra must be ≥ 0, got {s.target_lra}")
    
    # audio format
    if s.bit_depth not in (16, 24, 32):
        raise ValueError(f"--bit-depth must be 16/24/32, got {s.bit_depth}")
    if s.sample_rate not in (22050, 32000, 44100, 48000, 88200, 96000):
        raise ValueError(f"--sr must be a common rate (22050, 32000, 44100, 48000, 88200, 96000), got {s.sample_rate}")
    if s.channels < 1 or s.channels > 8:
        # Provide a clear inclusive range using two dots to avoid
        # confusion ("1.8" was previously seen).  Explicitly include
        # the offending value in the message.
        raise ValueError(f"--ch must be 1..8, got {s.channels}")
    
    return s

def validate_cli_args(args: argparse.Namespace) -> Tuple[bool, str]:
    """Validate CLI arguments and return (is_valid, error_message)"""
    try:
        # Create a temporary settings object to validate
        s = ProcessingSettings()
        if args.bit_depth is not None: s.bit_depth = int(args.bit_depth)
        if args.sr is not None: s.sample_rate = int(args.sr)
        if args.ch is not None: s.channels = int(args.ch)
        if args.lufs is not None: s.target_i = float(args.lufs)
        if args.tp is not None: s.target_tp = float(args.tp)
        if args.lra is not None: s.target_lra = float(args.lra)
        
        _validate_settings(s)
        return True, ""
    except ValueError as e:
        return False, str(e)


def parse_kv_pairs(pairs: Optional[List[str]]) -> Dict[str, str]:
    """Make metadata KV parsing robust to = and quotes inside values"""
    out = {}
    if not pairs:
        return out
    for item in pairs:
        if "=" not in item:
            continue
        # allow escaped \= and \"
        safe = item.replace(r"\=", "\uE000")
        key, val = safe.split("=", 1)
        val = val.replace("\uE000", "=")
        val = val.strip()
        # Strip surrounding quotes if present (either single or double).  Escaped
        # quotes inside the value are unescaped afterwards.  This logic must
        # remain entirely within ``parse_kv_pairs`` and not leak out to the
        # argument parser; see build_cli_parser for argument definitions.
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1].replace(r'\"', '"').replace(r"\'", "'")
        out[key.strip()] = val
    return out


def collect_audio_paths(inp: str) -> List[str]:
    p = Path(inp)
    if p.is_file():
        return [str(p)]
    found: List[str] = []
    for root, _, files in os.walk(p):
        for fn in files:
            if Path(fn).suffix.lower() in AUDIO_EXTS:
                found.append(str(Path(root) / fn))
    return found


def cli_main(argv: List[str]) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    # Ensure the EULA has been accepted before proceeding.  Even though a
    # lightweight acceptance check is performed in the module entrypoint,
    # perform it again here so that CLI usage clearly respects the
    # --accept-eula flag and provides an early exit on failure.
    if not ensure_eula_accepted(cli_accept=getattr(args, "accept_eula", False)):
        print("EULA not accepted. Use --accept-eula to run headless.")
        return 2

    if args.manual:
        print(USER_MANUAL)
        return 0
    if args.power_guide:
        print(POWER_GUIDE)
        return 0

    if args.preset_list:
        print("Available presets:")
        pm = PresetManager()
        for name in pm.list_builtin():
            print(f"  - {name}")
        return 0

    if args.test_progress:
        print("Testing progress parsing with simulated ffmpeg output...")
        try:
            import subprocess
            import sys
            
            # Run the simulator and capture output
            result = subprocess.run([sys.executable, "simulate_ffmpeg_progress.py"], 
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                print("Progress simulation completed successfully!")
                print("Sample output:")
                print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            else:
                print(f"Progress simulation failed: {result.stderr}")
                return 1
        except ImportError:
            print("simulate_ffmpeg_progress.py not found. Please ensure it's in the same directory.")
            return 1
        except Exception as e:
            print(f"Error testing progress: {e}")
            return 1
        return 0

    if args.gui or (not args.input and tk_available):
        # Launch GUI (if requested or if no input and Tk is present)
        return gui_main()

    if not args.input or not args.output:
        print("CLI mode requires --input and --output. Use --gui to launch desktop app.")
        return 2

    if not FFMPEG.is_available():
        print("FFmpeg/FFprobe not found. Install from https://ffmpeg.org/download.html")
        return 2

    files = collect_audio_paths(args.input)
    if not files:
        print("No audio files found.")
        return 0

    s = ProcessingSettings()
    if args.preset:
        pm = PresetManager()
        if args.preset in pm.list_builtin():
            s = pm.load_builtin(args.preset)
        else:
            # try user preset
            try:
                s = pm.load_user_preset(args.preset)
            except Exception:
                print(f"Preset not found: {args.preset}")

    # Validate CLI arguments first
    is_valid, error_msg = validate_cli_args(args)
    if not is_valid:
        print(f"ERROR: {error_msg}")
        return 2

    # Override with CLI flags (validation already done)
    if args.fmt: s.output_format = args.fmt
    if args.quality: 
        s.quality = args.quality
        # Warn if quality is set for formats that don't use it
        if s.output_format.lower() in {"wav", "flac"} and not args.dry_run:
            print(f"INFO: Quality setting '{args.quality}' is ignored for {s.output_format.upper()} format")
    if args.bit_depth is not None: s.bit_depth = int(args.bit_depth)
    if args.sr is not None: s.sample_rate = int(args.sr)
    if args.ch is not None: s.channels = int(args.ch)
    if args.normalize: s.normalize_loudness = True
    if args.mode: s.normalize_mode = args.mode
    if args.lufs is not None: s.target_i = float(args.lufs)
    if args.tp is not None: s.target_tp = float(args.tp)
    if args.lra is not None: s.target_lra = float(args.lra)
    if args.fade_in is not None: s.fade_in_sec = float(args.fade_in)
    if args.fade_out is not None: s.fade_out_sec = float(args.fade_out)
    if args.overwrite: s.overwrite_existing = True
    if args.template: s.filename_template = args.template
    if args.parallel: s.parallelism = max(1, int(args.parallel))

    # Validate settings after all CLI overrides
    try:
        _validate_settings(s)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 2

    md_pairs = parse_kv_pairs(args.meta)
    for k, v in md_pairs.items():
        if hasattr(s.metadata, k):
            setattr(s.metadata, k, v)

    outdir = Path(args.output)
    if args.dry_run:
        print("DRY RUN - Planned outputs and settings:")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Format: {s.output_format}")
        print(f"Quality: {s.quality}")
        if s.bit_depth: print(f"Bit depth: {s.bit_depth}")
        if s.sample_rate: print(f"Sample rate: {s.sample_rate}")
        if s.channels: print(f"Channels: {s.channels}")
        if s.normalize_loudness:
            print(f"Normalize: {s.normalize_mode} (I={s.target_i}, TP={s.target_tp}, LRA={s.target_lra})")
        print(f"Parallel workers: {s.parallelism}")
        print(f"Overwrite existing: {s.overwrite_existing}")
        print(f"Filename template: {s.filename_template}")
        print(f"Files to process: {len(files)}")
        for i, f in enumerate(files[:5], 1):  # Show first 5 files
            print(f"  {i}. {Path(f).name}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more files")
        return 0

    if not outdir.exists():
        outdir.mkdir(parents=True, exist_ok=True)

    # Process
    proc = AudioProcessor(FFMPEG)

    total = len(files)
    ok_count = 0
    fail_count = 0

    rows = []

    for idx, fp in enumerate(files, start=1):
        src = Path(fp)
        ext = proc.format_to_extension(s.output_format)
        # Prepare placeholders for filename template
        placeholders = {
            "stem": src.stem,
            "ext": ext,
            "index": idx,
            "artist": s.metadata.artist.format(stem=src.stem, ext=ext, index=idx) if s.metadata.artist else "",
            "title": s.metadata.title.format(stem=src.stem, ext=ext, index=idx) if s.metadata.title else src.stem,
        }
        fname = s.filename_template.format(**placeholders)
        dst = outdir / fname
        
        # Non-destructive write protection
        if dst.exists() and not s.overwrite_existing:
            base = dst.stem
            ext = dst.suffix
            counter = 1
            while dst.exists():
                dst = outdir / f"{base}_{counter:03d}{ext}"
                counter += 1

        af = AudioFile(path=str(src), name=src.name, size=int(src.stat().st_size), format=src.suffix.lstrip(".").lower())

        # Check for skip conditions before processing
        if dst.exists() and not s.overwrite_existing:
            print(f"[{idx}/{total}] {src.name} -> {fname}  SKIPPED (file exists)")
            rows.append([src.name, af.format.upper(), f"{af.size/(1024*1024):.1f}", f"{af.duration:.1f}" if af.duration else "", "SKIPPED", "File exists, skipping", str(dst), "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", ""])  # type: ignore
            continue

        # Hard block same in/out path to prevent clobbering
        try:
            if os.path.samefile(str(src), str(dst)):
                print(f"[{idx}/{total}] {src.name} -> {fname}  ERROR: Would overwrite source file")
                rows.append([src.name, af.format.upper(), f"{af.size/(1024*1024):.1f}", f"{af.duration:.1f}" if af.duration else "", "ERROR", "Would overwrite source; refusing to process", str(dst), "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", ""])  # type: ignore
                fail_count += 1
                continue
        except OSError:
            # Files don't exist or can't be compared, use string comparison as fallback
            if str(dst.resolve()) == str(src.resolve()):
                print(f"[{idx}/{total}] {src.name} -> {fname}  ERROR: Would overwrite source file")
                rows.append([src.name, af.format.upper(), f"{af.size/(1024*1024):.1f}", f"{af.duration:.1f}" if af.duration else "", "ERROR", "Would overwrite source; refusing to process", str(dst), "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", ""])  # type: ignore
                fail_count += 1
                continue

        def cb(kind: str, value: float) -> None:
            if kind == "progress":
                pct = f"{value:5.1f}%"
                print(f"[{idx}/{total}] {src.name} -> {fname} {pct}", end="\r")

        ok, err = proc.process_file(af, s, dst, progress_callback=cb)

        if ok:
            ok_count += 1
            # Enhanced metadata for successful files
            bitrate = "N/A"
            sample_rate = str(s.sample_rate) if s.sample_rate else "N/A"
            channels = str(s.channels) if s.channels else "N/A"
            lufs = f"{af.measured_loudness.get('input_i', 'N/A'):.1f}" if af.measured_loudness else "N/A"
            true_peak = f"{af.measured_loudness.get('input_tp', 'N/A'):.1f}" if af.measured_loudness else "N/A"
            encoder = "libfdk_aac" if s.output_format in ["aac", "m4a"] and FFMPEG.libfdk_aac_available else s.output_format
            warnings = "Two-pass fallback" if s.normalize_mode == "two-pass" and not af.measured_loudness else ""
            
            rows.append([src.name, af.format.upper(), f"{af.size/(1024*1024):.1f}", f"{af.duration:.1f}" if af.duration else "", "COMPLETED", "", str(dst), bitrate, sample_rate, channels, lufs, true_peak, encoder, warnings])  # type: ignore
            print(f"\n[{idx}/{total}] {src.name} -> {fname}  DONE")
        else:
            fail_count += 1
            rows.append([src.name, af.format.upper(), f"{af.size/(1024*1024):.1f}", f"{af.duration:.1f}" if af.duration else "", "FAILED", err or "", str(dst), "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", ""])  # type: ignore
            print(f"\n[{idx}/{total}] {src.name} -> {fname}  ERROR: {err}")

    if args.report:
        try:
            with open(args.report, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["File", "Format", "Size (MB)", "Duration (s)", "Status", "Error", "Output", "Bitrate", "Sample Rate", "Channels", "LUFS", "True Peak", "Encoder", "Warnings"])  # type: ignore
                for r in rows:
                    w.writerow(r)  # type: ignore
            print(f"Report written: {args.report}")
        except Exception as e:
            print(f"Report error: {e}")

    print(f"\nDone. OK={ok_count} FAILED={fail_count}")
    return 0 if fail_count == 0 else 1


# ======================================================================================
# GUI (Tkinter)
# ======================================================================================

class MusicForgeApp(tk.Tk if tk is not None else object):  # type: ignore
    # Note: This class uses tkinter which may not be available in all environments.
    # All tkinter operations are type-ignored due to optional imports
    # pyright: ignore[reportGeneralTypeIssues,reportOptionalMemberAccess,reportUnknownMemberType,reportUnknownVariableType,reportUnknownArgumentType,reportUnknownReturnType,reportUnknownParameterType,reportUnknownLambdaType,reportUnknownInheritance,reportUnknownSubclass]
    def __init__(self) -> None:  # type: ignore
        _ensure_tkinter()
        super().__init__()  # type: ignore
        self.title(f"{APP_NAME} — Desktop")  # type: ignore
        self.geometry("1400x900")  # type: ignore
        self.minsize(1200, 800)  # type: ignore
        self._log_lock = threading.Lock()  # Thread-safe logging

        # Status bar: provide instant feedback for user actions.  This
        # variable holds transient messages (e.g. progress, FFmpeg status) and
        # automatically reverts to "Ready." after a delay.  The label is
        # packed at the bottom of the window.
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status_var, style='Body.TLabel').pack(
            side="bottom", fill="x", padx=8, pady=(0, 6)
        )

        def set_status(msg: str, reset_ms: int = 2500) -> None:
            """Update the status bar and reset it after a short delay."""
            self.status_var.set(msg)
            self.after(reset_ms, lambda: self.status_var.set("Ready."))

        # Expose the method on the instance for use in callbacks
        self.set_status = set_status  # type: ignore[attr-defined]
        
        # Enhanced Dark UI Theme
        self.colors = {
            'bg_primary': '#0d1117',       # GitHub dark background
            'bg_secondary': '#161b22',     # Card background
            'bg_tertiary': '#21262d',      # Input background
            'bg_quaternary': '#30363d',    # Hover background
            'accent': '#58a6ff',           # GitHub blue accent
            'accent_hover': '#79c0ff',     # Blue hover
            'accent_pressed': '#1f6feb',   # Blue pressed
            'success': '#3fb950',          # GitHub green success
            'warning': '#d29922',          # GitHub orange warning
            'error': '#f85149',            # GitHub red error
            'text_primary': '#f0f6fc',     # Primary text
            'text_secondary': '#8b949e',   # Secondary text
            'text_muted': '#6e7681',       # Muted text
            'text_disabled': '#484f58',    # Disabled text
            'border': '#30363d',           # Border color
            'border_focus': '#58a6ff',     # Focus border
            'border_hover': '#8b949e',     # Hover border
            'shadow': 'rgba(0, 0, 0, 0.3)' # Shadow color
        }
        
        # Configure root window
        self.configure(bg=self.colors['bg_primary'])
        self.style = ttk.Style()
        self._configure_styles()

        self.proc = AudioProcessor(FFMPEG)
        self.preset_mgr = PresetManager()
        self.session = SessionStore()

        self.settings = ProcessingSettings()
        self.audio_files: List[AudioFile] = []
        self._log_queue: "queue.Queue[Tuple[str,str]]" = queue.Queue()
        self._stop_event = threading.Event()
        self._threads: List[threading.Thread] = []
        self._watcher: Optional[FolderWatcher] = None

        # TK Vars
        self.output_dir_var = tk.StringVar(value=self.settings.output_directory or "")
        self.format_var = tk.StringVar(value=self.settings.output_format)
        self.quality_var = tk.StringVar(value=self.settings.quality)
        self.bit_depth_var = tk.IntVar(value=self.settings.bit_depth)
        self.sample_rate_var = tk.IntVar(value=self.settings.sample_rate)
        self.channels_var = tk.IntVar(value=self.settings.channels)
        self.normalize_var = tk.BooleanVar(value=self.settings.normalize_loudness)
        self.normalize_mode_var = tk.StringVar(value=self.settings.normalize_mode)
        self.target_i_var = tk.DoubleVar(value=self.settings.target_i)
        self.target_tp_var = tk.DoubleVar(value=self.settings.target_tp)
        self.target_lra_var = tk.DoubleVar(value=self.settings.target_lra)
        self.fade_in_var = tk.DoubleVar(value=self.settings.fade_in_sec)
        self.fade_out_var = tk.DoubleVar(value=self.settings.fade_out_sec)
        self.overwrite_var = tk.BooleanVar(value=self.settings.overwrite_existing)
        self.parallelism_var = tk.IntVar(value=self.settings.parallelism)
        self.template_var = tk.StringVar(value=self.settings.filename_template)

        # Metadata vars
        self.meta_artist = tk.StringVar(value=self.settings.metadata.artist)
        self.meta_title = tk.StringVar(value=self.settings.metadata.title)
        self.meta_album = tk.StringVar(value=self.settings.metadata.album)
        self.meta_year = tk.StringVar(value=self.settings.metadata.year)
        self.meta_genre = tk.StringVar(value=self.settings.metadata.genre)
        self.meta_comment = tk.StringVar(value=self.settings.metadata.comment)

        self._build_menu()

        # After the window is initialized and shown, perform a gentle
        # first-run FFmpeg check.  If FFmpeg/ffprobe are not available,
        # prompt the user once to install them via the official download page.
        self.after(300, self._startup_ffmpeg_check)
        self._build_tabs()
        self._wire_events()

        # Restore session
        s, geo = self.session.load()
        if s:
            self._apply_settings_to_ui(s)
            self.settings = s
        if geo:
            try:
                self.geometry(geo)
            except Exception:
                pass

        self._check_ffmpeg()
        self.after(50, self._drain_log_queue)

    def _configure_styles(self) -> None:
        """Configure modern ttk styles"""
        # Configure main styles
        self.style.theme_use('clam')

        # ------------------------------------------------------------------
        # Baseline Primary CTA style
        #
        # Define a consistent look for call‑to‑action buttons when using
        # the default 'clam' theme or other themes that do not override
        # 'Primary.TButton'.  These settings ensure the button pops even if
        # our dark theme colours are not applied.  The dark theme
        # definitions later in this method will override these values.
        try:
            self.style.configure("Primary.TButton", padding=8, relief="flat")
            self.style.map(
                "Primary.TButton",
                background=[("!disabled", "#3b82f6"), ("active", "#2563eb")],
                foreground=[("!disabled", "white")],
            )
        except Exception:
            # Ignore style errors in minimal environments
            pass
        
        # Frame styles
        self.style.configure('Card.TFrame', 
                           background=self.colors['bg_secondary'],
                           relief='flat',
                           borderwidth=1)
        
        # Label styles
        self.style.configure('Title.TLabel',
                           background=self.colors['bg_secondary'],
                           foreground=self.colors['text_primary'],
                           font=('Segoe UI', 16, 'bold'))
        
        self.style.configure('Heading.TLabel',
                           background=self.colors['bg_secondary'],
                           foreground=self.colors['text_primary'],
                           font=('Segoe UI', 12, 'bold'))
        
        self.style.configure('Body.TLabel',
                           background=self.colors['bg_secondary'],
                           foreground=self.colors['text_secondary'],
                           font=('Segoe UI', 9))
        
        # Button styles
        self.style.configure('Primary.TButton',
                           background=self.colors['accent'],
                           foreground=self.colors['text_primary'],
                           font=('Segoe UI', 9, 'bold'),
                           relief='flat',
                           borderwidth=0,
                           padding=(12, 8),
                           focuscolor='none')
        
        self.style.map('Primary.TButton',
                      background=[('active', self.colors['accent_hover']),
                                ('pressed', self.colors['accent_pressed'])])
        
        self.style.configure('Secondary.TButton',
                           background=self.colors['bg_tertiary'],
                           foreground=self.colors['text_primary'],
                           font=('Segoe UI', 9),
                           relief='flat',
                           borderwidth=1,
                           padding=(8, 6),
                           focuscolor='none')
        
        self.style.map('Secondary.TButton',
                      background=[('active', self.colors['bg_quaternary']),
                                ('pressed', self.colors['bg_quaternary'])],
                      bordercolor=[('active', self.colors['border_hover'])])
        
        # Entry styles
        self.style.configure('Modern.TEntry',
                           fieldbackground=self.colors['bg_tertiary'],
                           foreground=self.colors['text_primary'],
                           borderwidth=1,
                           relief='solid',
                           insertcolor=self.colors['text_primary'],
                           focuscolor=self.colors['border_focus'])
        
        self.style.map('Modern.TEntry',
                      bordercolor=[('focus', self.colors['border_focus']),
                                  ('active', self.colors['border_hover'])])
        
        # Combobox styles
        self.style.configure('Modern.TCombobox',
                           fieldbackground=self.colors['bg_tertiary'],
                           background=self.colors['bg_tertiary'],
                           foreground=self.colors['text_primary'],
                           borderwidth=1,
                           relief='solid',
                           focuscolor=self.colors['border_focus'])
        
        self.style.map('Modern.TCombobox',
                      bordercolor=[('focus', self.colors['border_focus']),
                                  ('active', self.colors['border_hover'])],
                      fieldbackground=[('readonly', self.colors['bg_tertiary'])])
        
        # Progress bar styles
        self.style.configure('Modern.Horizontal.TProgressbar',
                           background=self.colors['accent'],
                           troughcolor=self.colors['bg_tertiary'],
                           borderwidth=0,
                           lightcolor=self.colors['accent'],
                           darkcolor=self.colors['accent'])
        
        # Treeview styles
        self.style.configure('Modern.Treeview',
                           background=self.colors['bg_tertiary'],
                           foreground=self.colors['text_primary'],
                           fieldbackground=self.colors['bg_tertiary'],
                           borderwidth=1,
                           relief='solid',
                           rowheight=25)
        
        self.style.configure('Modern.Treeview.Heading',
                           background=self.colors['bg_secondary'],
                           foreground=self.colors['text_primary'],
                           font=('Segoe UI', 9, 'bold'),
                           relief='flat',
                           borderwidth=1)
        
        self.style.map('Modern.Treeview',
                      background=[('selected', self.colors['accent']),
                                ('active', self.colors['bg_quaternary'])],
                      foreground=[('selected', self.colors['text_primary'])])
        
        self.style.map('Modern.Treeview.Heading',
                      background=[('active', self.colors['bg_quaternary'])])
        
        # Notebook styles
        self.style.configure('Modern.TNotebook',
                           background=self.colors['bg_primary'],
                           borderwidth=0,
                           tabmargins=[0, 0, 0, 0])
        
        self.style.configure('Modern.TNotebook.Tab',
                           background=self.colors['bg_secondary'],
                           foreground=self.colors['text_secondary'],
                           padding=(16, 10),
                           borderwidth=0,
                           font=('Segoe UI', 9))
        
        self.style.map('Modern.TNotebook.Tab',
                      background=[('selected', self.colors['accent']),
                                ('active', self.colors['bg_quaternary'])],
                      foreground=[('selected', self.colors['text_primary']),
                                ('active', self.colors['text_primary'])])
        
        # LabelFrame styles
        self.style.configure('Modern.TLabelframe',
                           background=self.colors['bg_secondary'],
                           foreground=self.colors['text_primary'],
                           borderwidth=1,
                           relief='solid')
        
        self.style.configure('Modern.TLabelframe.Label',
                           background=self.colors['bg_secondary'],
                           foreground=self.colors['text_primary'],
                           font=('Segoe UI', 9, 'bold'))
        
        # Spinbox styles
        self.style.configure('Modern.TSpinbox',
                           fieldbackground=self.colors['bg_tertiary'],
                           background=self.colors['bg_tertiary'],
                           foreground=self.colors['text_primary'],
                           borderwidth=1,
                           relief='solid',
                           focuscolor=self.colors['border_focus'])
        
        self.style.map('Modern.TSpinbox',
                      bordercolor=[('focus', self.colors['border_focus']),
                                  ('active', self.colors['border_hover'])])

    # ---------- Menu ----------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Add Files…", command=self._add_files)
        file_menu.add_command(label="Add Folder…", command=self._add_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Save Preset…", command=self._save_preset)
        file_menu.add_command(label="Load Preset…", command=self._load_preset)
        file_menu.add_separator()
        file_menu.add_command(label="Export Report…", command=self._export_report)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="FFmpeg Help", command=self._show_ffmpeg_help)
        # Add handy shortcuts to download the application and FFmpeg.  These
        # commands open the configured download links in the user's default
        # browser and display the built‑in EULA for quick reference.  A
        # dedicated download dialog with all available installers is
        # available via the "Download Links…" entry.
        help_menu.add_command(label="Download Links…", command=self._show_downloads)
        # Fast path to the product landing page.  Some users may want a
        # single click to reach the main site instead of picking a specific
        # installer.  This opens ``DOWNLOADS_LANDING_URL`` in the default
        # browser via the safe ``open_url`` helper.
        help_menu.add_command(label="Get Music Forge…",
                              command=lambda: open_url(DOWNLOADS_LANDING_URL))
        help_menu.add_command(label="Download FFmpeg…", command=lambda: open_ffmpeg_download_page())
        # Provide a friendly, step‑by‑step workflow for users who need help
        # installing FFmpeg.  This command opens the OS‑appropriate
        # download page, asks the user to pick a folder, and shows
        # guidance on extracting and locating the binary.  See
        # ``guided_ffmpeg_install`` for details.
        help_menu.add_command(label="Guided FFmpeg Install…", command=lambda: guided_ffmpeg_install())
        help_menu.add_command(label="View EULA…", command=lambda: messagebox.showinfo("EULA", _get_embedded_eula_text()))
        help_menu.add_command(label="About", command=self._show_about)
        # Add a quick FFmpeg status check with keyboard shortcut Ctrl+K
        help_menu.add_command(label="Check FFmpeg", command=self._check_ffmpeg_dialog, accelerator="Ctrl+K")
        self.bind_all("<Control-k>", lambda e: self._check_ffmpeg_dialog())
        help_menu.add_command(label="User Manual", command=self._show_manual)
        help_menu.add_command(label="Power Guide", command=self._show_power_guide)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    # ---------- Tabs ----------

    def _build_tabs(self) -> None:
        self.tabs = ttk.Notebook(self, style='Modern.TNotebook')
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)

        # Batch tab
        self.tab_batch = ttk.Frame(self.tabs, style='Card.TFrame')
        self.tabs.add(self.tab_batch, text="🎵 Batch Processor")

        ctrl = ttk.LabelFrame(self.tab_batch, text="⚙️ Processing Settings", style='Modern.TLabelframe')
        ctrl.pack(fill="x", padx=12, pady=12)

        # Row 1: format/quality/bitdepth
        row1 = ttk.Frame(ctrl, style='Card.TFrame')
        row1.pack(fill="x", padx=12, pady=8)
        ttk.Label(row1, text="Format:", style='Body.TLabel').pack(side="left")
        self.format_combo = ttk.Combobox(row1, textvariable=self.format_var, width=10, style='Modern.TCombobox',
                                         values=["wav","mp3","flac","aac","m4a","ogg"], state="readonly")
        self.format_combo.pack(side="left", padx=(4, 12))

        ttk.Label(row1, text="Quality:").pack(side="left")
        self.quality_combo = ttk.Combobox(row1, textvariable=self.quality_var, width=10,
                                          values=["V0","V1","V2","V3","V4","192k","224k","256k","320k","3","4","5","6","7","8","9","10"])
        self.quality_combo.pack(side="left", padx=(4, 12))

        ttk.Label(row1, text="Bit Depth (WAV):").pack(side="left")
        self.bit_depth_combo = ttk.Combobox(row1, textvariable=self.bit_depth_var, width=6, values=["16","24","32"], state="readonly")
        self.bit_depth_combo.pack(side="left", padx=(4, 12))

        # Row 2: sample rate, channels, overwrite, output dir
        row2 = ttk.Frame(ctrl); row2.pack(fill="x", padx=8, pady=4)
        ttk.Label(row2, text="Sample Rate (Hz):").pack(side="left")
        ttk.Entry(row2, textvariable=self.sample_rate_var, width=10).pack(side="left", padx=(4, 12))
        ttk.Label(row2, text="Channels:").pack(side="left")
        ttk.Spinbox(row2, from_=1, to=8, textvariable=self.channels_var, width=6).pack(side="left", padx=(4, 12))
        ttk.Checkbutton(row2, text="Overwrite existing", variable=self.overwrite_var).pack(side="left", padx=(4, 12))
        ttk.Label(row2, text="Output Folder:").pack(side="left")
        ttk.Entry(row2, textvariable=self.output_dir_var, width=44).pack(side="left", padx=4)
        ttk.Button(row2, text="Browse…", command=self._choose_output_dir).pack(side="left", padx=(6, 0))

        # Row 3: loudness, fades, parallelism, filename template
        row3 = ttk.Frame(ctrl); row3.pack(fill="x", padx=8, pady=4)
        ttk.Checkbutton(row3, text="Loudness normalize (EBU R128)", variable=self.normalize_var).pack(side="left")
        ttk.Label(row3, text="Mode:").pack(side="left", padx=(8,0))
        self.normalize_mode_combo = ttk.Combobox(row3, textvariable=self.normalize_mode_var, width=10,
                                                 values=["one-pass","two-pass"], state="readonly")
        self.normalize_mode_combo.pack(side="left", padx=(4, 12))
        ttk.Label(row3, text="I:").pack(side="left"); ttk.Entry(row3, textvariable=self.target_i_var, width=6).pack(side="left", padx=(0,8))
        ttk.Label(row3, text="TP:").pack(side="left"); ttk.Entry(row3, textvariable=self.target_tp_var, width=6).pack(side="left", padx=(0,8))
        ttk.Label(row3, text="LRA:").pack(side="left"); ttk.Entry(row3, textvariable=self.target_lra_var, width=6).pack(side="left", padx=(0,8))
        ttk.Label(row3, text="Fade in (s):").pack(side="left", padx=(12,0)); ttk.Entry(row3, textvariable=self.fade_in_var, width=6).pack(side="left")
        ttk.Label(row3, text="Fade out (s):").pack(side="left", padx=(6,0)); ttk.Entry(row3, textvariable=self.fade_out_var, width=6).pack(side="left")
        ttk.Label(row3, text="Parallel workers:").pack(side="left", padx=(12,0))
        workers_spinbox = ttk.Spinbox(row3, from_=1, to=max(1, os.cpu_count() or 4), textvariable=self.parallelism_var, width=6, style='Modern.TSpinbox')
        workers_spinbox.pack(side="left")
        # Add tooltip for two-pass worker capping
        def update_workers_info(*args: str) -> None:
            # Tooltip functionality removed - tkinter doesn't support tooltips natively
            # The worker capping logic is handled in the _dispatcher method
            pass
        self.normalize_var.trace_add('write', update_workers_info)
        self.normalize_mode_var.trace_add('write', update_workers_info)
        update_workers_info()
        ttk.Label(row3, text="Filename template:").pack(side="left", padx=(12,0)); ttk.Entry(row3, textvariable=self.template_var, width=40).pack(side="left")

        # Actions
        actions = ttk.Frame(self.tab_batch, style='Card.TFrame')
        actions.pack(fill="x", padx=12, pady=(0,12))
        ttk.Button(actions, text="📁 Add Files…", command=self._add_files, style='Secondary.TButton').pack(side="left", padx=(0,6))
        ttk.Button(actions, text="📂 Add Folder…", command=self._add_folder, style='Secondary.TButton').pack(side="left", padx=(0,6))
        ttk.Button(actions, text="🗑️ Clear", command=self._clear_queue, style='Secondary.TButton').pack(side="left", padx=(0,6))
        ttk.Button(actions, text="📊 Export Report…", command=self._export_report, style='Secondary.TButton').pack(side="left", padx=(0,12))
        ttk.Button(actions, text="▶️ Start", command=self._start_processing, style='Primary.TButton').pack(side="right", padx=(6,0))
        ttk.Button(actions, text="⏹️ Stop", command=self._stop_processing, style='Secondary.TButton').pack(side="right")

        # Treeview
        tv_wrap = ttk.Frame(self.tab_batch, style='Card.TFrame')
        tv_wrap.pack(fill="both", expand=True, padx=12, pady=(0,12))
        columns = ("format","duration","size","status","error","output")
        self.tree = ttk.Treeview(tv_wrap, columns=columns, show="headings", selectmode="extended", style='Modern.Treeview')
        for col, label, width in [
            ("format","Format",90), ("duration","Duration (s)",120), ("size","Size (MB)",100),
            ("status","Status",180), ("error","Error",440), ("output","Output",360)
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor="center" if col in {"format","duration","size","status"} else "w")
        yscroll = ttk.Scrollbar(tv_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set); self.tree.pack(side="left", fill="both", expand=True); yscroll.pack(side="left", fill="y")

        # Bottom bar
        bottom = ttk.Frame(self.tab_batch, style='Card.TFrame')
        bottom.pack(fill="x", padx=12, pady=(0,12))
        self.progress = ttk.Progressbar(bottom, mode="determinate", style='Modern.Horizontal.TProgressbar')
        self.progress.pack(side="left", fill="x", expand=True, padx=(0,12))
        self.ffmpeg_label = ttk.Label(bottom, text="FFmpeg: checking…", style='Body.TLabel')
        self.ffmpeg_label.pack(side="right")

        # Metadata tab
        self.tab_meta = ttk.Frame(self.tabs, style='Card.TFrame')
        self.tabs.add(self.tab_meta, text="🏷️ Metadata")
        meta = ttk.LabelFrame(self.tab_meta, text="🏷️ Tag Template", style='Modern.TLabelframe')
        meta.pack(fill="x", padx=12, pady=12)
        def ml(parent: tk.Widget, text: str, var: tk.StringVar) -> None: 
            row = ttk.Frame(parent); row.pack(fill="x", padx=8, pady=4)
            ttk.Label(row, text=text, width=12).pack(side="left")
            ttk.Entry(row, textvariable=var, width=60).pack(side="left", padx=(4,12))
        ml(meta, "Artist:", self.meta_artist)
        ml(meta, "Title:", self.meta_title)
        ml(meta, "Album:", self.meta_album)
        ml(meta, "Year:", self.meta_year)
        ml(meta, "Genre:", self.meta_genre)
        ml(meta, "Comment:", self.meta_comment)
        ttk.Label(meta, text="Placeholders: {stem}, {ext}, {index}, {artist}, {title}").pack(anchor="w", padx=16, pady=(0,8))

        # Presets tab
        self.tab_preset = ttk.Frame(self.tabs, style='Card.TFrame')
        self.tabs.add(self.tab_preset, text="⚙️ Presets")
        pr = ttk.LabelFrame(self.tab_preset, text="📦 Built‑in Presets", style='Modern.TLabelframe')
        pr.pack(fill="x", padx=12, pady=12)
        self.preset_list = tk.Listbox(pr, height=6); self.preset_list.pack(fill="x", padx=8, pady=8)
        for name in self.preset_mgr.list_builtin():
            self.preset_list.insert("end", name)
        ttk.Button(pr, text="Load Selected", command=self._load_builtin_preset).pack(padx=8, pady=(0,8))

        usr = ttk.LabelFrame(self.tab_preset, text="User Presets"); usr.pack(fill="x", padx=8, pady=8)
        self.user_preset_list = tk.Listbox(usr, height=6); self.user_preset_list.pack(fill="x", padx=8, pady=8)
        self._refresh_user_presets()
        btns = ttk.Frame(usr); btns.pack(fill="x", padx=8, pady=(0,8))
        ttk.Button(btns, text="Save Current as…", command=self._save_preset).pack(side="left")
        ttk.Button(btns, text="Load Selected", command=self._load_user_preset).pack(side="left", padx=(8,0))

        # Watch tab
        self.tab_watch = ttk.Frame(self.tabs, style='Card.TFrame')
        self.tabs.add(self.tab_watch, text="👁️ Folder Watch")
        watch = ttk.LabelFrame(self.tab_watch, text="👁️ Auto‑Ingest", style='Modern.TLabelframe')
        watch.pack(fill="x", padx=12, pady=12)
        self.watch_path_var = tk.StringVar(value="")
        self.poll_var = tk.IntVar(value=10)
        roww = ttk.Frame(watch); roww.pack(fill="x", padx=8, pady=4)
        ttk.Label(roww, text="Folder:").pack(side="left")
        ttk.Entry(roww, textvariable=self.watch_path_var, width=48).pack(side="left", padx=(4,8))
        ttk.Button(roww, text="Choose…", command=self._choose_watch_folder).pack(side="left")
        ttk.Label(roww, text="Poll (s):").pack(side="left", padx=(12,0))
        ttk.Spinbox(roww, from_=1, to=3600, textvariable=self.poll_var, width=6).pack(side="left", padx=(4,0))
        roww2 = ttk.Frame(watch); roww2.pack(fill="x", padx=8, pady=4)
        ttk.Button(roww2, text="Start Watch", command=self._start_watch).pack(side="left")
        ttk.Button(roww2, text="Stop Watch", command=self._stop_watch).pack(side="left", padx=(8,0))

        # Diagnostics tab
        self.tab_diag = ttk.Frame(self.tabs, style='Card.TFrame')
        self.tabs.add(self.tab_diag, text="🔧 Diagnostics")
        dtop = ttk.Frame(self.tab_diag); dtop.pack(fill="x", padx=8, pady=8)
        ttk.Button(dtop, text="Refresh FFmpeg Info", command=self._refresh_diag).pack(side="left")
        self.diag_text = tk.Text(self.tab_diag, wrap="word", height=20); self.diag_text.pack(fill="both", expand=True, padx=8, pady=(0,8))

        # Log tab
        self.tab_log = ttk.Frame(self.tabs, style='Card.TFrame')
        self.tabs.add(self.tab_log, text="📋 Log")
        self.log_text = tk.Text(self.tab_log, wrap="word", height=12); self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

    # ---------- Events / wire ----------

    def _wire_events(self) -> None:
        self.format_combo.bind("<<ComboboxSelected>>", lambda e: self._on_format_changed())

    # ---------- Helpers ----------

    def _choose_output_dir(self) -> None:
        d = filedialog.askdirectory(title="Choose Output Folder")
        if d: self.output_dir_var.set(d)

    def _choose_watch_folder(self) -> None:
        d = filedialog.askdirectory(title="Choose Watch Folder")
        if d: self.watch_path_var.set(d)

    def _add_files(self) -> None:
        types = [("Audio files", "*.wav *.mp3 *.flac *.aac *.m4a *.ogg *.aiff *.wma *.mka *.opus"), ("All files", "*.*")]
        files = filedialog.askopenfilenames(title="Add Audio Files", filetypes=types)
        if files: self._enqueue_files(files)

    def _add_folder(self) -> None:
        d = filedialog.askdirectory(title="Add Folder")
        if not d: return
        paths = []
        for root, _, filenames in os.walk(d):
            for fn in filenames:
                if Path(fn).suffix.lower() in AUDIO_EXTS:
                    paths.append(str(Path(root) / fn))
        self._enqueue_files(paths)

    def _clear_queue(self) -> None:
        self.audio_files.clear()
        self.tree.delete(*self.tree.get_children())
        self.progress["value"] = 0

    def _refresh_user_presets(self) -> None:
        self.user_preset_list.delete(0, "end")
        for name in self.preset_mgr.list_user_presets():
            self.user_preset_list.insert("end", name)

    def _enqueue_files(self, paths: Iterable[str]) -> None:
        added = 0
        for p in paths:
            p = str(Path(p))
            if not Path(p).exists(): continue
            st = os.stat(p)
            af = AudioFile(path=p, name=Path(p).name, size=int(st.st_size), format=(Path(p).suffix.lstrip(".") or "").lower())
            af.duration = FFMPEG.probe_duration(p)
            self.audio_files.append(af)
            self._add_tree_item(af)
            added += 1
        if added:
            self._log(f"Added {added} file(s) to queue.", "info")

    def _add_tree_item(self, af: AudioFile) -> None:
        self.tree.insert("", "end", iid=af.path, values=(
            af.format.upper(),
            f"{af.duration:.1f}" if af.duration else "",
            f"{af.size / (1024*1024):.1f}",
            af.status.value,
            af.error_message or "",
            af.output_path or "",
        ))

    # ---------- Processing ----------

    def _start_processing(self) -> None:
        self._stop_event.clear()
        self._sync_settings_from_ui()

        if not FFMPEG.is_available():
            messagebox.showerror("FFmpeg Missing", "FFmpeg/FFprobe not found.\nInstall from https://ffmpeg.org/download.html")
            return
        if not self.audio_files:
            messagebox.showinfo("No Files", "Add files to the queue first.")
            return

        # Reset statuses
        for af in self.audio_files:
            af.status = ProcessingStatus.QUEUED
            af.error_message = None
            af.output_path = None
            self._update_tree_row(af)

        # Spawn worker manager
        t = threading.Thread(target=self._dispatcher, daemon=True)
        t.start()
        self._threads.append(t)
        self._log("Started processing.", "info")

    def _dispatcher(self) -> None:
        work_q: "queue.Queue[AudioFile]" = queue.Queue()
        for af in self.audio_files:
            work_q.put(af)
        active: List[threading.Thread] = []

        def start_job():
            if work_q.empty(): return
            af = work_q.get()
            af.status = ProcessingStatus.PROCESSING
            self._update_tree_row(af)
            thread = threading.Thread(target=self._run_one, args=(af,), daemon=True)
            thread.start()
            active.append(thread)

        # Cap workers for two-pass mode to avoid oversubscription
        max_workers = self.settings.parallelism
        if (self.settings.normalize_loudness and 
            self.settings.normalize_mode == "two-pass"):
            max_workers = min(max_workers, max(1, (os.cpu_count() or 4) // 2))
        
        for _ in range(max_workers):
            start_job()

        while active:
            for t in list(active):
                if not t.is_alive():
                    active.remove(t)
                    if not work_q.empty() and not self._stop_event.is_set():
                        start_job()
            self._update_overall_progress()
            time.sleep(0.05)

        self._update_overall_progress(force_done=True)
        self._log("All processing finished.", "info")

    def _run_one(self, af: AudioFile) -> None:
        try:
            outp = self._output_path_for(af)
            if outp.exists() and not self.settings.overwrite_existing:
                af.status = ProcessingStatus.SKIPPED
                af.output_path = str(outp)
                af.error_message = "File exists, skipping"
                self._update_tree_row(af); return

            if str(outp.resolve()) == str(Path(af.path).resolve()):
                af.status = ProcessingStatus.FAILED
                af.error_message = "Would overwrite source; refusing to process"
                self._update_tree_row(af); return

            # Auto-rename if output would overwrite and overwrite is disabled
            if outp.exists() and not self.settings.overwrite_existing:
                base = outp.stem
                ext = outp.suffix
                counter = 1
                while outp.exists():
                    outp = outp.parent / f"{base}_{counter:03d}{ext}"
                    counter += 1
                af.output_path = str(outp)

            outp.parent.mkdir(parents=True, exist_ok=True)
            af.output_path = str(outp)

            def cb(kind: str, value: float) -> None:
                if kind == "progress":
                    self._update_tree_status_text(af, f"Processing {value:5.1f}%")

            ok, err = self.proc.process_file(af, self.settings, outp, progress_callback=cb, stop_event=self._stop_event)
            if ok:
                af.status = ProcessingStatus.COMPLETED
                af.error_message = None
            else:
                af.status = ProcessingStatus.SKIPPED if err == "Cancelled" else ProcessingStatus.FAILED
                af.error_message = err
            self._update_tree_row(af)
        except Exception as e:
            af.status = ProcessingStatus.FAILED
            af.error_message = str(e)
            self._update_tree_row(af)

    def _output_path_for(self, af: AudioFile) -> Path:
        ext = self.proc.format_to_extension(self.settings.output_format)
        src = Path(af.path)
        placeholders = {
            "stem": src.stem,
            "ext": ext,
            "index": 1,  # In GUI we don't guarantee stable indices; keep placeholder minimal
            "artist": self.meta_artist.get().format(stem=src.stem, ext=ext, index=1) if self.meta_artist.get() else "",
            "title": self.meta_title.get().format(stem=src.stem, ext=ext, index=1) if self.meta_title.get() else src.stem,
        }
        fname = self.template_var.get().format(**placeholders)
        outdir = Path(self.output_dir_var.get() or self.settings.output_directory or src.parent)
        return outdir / fname

    def _stop_processing(self) -> None:
        self._stop_event.set()
        self._log("Stop requested. Running jobs will finish or cancel shortly.", "warn")

    def _update_overall_progress(self, force_done: bool = False) -> None:
        total = len(self.audio_files)
        if total == 0:
            self.progress["value"] = 0; return
        if force_done:
            self.progress["value"] = 100; return
        done = sum(1 for af in self.audio_files if af.status == ProcessingStatus.COMPLETED)
        running = sum(1 for af in self.audio_files if af.status == ProcessingStatus.PROCESSING)
        pct = (done / total) * 100.0 + (running / total) * 15.0
        self.progress["value"] = min(100.0, pct)

    # ---------- Watch ----------

    def _start_watch(self) -> None:
        path = self.watch_path_var.get().strip()
        if not path:
            messagebox.showinfo("Watch", "Choose a folder to watch."); return
        folder = Path(path)
        if not folder.exists():
            messagebox.showerror("Watch", "Folder does not exist."); return
        if self._watcher:
            self._watcher.stop(); self._watcher = None
        self._watcher = FolderWatcher(folder, self.poll_var.get(), self._enqueue_files)
        self._watcher.start()
        self._log(f"Started watching: {folder} (poll {self.poll_var.get()}s)", "info")

    def _stop_watch(self) -> None:
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
            self._log("Stopped watching folder.", "info")

    # ---------- Diagnostics ----------

    def _check_ffmpeg(self) -> None:
        if FFMPEG.is_available():
            vi = FFMPEG.get_version_info()
            ver = vi.get("ffmpeg_version", "Ready")
            self.ffmpeg_label.config(text=f"FFmpeg {ver}", foreground="green")
        else:
            self.ffmpeg_label.config(text="FFmpeg Missing", foreground="red")
            self._show_ffmpeg_help()

    def _refresh_diag(self) -> None:
        if not FFMPEG.is_available():
            txt = "FFmpeg: Not Found\n\nInstall from https://ffmpeg.org/download.html"
        else:
            vi = FFMPEG.get_version_info()
            txt = (
                f"FFmpeg: {vi.get('ffmpeg_version','?')}\n"
                f"FFprobe: {vi.get('ffprobe_version','?')}\n"
                f"ffmpeg path: {vi.get('ffmpeg_path','?')}\n"
                f"ffprobe path: {vi.get('ffprobe_path','?')}\n"
            )
        self.diag_text.delete("1.0", "end")
        self.diag_text.insert("1.0", txt)

    def _show_ffmpeg_help(self) -> None:
        """
        Display a platform-aware prompt for installing FFmpeg.  This uses the
        ``FFMPEG_URLS`` dictionary to select the most appropriate download
        page for the user's operating system.  If detection fails, a
        generic URL is used.
        """
        try:
            import platform
            sysname = platform.system().lower()
            if "windows" in sysname:
                url = FFMPEG_URLS.get("windows", "https://ffmpeg.org/download.html")
            elif "darwin" in sysname or "mac" in sysname:
                url = FFMPEG_URLS.get("darwin", "https://ffmpeg.org/download.html")
            else:
                url = FFMPEG_URLS.get("linux", "https://ffmpeg.org/download.html")
        except Exception:
            url = "https://ffmpeg.org/download.html"
        messagebox.showinfo(
            "Install FFmpeg",
            "MusicForge requires FFmpeg and FFprobe.\n\n"
            f"Download from {url}\n"
            "After installation, restart MusicForge."
        )

    def _show_manual(self) -> None:
        win = tk.Toplevel(self); win.title("User Manual"); win.geometry("900x700")
        txt = tk.Text(win, wrap="word"); txt.pack(fill="both", expand=True); txt.insert("1.0", USER_MANUAL); txt.config(state="disabled")

    def _show_power_guide(self) -> None:
        win = tk.Toplevel(self); win.title("Power Guide"); win.geometry("900x700")
        txt = tk.Text(win, wrap="word")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", POWER_GUIDE + "\n\n" + COOKBOOK)
        txt.config(state="disabled")

    def _show_downloads(self) -> None:
        """
        Display a modal dialog presenting the user with links to download
        installers or packages for MusicForge Pro and related tools.  If
        tkinter is unavailable, this method falls back to simply
        opening the landing page in the default browser.  This helper
        replicates the behaviour of the standalone ``attach_downloads_ui``
        function but integrates cleanly into the application's existing
        menu system.
        """
        try:
            # If tkinter is unavailable (headless CLI or misconfigured
            # environment), open the generic landing page and return.
            if not tk_available:
                open_url(DOWNLOADS_LANDING_URL)
                return
            dlg = tk.Toplevel(self)
            dlg.title("Download MusicForge Pro")
            # Provide a modest default size; allow the window to resize
            dlg.geometry("480x300")
            frm = ttk.Frame(dlg, padding=12)
            frm.pack(fill="both", expand=True)
            ttk.Label(frm, text="Choose a download:", font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(0,6))
            # Create a row for each tuple in DOWNLOAD_LINKS.  Use a lambda
            # with a default argument to bind the current URL correctly.
            for label, url in DOWNLOAD_LINKS:
                row = ttk.Frame(frm)
                row.pack(fill="x", pady=2)
                ttk.Label(row, text=label).pack(side="left")
                ttk.Button(row, text="Open", command=lambda u=url: open_url(u)).pack(side="right")
            ttk.Button(frm, text="Close", command=dlg.destroy).pack(anchor="e", pady=(8,0))
        except Exception:
            # On any unexpected error, fall back to launching the landing
            # page so the user still has a way to obtain the software.
            try:
                open_url(DOWNLOADS_LANDING_URL)
            except Exception:
                pass

    def _show_about(self) -> None:
        messagebox.showinfo("About", f"{APP_NAME} {APP_VERSION}\n© iD01t Productions")

    # ---------- FFmpeg diagnostics ----------
    def _check_ffmpeg_dialog(self) -> None:
        """
        Show a simple dialog reporting whether FFmpeg and FFprobe are
        available, including version information if possible.  This
        method is bound to the Help menu and the Ctrl+K accelerator.
        """
        try:
            if FFMPEG.is_available():
                vi = FFMPEG.get_version_info()
                ver = vi.get("ffmpeg_version", "unknown")
                msg = (
                    f"FFmpeg is installed.\n"
                    f"Version: {ver}\n\n"
                    "Use the Diagnostics tab for more details."
                )
                messagebox.showinfo("FFmpeg", msg)
                # Update status bar to reflect that FFmpeg is present
                try:
                    self.set_status("FFmpeg detected")
                except Exception:
                    pass
            else:
                messagebox.showwarning(
                    "FFmpeg",
                    "FFmpeg/ffprobe were not found on your PATH.\n\n"
                    "Use 'Download FFmpeg…' from the toolbar or Help menu to install."
                )
                try:
                    self.set_status("FFmpeg not found")
                except Exception:
                    pass
        except Exception:
            # Fallback: generic error prompt
            try:
                messagebox.showwarning("FFmpeg", "Unable to determine FFmpeg status.")
            except Exception:
                pass

    def _startup_ffmpeg_check(self) -> None:
        """
        Prompt the user to install FFmpeg/FFprobe on first run if they
        are not currently available on the system.  This check is
        deferred via ``after`` to allow the main window to appear
        before any modal dialogs.  It runs once per session at app
        startup.

        This implementation delegates to the ``ensure_ffmpeg_present_or_prompt``
        helper, which encapsulates the platform check and user prompt.
        """
        try:
            # Use the shared helper to detect FFmpeg availability and
            # optionally prompt the user to download it.  Pass ``self`` as
            # the root so that message boxes appear relative to the main
            # window.  Ignore the boolean return value, since we only
            # care about prompting once at startup.
            ensure_ffmpeg_present_or_prompt(self)
        except Exception:
            # Silently ignore any errors during the startup check
            pass

    # ---------- Settings sync / presets ----------

    def _apply_settings_to_ui(self, s: ProcessingSettings) -> None:
        self.format_var.set(s.output_format); self.quality_var.set(s.quality)
        self.bit_depth_var.set(s.bit_depth); self.sample_rate_var.set(s.sample_rate)
        self.channels_var.set(s.channels); self.normalize_var.set(s.normalize_loudness)
        self.normalize_mode_var.set(s.normalize_mode); self.target_i_var.set(s.target_i)
        self.target_tp_var.set(s.target_tp); self.target_lra_var.set(s.target_lra)
        self.fade_in_var.set(s.fade_in_sec); self.fade_out_var.set(s.fade_out_sec)
        self.overwrite_var.set(s.overwrite_existing); self.output_dir_var.set(s.output_directory or "")
        self.parallelism_var.set(s.parallelism); self.template_var.set(s.filename_template)

        self.meta_artist.set(s.metadata.artist); self.meta_title.set(s.metadata.title)
        self.meta_album.set(s.metadata.album); self.meta_year.set(s.metadata.year)
        self.meta_genre.set(s.metadata.genre); self.meta_comment.set(s.metadata.comment)

        self._on_format_changed()

    def _sync_settings_from_ui(self) -> None:
        self.settings.output_format = self.format_var.get().lower()
        self.settings.quality = self.quality_var.get()
        
        # Validate bit depth
        bit_depth = int(self.bit_depth_var.get() or 16)
        if bit_depth not in {16, 24, 32}:
            bit_depth = 16
        self.settings.bit_depth = bit_depth
        
        # Validate sample rate
        sample_rate = int(self.sample_rate_var.get() or 48000)
        if sample_rate <= 0 or sample_rate > 192000:
            sample_rate = 48000
        self.settings.sample_rate = sample_rate
        
        # Validate channels
        channels = int(self.channels_var.get() or 2)
        if channels < 1 or channels > 8:
            channels = 2
        self.settings.channels = channels
        self.settings.normalize_loudness = bool(self.normalize_var.get())
        self.settings.normalize_mode = self.normalize_mode_var.get()
        self.settings.target_i = float(self.target_i_var.get())
        self.settings.target_tp = float(self.target_tp_var.get())
        self.settings.target_lra = float(self.target_lra_var.get())
        self.settings.fade_in_sec = float(self.fade_in_var.get() or 0)
        self.settings.fade_out_sec = float(self.fade_out_var.get() or 0)
        self.settings.overwrite_existing = bool(self.overwrite_var.get())
        self.settings.output_directory = self.output_dir_var.get() or None
        self.settings.parallelism = max(1, int(self.parallelism_var.get() or 1))
        self.settings.filename_template = self.template_var.get()

        self.settings.metadata = MetadataTemplate(
            artist=self.meta_artist.get(), title=self.meta_title.get(),
            album=self.meta_album.get(), year=self.meta_year.get(),
            genre=self.meta_genre.get(), comment=self.meta_comment.get()
        )

        # Persist session
        try:
            self.session.save(self.settings, geometry=self.geometry())
        except Exception:
            pass

    def _load_builtin_preset(self) -> None:
        sel: Tuple[int, ...] = self.preset_list.curselection()
        if not sel: return
        name: str = self.preset_list.get(sel[0])
        s = self.preset_mgr.load_builtin(name)
        self._apply_settings_to_ui(s)
        self.settings = s
        self._log(f"Loaded preset: {name}", "info")

    def _save_preset(self) -> None:
        name: Optional[str] = self._prompt("Preset Name", "Enter a name for this preset:")
        if not name: return
        self._sync_settings_from_ui()
        try:
            path = self.preset_mgr.save_user_preset(name, self.settings)
            self._refresh_user_presets()
            self._log(f"Preset saved: {path}", "info")
        except Exception as e:
            messagebox.showerror("Preset Error", str(e))

    def _load_preset(self) -> None:
        self._load_user_preset()

    def _load_user_preset(self) -> None:
        sel: Tuple[int, ...] = self.user_preset_list.curselection()
        if not sel:
            messagebox.showinfo("Presets", "Select a user preset to load."); return
        name: str = self.user_preset_list.get(sel[0])
        try:
            s = self.preset_mgr.load_user_preset(name)
            self._apply_settings_to_ui(s); self.settings = s
            self._log(f"Loaded user preset: {name}", "info")
        except Exception as e:
            messagebox.showerror("Preset Error", str(e))

    # ---------- Logging ----------

    def _log(self, msg: str, level: str = "info") -> None:
        self._log_queue.put((level, msg))
        try:
            with self._log_lock, open(LOG_FILE, "a", encoding="utf-8") as fp:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                fp.write(f"[{ts}] {level.upper()}: {msg}\n")
        except Exception:
            pass

    def _drain_log_queue(self) -> None:
        try:
            while True:
                level, msg = self._log_queue.get_nowait()
                ts = datetime.now().strftime("%H:%M:%S")
                self.log_text.insert("end", f"[{ts}] {level.upper()}: {msg}\n")
                self.log_text.see("end")
        except queue.Empty:
            pass
        finally:
            self.after(120, self._drain_log_queue)

    # ---------- Tree helpers ----------

    def _update_tree_row(self, af: AudioFile) -> None:
        if self.tree.exists(af.path):
            self.tree.item(af.path, values=(
                af.format.upper(),
                f"{af.duration:.1f}" if af.duration else "",
                f"{af.size / (1024*1024):.1f}",
                af.status.value,
                af.error_message or "",
                af.output_path or "",
            ))

    def _update_tree_status_text(self, af: AudioFile, text_status: str) -> None:
        if self.tree.exists(af.path):
            vals = list(self.tree.item(af.path, "values"))
            vals[3] = text_status
            self.tree.item(af.path, values=tuple(vals))

    # ---------- Misc ----------

    def _on_format_changed(self) -> None:
        fmt = self.format_var.get().lower()
        if fmt == "mp3":
            self.quality_combo.configure(values=["V0","V1","V2","V3","V4"])
            if self.quality_var.get() not in {"V0","V1","V2","V3","V4"}:
                self.quality_var.set("V2")
        elif fmt in {"aac","m4a"}:
            self.quality_combo.configure(values=["192k","224k","256k","320k"])
            if not str(self.quality_var.get()).endswith("k"):
                self.quality_var.set("256k")
        elif fmt == "ogg":
            self.quality_combo.configure(values=[str(i) for i in range(0,11)])
            if self.quality_var.get() not in {str(i) for i in range(0,11)}:
                self.quality_var.set("6")
        elif fmt == "opus":
            self.quality_combo.configure(values=["64k","96k","128k","160k","192k","256k","320k"])
            if not str(self.quality_var.get()).endswith("k"):
                self.quality_var.set("128k")
        else:
            self.quality_combo.configure(values=[])
        self.bit_depth_combo.configure(state="readonly" if fmt == "wav" else "disabled")

    def _export_report(self) -> None:
        try:
            outdir = Path(self.output_dir_var.get() or self.settings.output_directory or Path.home())
            outdir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report = outdir / f"MusicForge_Report_{ts}.csv"
            with open(report, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["File","Format","Size (MB)","Duration (s)","Status","Error","Output","Bitrate","Sample Rate","Channels","LUFS","True Peak","Encoder","Warnings"])
                for af in self.audio_files:
                    # Enhanced metadata for GUI reports
                    bitrate = "N/A"
                    sample_rate = str(self.settings.sample_rate) if self.settings.sample_rate else "N/A"
                    channels = str(self.settings.channels) if self.settings.channels else "N/A"
                    lufs = f"{af.measured_loudness.get('input_i', 'N/A'):.1f}" if af.measured_loudness else "N/A"
                    true_peak = f"{af.measured_loudness.get('input_tp', 'N/A'):.1f}" if af.measured_loudness else "N/A"
                    encoder = "libfdk_aac" if self.settings.output_format in ["aac", "m4a"] and FFMPEG.libfdk_aac_available else self.settings.output_format
                    warnings = "Two-pass fallback" if self.settings.normalize_mode == "two-pass" and not af.measured_loudness else ""
                    
                    w.writerow([af.name, af.format.upper(), f"{af.size/(1024*1024):.1f}", f"{af.duration:.1f}" if af.duration else "", af.status.value, af.error_message or "", af.output_path or "", bitrate, sample_rate, channels, lufs, true_peak, encoder, warnings])
            messagebox.showinfo("Report Exported", f"Saved to:\n{report}")
            self._log(f"Report exported: {report}", "info")
        except Exception as e:
            self._log(f"Failed to export report: {e}", "error")
            messagebox.showerror("Export Error", str(e))

    def _prompt(self, title: str, message: str) -> Optional[str]:
        _ensure_tkinter()
        win = tk.Toplevel(self); win.title(title); win.transient(self); win.grab_set()
        ttk.Label(win, text=message).pack(padx=12, pady=12)
        var = tk.StringVar(value="")
        ttk.Entry(win, textvariable=var, width=40).pack(padx=12, pady=(0,12))
        btns = ttk.Frame(win); btns.pack(padx=12, pady=(0,12))
        out = {"val": None}
        def ok():
            out["val"] = var.get().strip(); win.destroy()
        def cancel():
            out["val"] = None; win.destroy()
        ttk.Button(btns, text="OK", command=ok).pack(side="left", padx=(0,6))
        ttk.Button(btns, text="Cancel", command=cancel).pack(side="left")
        self.wait_window(win)
        return out["val"]

    def _on_quit(self) -> None:
        if any(af.status == ProcessingStatus.PROCESSING for af in self.audio_files):
            if not messagebox.askyesno("Quit", "Processing is still running. Quit anyway?"):
                return
        try:
            self.session.save(self.settings, geometry=self.geometry())
        except Exception:
            pass
        self.destroy()


# ======================================================================================
# Entrypoints
# ======================================================================================

def gui_main() -> int:
    if not tk_available:
        print("Tkinter is not available in this environment. Use CLI mode.")
        return 2
    app = MusicForgeApp()
    app.mainloop()
    return 0


def main() -> int:
    """
    Determine whether to run the GUI or CLI based on the provided
    command‑line arguments.  By default, if no input/output or other
    CLI‑specific flags are provided and Tkinter is available, the GUI
    will be launched.  Users can explicitly request the GUI with
    ``--gui`` or force CLI mode by providing any CLI options.
    """
    # Extract argument list (excluding the script name)
    argv = sys.argv[1:]
    # If the user explicitly requested the GUI via --gui, launch it
    if '--gui' in argv:
        return gui_main()
    # Perform a lightweight parse to check for CLI inputs
    try:
        parser = build_cli_parser()
        # Use parse_known_args so that unrecognized options do not cause an
        # early exit; unrecognized options will still be passed to cli_main.
        args, unknown = parser.parse_known_args(argv)
        # If there is no input/output specified and no other CLI‑specific
        # actions were requested (like manual, power_guide, preset_list,
        # test_progress, dry_run or report), then default to launching
        # the GUI when Tkinter is available.
        no_cli_params = not any([
            getattr(args, 'input', None),
            getattr(args, 'output', None),
            getattr(args, 'manual', False),
            getattr(args, 'power_guide', False),
            getattr(args, 'preset_list', False),
            getattr(args, 'test_progress', False),
            getattr(args, 'dry_run', False),
            getattr(args, 'report', None),
            getattr(args, 'preset', None),
            getattr(args, 'watch', None),
            getattr(args, 'meta', None),
        ])
        if no_cli_params and tk_available:
            return gui_main()
    except SystemExit:
        # If the parser attempted to exit (e.g. due to -h/--help), rethrow
        raise
    except Exception:
        # Fall back to CLI if parsing fails
        pass
    # Otherwise, run the CLI with the provided arguments
    return cli_main(argv)


if __name__ == "__main__":
    # EULA acceptance gate: perform a lightweight parse for --accept-eula
    # before handing off to the full CLI parser.  If acceptance fails,
    # terminate the program immediately.  This ensures that the EULA
    # prompt appears before any processing or GUI construction.
    try:
        import argparse as _argp
        _cli = _argp.ArgumentParser(add_help=False)
        _cli.add_argument("--accept-eula", action="store_true")
        _known, _ = _cli.parse_known_args()
        if not ensure_eula_accepted(cli_accept=_known.accept_eula):
            raise SystemExit("EULA not accepted. Exiting.")
    except Exception:
        pass
    # Delegate to the main entrypoint and exit with its return code
    sys.exit(main())
