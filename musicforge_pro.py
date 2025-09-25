#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MusicForge Pro — Single-File Edition
Minimal-yet-practical batch audio utility using FFmpeg/FFprobe.
Includes: CLI + simple Tk GUI, EULA acceptance, two-pass loudnorm,
templated metadata/filenames, CSV reports, folder watch, and logging.

Dependencies: Only the Python stdlib. Requires FFmpeg + FFprobe on PATH.
License: © iD01t Productions
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import platform
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

APP_NAME = "MusicForge Pro"
APP_VERSION = "1.0.0"
LOG_FILE = Path.home() / ".musicforge_pro.log"
SESSION_FILE = Path.home() / ".musicforge_pro_session.json"
EULA_TEXT_FILE = Path.home() / ".musicforge_pro_eula.txt"
EULA_ACCEPT_FLAG = Path.home() / ".musicforge_pro_eula.accepted"

DOWNLOADS_BASE = "https://id01t.store"
DOWNLOADS_LANDING_URL = f"{DOWNLOADS_BASE}/musicforge"
FFMPEG_URLS = {
    "windows": "https://ffmpeg.org/download.html#build-windows",
    "darwin": "https://ffmpeg.org/download.html#build-mac",
    "linux": "https://ffmpeg.org/download.html#build-linux",
}

# ------------------------- Logging ---------------------------------
def _setup_logging() -> None:
    try:
        logging.basicConfig(
            filename=str(LOG_FILE),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    except Exception:
        # As a last resort, log to stderr
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)
_setup_logging()
logging.info("%s v%s starting", APP_NAME, APP_VERSION)

# ------------------------- Utilities -------------------------------
def print_err(msg: str) -> None:
    try:
        sys.stderr.write(msg + "\n")
    except Exception:
        pass

def open_url(url: str) -> None:
    try:
        import webbrowser
        if not webbrowser.open(url, new=2):
            raise RuntimeError("webbrowser.open returned False")
    except Exception as e:
        logging.warning("open_url failed: %s", e)
        print(f"Open this link in your browser:\n{url}")

def open_ffmpeg_download_page() -> None:
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
        logging.exception("open_ffmpeg_download_page failed: %s", e)
        open_url("https://ffmpeg.org/download.html")

def ensure_eula_accepted(cli_accept: bool=False) -> bool:
    if EULA_ACCEPT_FLAG.exists():
        return True
    eula = f"""MusicForge Pro — EULA (v{APP_VERSION})

IMPORTANT—READ CAREFULLY: By installing or using this software, you agree to the terms.
The Software is provided “AS IS” without warranty. You are responsible for
complying with FFmpeg and any third-party licenses.

By proceeding, you acknowledge these terms.
"""
    try:
        EULA_TEXT_FILE.write_text(eula, encoding="utf-8")
    except Exception:
        pass

    if cli_accept or not _tk_available():
        # headless acceptance (CI/CLI), write flag best-effort
        try:
            EULA_ACCEPT_FLAG.write_text("accepted\n", encoding="utf-8")
        except Exception:
            pass
        return True

    # GUI modal
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
        root = tk.Tk(); root.withdraw()
        dlg = tk.Toplevel(root); dlg.title("End User License Agreement")
        dlg.geometry("700x500")
        frm = ttk.Frame(dlg, padding=12); frm.pack(fill="both", expand=True)
        txt = tk.Text(frm, wrap="word"); txt.pack(fill="both", expand=True)
        txt.insert("1.0", eula); txt.configure(state="disabled")
        agreed = {"ok": False}
        btns = ttk.Frame(frm); btns.pack(fill="x", pady=(8,0))
        def _ok(): agreed["ok"] = True; dlg.destroy()
        def _cancel(): dlg.destroy()
        ttk.Button(btns, text="I Agree", command=_ok).pack(side="right", padx=6)
        ttk.Button(btns, text="Cancel", command=_cancel).pack(side="right")
        dlg.transient(root); dlg.grab_set(); root.wait_window(dlg); root.destroy()
        if agreed["ok"]:
            try: EULA_ACCEPT_FLAG.write_text("accepted\n", encoding="utf-8")
            except Exception: pass
            return True
        return False
    except Exception:
        # Non-blocking fallback
        try: EULA_ACCEPT_FLAG.write_text("accepted\n", encoding="utf-8")
        except Exception: pass
        return True

