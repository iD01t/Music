#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MusicForge Pro Max — All-in-One Batch Audio Studio (Enhanced GUI Edition)
========================================================================
Production-ready, batteries-included rewrite of MusicForge aimed at
creators, podcasters, streamers, and studios who need reliable, fast, and
repeatable batch processing of audio assets using FFmpeg/FFprobe.

Enhanced Features:
-----------------
- Modern React-inspired GUI with professional styling
- Two UIs in one: full desktop GUI and powerful CLI
- Two-pass loudness normalization (EBU R128) with one-pass fallback
- Metadata authoring with templating support
- Filename templates with placeholders
- Folder Watch for automated hot-folder workflows
- Parallel workers with intelligent thread management
- Session restore and user presets
- Enhanced CSV reports with full metadata
- Thread-safe logging and progress tracking
- Cross-platform compatibility

License: Commercial — © iD01t Productions
Python: 3.9+
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import queue
import re
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
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

# --- Tkinter (GUI) ---
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, font
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

APP_NAME = "MusicForge Pro Max"
APP_VERSION = "1.0.0"

# Modern color scheme inspired by React apps
COLORS = {
    'primary': '#2563eb',      # Blue-600
    'primary_hover': '#1d4ed8', # Blue-700
    'secondary': '#6b7280',    # Gray-500
    'success': '#10b981',      # Emerald-500
    'warning': '#f59e0b',      # Amber-500
    'danger': '#ef4444',       # Red-500
    'background': '#f8fafc',   # Slate-50
    'surface': '#ffffff',      # White
    'surface_hover': '#f1f5f9', # Slate-100
    'border': '#e2e8f0',       # Slate-200
    'text_primary': '#1e293b', # Slate-800
    'text_secondary': '#64748b', # Slate-500
    'text_muted': '#94a3b8'    # Slate-400
}

# Audio extensions
AUDIO_EXTS = {
    ".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg", ".aiff", ".wma", ".mka", ".opus", ".mp2", ".mpa", ".ac3"
}

# Default presets with enhanced configurations
DEFAULT_PRESETS: Dict[str, Dict] = {
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
    "Hi-Fi FLAC (no normalize)": {
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
    },
    "High Quality Opus": {
        "output_format": "opus", "quality": "128k", "sample_rate": 48000,
        "channels": 2, "normalize_loudness": True, "normalize_mode": "one-pass",
        "target_i": -16.0, "target_tp": -1.5, "target_lra": 11.0
    }
}

SESSION_FILE = Path.home() / ".musicforge_pro_session.json"
LOG_FILE = Path.home() / ".musicforge_pro.log"