def _tk_available() -> bool:
    try:
        import tkinter
        return True
    except Exception:
        return False

# ------------------------- FFmpeg Manager --------------------------
class FFmpegManager:
    def __init__(self) -> None:
        self.ffmpeg = shutil.which("ffmpeg") or ""
        self.ffprobe = shutil.which("ffprobe") or ""

    def is_available(self) -> bool:
        return bool(self.ffmpeg and self.ffprobe)

    def version(self) -> str:
        if not self.ffmpeg:
            return "ffmpeg: not found"
        try:
            out = subprocess.run([self.ffmpeg, "-version"], capture_output=True, text=True, check=False)
            return out.stdout.splitlines()[0] if out.stdout else "unknown"
        except Exception as e:
            logging.warning("ffmpeg version failed: %s", e)
            return "unknown"

    def probe_duration(self, path: Path) -> float:
        if not self.ffprobe:
            return 0.0
        try:
            cmd = [
                self.ffprobe, "-v", "error", "-show_entries", "format=duration",
                "-of", "json", str(path)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            data = json.loads(res.stdout or "{}")
            dur = float(data.get("format", {}).get("duration", 0) or 0)
            return max(0.0, dur)
        except Exception as e:
            logging.warning("probe_duration failed for %s: %s", path, e)
            return 0.0

    def run(self, args: List[str], env: Optional[Dict[str,str]]=None) -> Tuple[int, str, str]:
        """Run ffmpeg and return (rc, stdout, stderr). Adds -nostdin for safety."""
        if not self.ffmpeg:
            return 1, "", "ffmpeg not found"
        cmd = [self.ffmpeg] + args
        if "-nostdin" not in cmd:
            cmd.insert(1, "-nostdin")
        logging.info("Running: %s", " ".join(cmd))
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
            return proc.returncode, proc.stdout, proc.stderr
        except KeyboardInterrupt:
            return 130, "", "Interrupted"
        except Exception as e:
            logging.exception("ffmpeg run failed: %s", e)
            return 1, "", str(e)

FFMPEG = FFmpegManager()

# ------------------------- Data Models -----------------------------
def _safe_template_map(extras: Optional[Dict[str, str]]=None) -> defaultdict:
    base = defaultdict(str)
    if extras:
        base.update({k: str(v) for k, v in extras.items()})
    return base

@dataclass
class MetadataTemplate:
    artist: str = "{artist}"
    title: str = "{stem}"
    album: str = ""
    year: str = ""
    genre: str = ""
    comment: str = ""

    def to_args(self, placeholders: Dict[str, str]) -> List[str]:
        mp = _safe_template_map(placeholders)
        meta = {
            "artist": self.artist.format_map(mp),
            "title": self.title.format_map(mp),
            "album": self.album.format_map(mp),
            "date": self.year.format_map(mp),
            "genre": self.genre.format_map(mp),
            "comment": self.comment.format_map(mp),
        }
        args: List[str] = []
        for k, v in meta.items():
            if v:
                args += ["-metadata", f"{k}={v}"]
        return args

@dataclass
class ProcessingSettings:
    fmt: str = "wav"
    quality: str = ""
    bit_depth: int = 24
    sr: int = 48000
    ch: int = 2
    normalize: bool = False
    lufs: float = -16.0
    tp: float = -1.5
    lra: float = 11.0
    two_pass: bool = True
    fade_in: float = 0.0
    fade_out: float = 0.0
    overwrite: bool = False
    metadata: MetadataTemplate = field(default_factory=MetadataTemplate)

    def validate(self) -> None:
        if self.fmt not in {"wav","mp3","flac","m4a","aac","ogg","opus"}:
            raise ValueError("--format must be one of wav/mp3/flac/m4a/aac/ogg/opus")
        if self.bit_depth not in (16,24,32):
            raise ValueError("--bit-depth must be 16/24/32")
        if self.sr not in (22050,32000,44100,48000,88200,96000):
            raise ValueError("--sr invalid")
        if not (1 <= self.ch <= 8):
            raise ValueError("--ch must be 1..8")
        if self.normalize:
            if not (-36.0 <= self.lufs <= -8.0):
                raise ValueError("--lufs must be between -36 and -8")
            if self.tp > -1.0:
                raise ValueError("--tp must be <= -1.0 dBTP")
            if self.lra < 0.0:
                raise ValueError("--lra must be >= 0")

# ------------------------- Helpers --------------------------------
AUDIO_EXTS = {".wav",".mp3",".flac",".m4a",".aac",".ogg",".opus",".aiff",".aif",".wma",".mka"}

def discover_inputs(path: Path) -> List[Path]:
    files: List[Path] = []
    if path.is_file():
        if path.suffix.lower() in AUDIO_EXTS:
            files.append(path)
        return files
    for p in path.rglob("*"):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            files.append(p)
    return files

def hard_guard_samefile(src: Path, dst: Path, overwrite: bool) -> Tuple[bool, str]:
    try:
        if dst.exists() and not overwrite:
            return False, "exists"
        try:
            if os.path.samefile(src, dst):
                return False, "Refusing to overwrite source; adjust output/template."
        except FileNotFoundError:
            pass
        return True, ""
    except Exception as e:
        return False, f"filesystem check failed: {e}"

def ensure_progress_flags(args: List[str]) -> List[str]:
    text = " " + " ".join(args) + " "
    if " -progress " not in text:
        args += ["-progress","pipe:1","-nostats","-v","error"]
    return args

def format_specific_args(s: ProcessingSettings) -> List[str]:
    a: List[str] = []
    if s.fmt == "wav":
        if s.bit_depth == 16:
            a += ["-c:a","pcm_s16le"]
        elif s.bit_depth == 24:
            a += ["-c:a","pcm_s24le"]
        else:
            a += ["-c:a","pcm_s32le"]
    elif s.fmt == "mp3":
        if s.quality and s.quality.upper().startswith("V"):
            a += ["-q:a", s.quality[1:]]
        else:
            a += ["-q:a", "2"]
        a += ["-c:a","libmp3lame"]
    elif s.fmt in {"m4a","aac"}:
        a += ["-c:a","aac"]
        if s.quality:
            a += ["-b:a", s.quality]
        else:
            a += ["-b:a","192k"]
    elif s.fmt == "flac":
        a += ["-c:a","flac"]
    elif s.fmt == "ogg":
        a += ["-c:a","libvorbis"]
        a += ["-q:a", "5"] if not s.quality else ["-b:a", s.quality]
    elif s.fmt == "opus":
        a += ["-c:a","libopus"]
        a += ["-b:a", s.quality or "160k"]
    return a

def build_filters(s: ProcessingSettings) -> str:
    af: List[str] = []
    if s.fade_in > 0:
        af.append(f"afade=t=in:st=0:d={s.fade_in}")
    if s.fade_out > 0:
        af.append(f"afade=t=out:st=0:d={s.fade_out}")
    if s.normalize:
        af.append(f"loudnorm=I={s.lufs}:TP={s.tp}:LRA={s.lra}:print_format=json")
    return ",".join([a for a in af if a])

def safe_out_name(src: Path, out_dir: Path, template: str, idx: int, s: ProcessingSettings) -> Path:
    stem = src.stem
    ext = s.fmt if s.fmt != "m4a" else "m4a"
    mp = _safe_template_map({
        "stem": stem,
        "ext": ext,
        "index": f"{idx:02d}",
        "artist": "", "title": stem,
    })
    name = (template or "{stem}.{ext}").format_map(mp)
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    return out_dir / name

# ------------------------- Processor -------------------------------
class AudioProcessor:
    def __init__(self, settings: ProcessingSettings, out_dir: Path, template: str) -> None:
        self.s = settings
        self.out_dir = out_dir
        self.template = template
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _loudnorm_measure(self, src: Path) -> Optional[Dict[str, float]]:
        args = ["-i", str(src), "-af", f"loudnorm=I={self.s.lufs}:TP={self.s.tp}:LRA={self.s.lra}:print_format=json", "-f", "null", "-"]
        rc, out, err = FFMPEG.run(args)
        text = out + "\n" + err
        m = re.search(r"\{\s*\"input_i\".*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
            return {
                "measured_I": float(data.get("input_i", 0)),
                "measured_TP": float(data.get("input_tp", 0)),
                "measured_LRA": float(data.get("input_lra", 0)),
                "measured_thresh": float(data.get("input_thresh", 0)),
                "offset": float(data.get("target_offset", 0)),
            }
        except Exception as e:
            logging.warning("loudnorm measure parse failed: %s", e)
            return None

    def process_one(self, src: Path, dst: Path) -> Tuple[str, str, float]:
        start = time.time()
        ok, why = hard_guard_samefile(src, dst, self.s.overwrite)
        if not ok:
            return "skip", why, 0.0
        self.s.validate()

        base_args = ["-y" if self.s.overwrite else "-n", "-i", str(src)]
        base_args += ["-ar", str(self.s.sr), "-ac", str(self.s.ch)]
        meta_placeholders = {"stem": src.stem, "ext": dst.suffix.lstrip("."), "artist":"", "title": src.stem}
        base_args += self.s.metadata.to_args(meta_placeholders)

        filters = []
        if self.s.fade_in > 0:
            filters.append(f"afade=t=in:st=0:d={self.s.fade_in}")
        if self.s.fade_out > 0:
            filters.append(f"afade=t=out:st=0:d={self.s.fade_out}")
        if self.s.normalize and self.s.two_pass:
            meas = self._loudnorm_measure(src)
            if meas:
                filters.append(
                    "loudnorm="
                    f"I={self.s.lufs}:TP={self.s.tp}:LRA={self.s.lra}:"
                    f"measured_I={meas['measured_I']}:measured_TP={meas['measured_TP']}:"
                    f"measured_LRA={meas['measured_LRA']}:measured_thresh={meas['measured_thresh']}:"
                    f"offset={meas['offset']}:linear=true:print_format=summary"
                )
            else:
                logging.warning("Two-pass measure failed; falling back to one-pass.")
                filters.append(f"loudnorm=I={self.s.lufs}:TP={self.s.tp}:LRA={self.s.lra}")
        elif self.s.normalize:
            filters.append(f"loudnorm=I={self.s.lufs}:TP={self.s.tp}:LRA={self.s.lra}")

        if filters:
            base_args += ["-af", ",".join(filters)]

        base_args += format_specific_args(self.s)
        base_args = ensure_progress_flags(base_args)
        base_args += [str(dst)]

        rc, out, err = FFMPEG.run(base_args)
        dur = FFMPEG.probe_duration(dst) if rc == 0 else 0.0
        elapsed = time.time() - start
        if rc == 0 and dur > 0:
            return "ok", f"done in {elapsed:.1f}s", dur
        return "error", (err.strip() or "ffmpeg failed"), 0.0

# ------------------------- CSV Report ------------------------------
def write_csv_report(rows: List[Dict[str, str]], path: Path) -> None:
    if not rows:
        return
    keys = ["source","dest","status","message","seconds"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k,"") for k in keys})

# ------------------------- Session --------------------------------
def save_session(d: Dict) -> None:
    try:
        SESSION_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8")
    except Exception as e:
        logging.warning("save_session failed: %s", e)

def load_session() -> Dict:
    try:
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

# ------------------------- CLI ------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="musicforge_pro", description=f"{APP_NAME} v{APP_VERSION}")
    p.add_argument("-i","--input", help="Input file or folder", required=False)
    p.add_argument("-o","--output", help="Output folder", required=False)
    p.add_argument("-f","--format", dest="fmt", default="wav", help="Output format (wav/mp3/flac/m4a/aac/ogg/opus)")
    p.add_argument("--quality", default="", help="Format quality (e.g., V2 for mp3, 192k for aac/opus)")
    p.add_argument("--bit-depth", type=int, default=24, help="Bit depth for WAV (16/24/32)")
    p.add_argument("--sr", type=int, default=48000, help="Sample rate")
    p.add_argument("--ch", type=int, default=2, help="Channels 1..8")
    p.add_argument("--normalize", action="store_true", help="Enable loudness normalization (EBU R128)")
    p.add_argument("--two-pass", action="store_true", help="Use two-pass loudnorm (more accurate)")
    p.add_argument("--lufs", type=float, default=-16.0, help="Target LUFS")
    p.add_argument("--tp", type=float, default=-1.5, help="True peak (dBTP) <= -1.0")
    p.add_argument("--lra", type=float, default=11.0, help="Loudness range (LU)")
    p.add_argument("--fade-in", type=float, default=0.0, help="Seconds fade in")
    p.add_argument("--fade-out", type=float, default=0.0, help="Seconds fade out")
    p.add_argument("--template", default="{stem}.{ext}", help="Filename template with placeholders")
    p.add_argument("--overwrite", action="store_true", help="Overwrite outputs when possible")
    p.add_argument("--report", default="", help="Write CSV report to this file")
    p.add_argument("--watch", default="", help="Watch this folder for new files")
    p.add_argument("--poll", type=int, default=10, help="Polling seconds for --watch")
    p.add_argument("--accept-eula", action="store_true", help="Auto-accept EULA (headless)")
    p.add_argument("--gui", action="store_true", help="Force GUI launch")
    p.add_argument("--manual", action="store_true", help="Print user manual and exit")
    return p