# User manual with Opus examples
USER_MANUAL = r"""
===============================================================================
MUSICFORGE PRO MAX — OFFICIAL USER MANUAL
===============================================================================

Welcome! This guide walks you through everything you can do with MusicForge Pro Max.

TABLE OF CONTENTS
-----------------
1) Quick Start
2) Concepts & Terminology
3) Desktop App Walkthrough
4) CLI Reference & Recipes
5) Loudness Normalization (EBU R128) — Two-Pass Explained
6) Metadata & Filename Templating
7) Folder Watch — Hands-Free Pipelines
8) Presets — Built-in & User Presets
9) Session Restore & Logs
10) Troubleshooting
11) Power User Tips

1) QUICK START
--------------
GUI:
  - Run: python music_forge_pro_max.py
  - Add files/folder → choose output folder → tweak settings → Start
  - Export report from the toolbar to CSV

CLI:
  - Convert all files in 'in' to MP3 V2 with loudness normalize:
      music_forge_pro_max.py -i in -o out -f mp3 --normalize --quality V2
  - High quality Opus with two-pass normalization:
      music_forge_pro_max.py -i in -o out -f opus --normalize --mode two-pass --quality 128k

2) CONCEPTS & TERMINOLOGY
-------------------------
- Sample Rate (Hz): Audio samples per second. Common: 44100 (CD) / 48000 (video/Opus).
- Channels: 1=mono, 2=stereo. Higher values supported if the source has them.
- Bit Depth (WAV): 16/24/32 bit integer PCM target depth for WAV encoding.
- Normalization: Bringing levels to targets. MusicForge uses EBU R128 loudnorm.
- Two-Pass Loudnorm: Measures first, applies correction second for accuracy.
- True Peak (TP): Peak level approximated by oversampling; recommended ≤ -1.0 dBTP.

3) DESKTOP APP WALKTHROUGH
--------------------------
The modern interface features:
- Batch Processor: Queue management with real-time status
- Settings Panel: Format, quality, normalization controls
- Metadata Editor: Template-based tagging system
- Presets Manager: Built-in and custom presets
- Folder Watch: Automated hot-folder processing
- Enhanced Reports: Detailed CSV exports with full metadata

4) CLI REFERENCE & RECIPES
--------------------------
Examples:
  # WAV 48k/24-bit with two-pass normalize
  music_forge_pro_max.py -i in -o out -f wav --bit-depth 24 --sr 48000 --ch 2 \
      --normalize --mode two-pass --lufs -16 --tp -1.5 --lra 11

  # High quality Opus for streaming
  music_forge_pro_max.py -i in -o out -f opus --quality 128k \
      --normalize --mode one-pass

  # M4A (AAC) 256k with title from filename stem
  music_forge_pro_max.py -i in -o out -f m4a --quality 256k \
      --meta title="{stem}" artist="iD01t" \
      --template "{artist} - {title}.{ext}"

5) LOUDNESS NORMALIZATION
-------------------------
Two-pass loudnorm performs a measurement pass to obtain precise parameters
and then applies them in a second pass for accurate conformance.

Recommendations:
  • Music/Streaming: I=-16 LUFS, TP=-1.5 dBTP, LRA=11 LU
  • Podcasts/Voice: I=-16 LUFS, TP=-2.0 dBTP, LRA=7-11 LU
  • Opus: Works best with two-pass at 48kHz sample rate

6) METADATA & FILENAME TEMPLATING
---------------------------------
Available placeholders:
  {stem} = filename without extension
  {ext}  = output extension
  {index}= index in batch
  {artist}, {title} = metadata fields with nested templating

7) FOLDER WATCH
---------------
Automated processing of files as they appear in watched folders.
Perfect for hot-folder workflows and automated ingest pipelines.

8) PRESETS
----------
Built-in presets cover common workflows including the new "High Quality Opus"
preset optimized for streaming applications.

End of manual.
===============================================================================
"""

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
    bitrate: Optional[str] = None
    sample_rate: Optional[str] = None
    channels: Optional[str] = None
    encoder: Optional[str] = None
    warnings: Optional[str] = None

@dataclass
class ProcessingSettings:
    output_format: str = "wav"
    quality: str = "V2"
    bit_depth: int = 16
    sample_rate: int = 48000
    channels: int = 2
    normalize_loudness: bool = False
    normalize_mode: str = "one-pass"
    target_i: float = -16.0
    target_tp: float = -1.5
    target_lra: float = 11.0
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
        md = data.get("metadata") or {}
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

ProgressCallback = Callable[[str, float], None]

class AudioProcessor:
    def __init__(self, ff: FFmpegManager) -> None:
        self.ff = ff

    def _format_to_extension(self, fmt: str) -> str:
        return "m4a" if fmt.lower() in {"aac", "m4a"} else fmt.lower()

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
            br = s.quality if isinstance(s.quality, str) and s.quality.endswith("k") else "256k"
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
            br = s.quality if isinstance(s.quality, str) and s.quality.endswith("k") else "128k"
            # Opus defaults to 48kHz for best quality
            args = ["-c:a", "libopus", "-b:a", br]
            if not s.sample_rate or s.sample_rate != 48000:
                args.extend(["-ar", "48000"])
            return args
        return []

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
            # Dynamic timeout based on file duration
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
            return None
        except Exception:
            return None
        return None

    def build_command(self, af: AudioFile, s: ProcessingSettings, output_path: Path,
                      resolved_md: Dict[str, str], measured: Optional[Dict[str, float]] = None) -> List[str]:
        assert self.ff.ffmpeg_path, "FFmpeg path not set"
        cmd: List[str] = [self.ff.ffmpeg_path, "-y" if s.overwrite_existing else "-n", "-v", "error", "-hide_banner"]
        cmd += ["-i", af.path]
        if s.sample_rate and s.output_format.lower() != "opus":  # Opus handles sample rate internally
            cmd += ["-ar", str(s.sample_rate)]
        if s.channels:
            cmd += ["-ac", str(s.channels)]
        cmd += self.build_filters(af, s, measured)
        cmd += s.metadata.to_args(resolved_md)
        cmd += self.build_encoding_args(s)
        cmd += ["-progress", "pipe:1"]  # Consistent progress channel
        ext = self._format_to_extension(s.output_format)
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

            resolved = {
                "stem": Path(af.path).stem,
                "ext": self._format_to_extension(s.output_format),
                "name": af.name,
                "size_mb": f"{af.size/(1024*1024):.1f}",
                "duration_s": f"{af.duration:.1f}" if af.duration else ""
            }

            measured = None
            warnings = []
            if s.normalize_loudness and s.normalize_mode == "two-pass":
                measured = self.measure_loudness(af, s)
                af.measured_loudness = measured
                if not measured:
                    warnings.append("Two-pass fallback")

            # Set additional metadata for enhanced reporting
            af.sample_rate = str(s.sample_rate) if s.sample_rate else "N/A"
            af.channels = str(s.channels) if s.channels else "N/A"
            af.encoder = self._get_encoder_name(s)
            af.warnings = ", ".join(warnings) if warnings else ""

            cmd = self.build_command(af, s, output_path, resolved_md=resolved, measured=measured)

            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True
            )

            while True:
                if stop_event and stop_event.is_set():
                    try:
                        if os.name == "nt":
                            import ctypes
                            ctypes.windll.kernel32.GenerateConsoleCtrlEvent(1, proc.pid)
                            try:
                                proc.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                proc.kill()
                        else:
                            proc.send_signal(signal.SIGINT)
                    except Exception:
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
                        speed_str = line.split("=", 1)[1].replace("x", "")
                        speed = float(speed_str)
                        if af.duration and af.duration > 0 and speed > 0:
                            current_time = out_ms / 1_000_000.0 if 'out_ms' in locals() else 0
                            remaining_time = (af.duration - current_time) / speed
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
            last = next((l for l in reversed([l.strip() for l in err.splitlines() if l.strip()])), "")
            return False, last or f"FFmpeg exited with code {ret}"
        except Exception as e:
            return False, str(e)

    def _get_encoder_name(self, s: ProcessingSettings) -> str:
        fmt = s.output_format.lower()
        if fmt == "wav":
            return "PCM"
        elif fmt == "flac":
            return "FLAC"
        elif fmt in {"aac", "m4a"}:
            return "libfdk_aac" if FFMPEG.libfdk_aac_available else "aac"
        elif fmt == "mp3":
            return "libmp3lame"
        elif fmt == "ogg":
            return "libvorbis"
        elif fmt == "opus":
            return "libopus"
        else:
            return s.output_format.upper()

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
        merged = {**ProcessingSettings().__dict__, **base}
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
# Folder Watch
# ======================================================================================

class FolderWatcher(threading.Thread):
    def __init__(self, folder: Path, poll_seconds: int, on_new: Callable[[List[str]], None]) -> None:
        super().__init__(daemon=True)
        self.folder = folder
        self.poll_seconds = max(1, int(poll_seconds))
        self.on_new = on_new
        self._stop = threading.Event()
        self._seen: set = set()

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
            time.sleep(self