USER_MANUAL = """\
MUSICFORGE PRO — USER MANUAL (CONDENSED)
1) Install FFmpeg & FFprobe; ensure they are on PATH.
2) CLI: musicforge_pro.py -i IN -o OUT -f mp3 --normalize --two-pass
3) GUI: python musicforge_pro.py --gui
Placeholders: {stem} {ext} {index} {artist} {title}
"""

def cli_main(argv: Optional[List[str]]=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = build_parser()
    args = p.parse_args(argv)

    if args.manual:
        print(USER_MANUAL); return 0

    if args.gui or (not args.input and not args.watch):
        return gui_main(args)

    if not ensure_eula_accepted(cli_accept=args.accept_eula):
        print_err("EULA not accepted."); return 2

    if not FFMPEG.is_available():
        print_err("FFmpeg/ffprobe not found on PATH.")
        open_ffmpeg_download_page()
        return 2

    if not args.output:
        print_err("--output folder is required"); return 2
    out_dir = Path(args.output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    s = ProcessingSettings(
        fmt=args.fmt, quality=args.quality, bit_depth=args.bit_depth, sr=args.sr, ch=args.ch,
        normalize=bool(args.normalize), lufs=args.lufs, tp=args.tp, lra=args.lra,
        two_pass=bool(args.two_pass), fade_in=args.fade_in, fade_out=args.fade_out,
        overwrite=bool(args.overwrite),
    )

    files: List[Path] = []
    if args.input:
        ip = Path(args.input).expanduser().resolve()
        if not ip.exists():
            print_err(f"Input path not found: {ip}"); return 2
        files = discover_inputs(ip)

    rows: List[Dict[str,str]] = []
    if args.watch:
        watch_dir = Path(args.watch).expanduser().resolve()
        if not watch_dir.exists() or not watch_dir.is_dir():
            print_err(f"--watch path is invalid: {watch_dir}"); return 2
        seen: set = set()
        idx = 1
        try:
            print(f"Watching {watch_dir} every {args.poll}s … Ctrl+C to stop.")
            while True:
                new_files = [p for p in discover_inputs(watch_dir) if str(p) not in seen]
                for src in new_files:
                    seen.add(str(src))
                    dst = safe_out_name(src, out_dir, args.template, idx, s)
                    status, message, seconds = AudioProcessor(s, out_dir, args.template).process_one(src, dst)
                    rows.append({"source": str(src), "dest": str(dst), "status": status, "message": message, "seconds": f"{seconds:.2f}"})
                    print(f"[{status}] {src.name} -> {dst.name} — {message}")
                    idx += 1
                if args.report:
                    try: write_csv_report(rows, Path(args.report))
                    except Exception: pass
                time.sleep(max(1, int(args.poll)))
        except KeyboardInterrupt:
            pass
    else:
        if not files:
            print_err("No input files found."); return 2
        proc = AudioProcessor(s, out_dir, args.template)
        for i, src in enumerate(files, 1):
            dst = safe_out_name(src, out_dir, args.template, i, s)
            status, message, seconds = proc.process_one(src, dst)
            rows.append({"source": str(src), "dest": str(dst), "status": status, "message": message, "seconds": f"{seconds:.2f}"})
            print(f"[{status}] {src.name} -> {dst.name} — {message}")

    if args.report:
        try:
            write_csv_report(rows, Path(args.report))
            print(f"Report written to {args.report}")
        except Exception as e:
            print_err(f"Failed to write report: {e}")

    save_session({"last_args": vars(args)})
    return 0

# ------------------------- GUI (Tk) --------------------------------
def gui_main(ns) -> int:
    if not _tk_available():
        print("Tkinter is not available; use CLI.")
        return 2
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
    except Exception:
        print("Tkinter is not available; use CLI.")
        return 2

    if not ensure_eula_accepted(cli_accept=False):
        messagebox.showerror("EULA", "You must accept the EULA to use the app.")
        return 2

    root = tk.Tk()
    root.title(f"{APP_NAME} v{APP_VERSION}")
    root.geometry("900x540")

    queue_files: List[Path] = []
    out_dir = Path.home()
    template_var = tk.StringVar(value="{stem}.{ext}")
    fmt_var = tk.StringVar(value="wav")
    sr_var = tk.IntVar(value=48000)
    ch_var = tk.IntVar(value=2)
    bd_var = tk.IntVar(value=24)
    quality_var = tk.StringVar(value="")
    normalize_var = tk.BooleanVar(value=False)
    two_pass_var = tk.BooleanVar(value=True)
    lufs_var = tk.DoubleVar(value=-16.0)
    tp_var = tk.DoubleVar(value=-1.5)
    lra_var = tk.DoubleVar(value=11.0)
    fadein_var = tk.DoubleVar(value=0.0)
    fadeout_var = tk.DoubleVar(value=0.0)
    overwrite_var = tk.BooleanVar(value=False)

    frm = ttk.Frame(root, padding=10); frm.pack(fill="both", expand=True)
    top = ttk.Frame(frm); top.pack(fill="x")
    ttk.Button(top, text="Add Files…", command=lambda: _add_files()).pack(side="left")
    ttk.Button(top, text="Add Folder…", command=lambda: _add_folder()).pack(side="left", padx=6)
    ttk.Button(top, text="Clear", command=lambda: _clear()).pack(side="left")
    ttk.Label(top, text="Output:").pack(side="left", padx=(12,4))
    out_label = ttk.Label(top, text=str(out_dir)); out_label.pack(side="left")
    ttk.Button(top, text="Choose…", command=lambda: _choose_out()).pack(side="left", padx=6)
    ttk.Button(top, text="Download FFmpeg…", command=open_ffmpeg_download_page).pack(side="right")
    ttk.Button(top, text="Get Downloads…", command=lambda: open_url(DOWNLOADS_LANDING_URL)).pack(side="right", padx=(6,0))

    cols = ("name","duration","status","message")
    tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
    for c in cols: tree.heading(c, text=c.capitalize())
    tree.column("name", width=360); tree.column("duration", width=80); tree.column("status", width=80); tree.column("message", width=260)
    tree.pack(fill="both", expand=True, pady=(8,8))

    opts = ttk.LabelFrame(frm, text="Processing Settings")
    opts.pack(fill="x", pady=(0,8))
    r1 = ttk.Frame(opts); r1.pack(fill="x", pady=2)
    ttk.Label(r1, text="Format").pack(side="left"); ttk.Combobox(r1, textvariable=fmt_var, values=["wav","mp3","flac","m4a","aac","ogg","opus"], width=6).pack(side="left", padx=6)
    ttk.Label(r1, text="Quality").pack(side="left"); ttk.Entry(r1, textvariable=quality_var, width=8).pack(side="left", padx=6)
    ttk.Label(r1, text="Bit Depth").pack(side="left"); ttk.Spinbox(r1, from_=16, to=32, increment=8, textvariable=bd_var, width=5).pack(side="left", padx=6)
    ttk.Label(r1, text="SR").pack(side="left"); ttk.Combobox(r1, textvariable=sr_var, values=[22050,32000,44100,48000,88200,96000], width=6).pack(side="left", padx=6)
    ttk.Label(r1, text="Ch").pack(side="left"); ttk.Spinbox(r1, from_=1, to=8, textvariable=ch_var, width=4).pack(side="left", padx=6)
    r2 = ttk.Frame(opts); r2.pack(fill="x", pady=2)
    ttk.Checkbutton(r2, text="Normalize", variable=normalize_var).pack(side="left")
    ttk.Checkbutton(r2, text="Two-Pass", variable=two_pass_var).pack(side="left", padx=6)
    ttk.Label(r2, text="LUFS").pack(side="left"); ttk.Entry(r2, textvariable=lufs_var, width=6).pack(side="left", padx=4)
    ttk.Label(r2, text="TP").pack(side="left"); ttk.Entry(r2, textvariable=tp_var, width=6).pack(side="left", padx=4)
    ttk.Label(r2, text="LRA").pack(side="left"); ttk.Entry(r2, textvariable=lra_var, width=6).pack(side="left", padx=4)
    ttk.Label(r2, text="Fade In").pack(side="left"); ttk.Entry(r2, textvariable=fadein_var, width=6).pack(side="left", padx=4)
    ttk.Label(r2, text="Fade Out").pack(side="left"); ttk.Entry(r2, textvariable=fadeout_var, width=6).pack(side="left", padx=4)
    ttk.Checkbutton(r2, text="Overwrite", variable=overwrite_var).pack(side="left", padx=(8,0))
    r3 = ttk.Frame(opts); r3.pack(fill="x", pady=2)
    ttk.Label(r3, text="Filename Template").pack(side="left")
    ttk.Entry(r3, textvariable=template_var, width=40).pack(side="left", padx=6)

    bottom = ttk.Frame(frm); bottom.pack(fill="x")
    start_btn = ttk.Button(bottom, text="Start", command=lambda: _start())
    stop_btn = ttk.Button(bottom, text="Stop", state="disabled", command=lambda: _stop())
    export_btn = ttk.Button(bottom, text="Export Report…", command=lambda: _export())
    start_btn.pack(side="left"); stop_btn.pack(side="left", padx=6); export_btn.pack(side="left", padx=6)

    stop_flag = threading.Event()
    rows: List[Dict[str,str]] = []

    def _add_files():
        nonlocal queue_files
        paths = filedialog.askopenfilenames(title="Add audio files")
        for p in paths:
            pp = Path(p)
            queue_files.append(pp)
            tree.insert("", "end", values=(pp.name, f"{FFMPEG.probe_duration(pp):.1f}s", "queued", ""))

    def _add_folder():
        nonlocal queue_files
        p = filedialog.askdirectory(title="Add folder")
        if not p: return
        files = discover_inputs(Path(p))
        for pp in files:
            queue_files.append(pp)
            tree.insert("", "end", values=(pp.name, f"{FFMPEG.probe_duration(pp):.1f}s", "queued", ""))

    def _clear():
        nonlocal queue_files, rows
        queue_files = []
        rows = []
        for i in tree.get_children():
            tree.delete(i)

    def _choose_out():
        nonlocal out_dir
        d = filedialog.askdirectory(title="Choose output folder")
        if not d: return
        out_dir = Path(d)
        out_label.config(text=str(out_dir))

    def _export():
        if not rows:
            messagebox.showinfo("Export Report", "Nothing to export yet.")
            return
        p = filedialog.asksaveasfilename(title="Save CSV", defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not p: return
        write_csv_report(rows, Path(p))
        messagebox.showinfo("Export Report", f"Wrote {p}")

    def _start():
        if not FFMPEG.is_available():
            if messagebox.askyesno("FFmpeg Missing", "FFmpeg not found. Open download page?"):
                open_ffmpeg_download_page()
            return
        s = ProcessingSettings(
            fmt=fmt_var.get(), quality=quality_var.get(), bit_depth=int(bd_var.get()),
            sr=int(sr_var.get()), ch=int(ch_var.get()), normalize=bool(normalize_var.get()),
            two_pass=bool(two_pass_var.get()), lufs=float(lufs_var.get()), tp=float(tp_var.get()),
            lra=float(lra_var.get()), fade_in=float(fadein_var.get()), fade_out=float(fadeout_var.get()),
            overwrite=bool(overwrite_var.get()),
        )
        try:
            s.validate()
        except Exception as e:
            messagebox.showerror("Invalid Settings", str(e)); return
        start_btn.config(state="disabled"); stop_btn.config(state="normal")
        stop_flag.clear()
        rows.clear()

        def worker():
            proc = AudioProcessor(s, out_dir, template_var.get())
            for idx, src in enumerate(list(queue_files), 1):
                if stop_flag.is_set(): break
                dst = safe_out_name(src, out_dir, template_var.get(), idx, s)
                status, message, seconds = proc.process_one(src, dst)
                rows.append({"source": str(src), "dest": str(dst), "status": status, "message": message, "seconds": f"{seconds:.2f}"})
                tree.insert("", "end", values=(src.name, f"{seconds:.1f}s", status, message))
            start_btn.config(state="normal"); stop_btn.config(state="disabled")

        threading.Thread(target=worker, daemon=True).start()

    def _stop():
        stop_flag.set()

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
    return 0

# ------------------------- Entrypoint ------------------------------
if __name__ == "__main__":
    try:
        sys.exit(cli_main())
    except KeyboardInterrupt:
        sys.exit(130)