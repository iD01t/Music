import os
import subprocess
import json
import logging
import shlex
import threading
import time
import signal
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .utils import run_ffmpeg, validate_settings


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
        md: Dict[str, str] = data.get("metadata") or {}
        data["metadata"] = MetadataTemplate(**md)
        return ProcessingSettings(**data)


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
            for c in [
                Path("C:/ffmpeg/bin") / f"{name}.exe",
                Path("C:/Program Files/ffmpeg/bin") / f"{name}.exe",
                Path("C:/Program Files (x86)/ffmpeg/bin") / f"{name}.exe",
            ]:
                if c.exists() and os.access(c, os.X_OK):
                    return str(c)
        return None

    def _check_libfdk_aac(self) -> bool:
        if not self.ffmpeg_path:
            return False
        try:
            cmd = [self.ffmpeg_path, "-encoders"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=10
            )
            return "libfdk_aac" in (result.stdout or "")
        except Exception:
            return False

    def is_available(self) -> bool:
        return bool(self.ffmpeg_path and self.ffprobe_path)

    def get_version_info(self) -> Dict[str, str]:
        info: Dict[str, str] = {}
        try:
            if self.ffmpeg_path:
                out = subprocess.run(
                    [self.ffmpeg_path, "-version"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                info["ffmpeg_version"] = (out.stdout or "").splitlines()[0].replace(
                    "ffmpeg version", ""
                ).strip() or "Unknown"
        except Exception:
            info["ffmpeg_version"] = "Unknown"
        try:
            if self.ffprobe_path:
                out = subprocess.run(
                    [self.ffprobe_path, "-version"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                info["ffprobe_version"] = (out.stdout or "").splitlines()[0].replace(
                    "ffprobe version", ""
                ).strip() or "Unknown"
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
                self.ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ]
            out = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return float((out.stdout or "").strip())
        except Exception:
            return 0.0


FFMPEG = FFmpegManager()

ProgressCallback = Callable[[str, float], None]


class AudioProcessor:
    def __init__(self, ff: FFmpegManager) -> None:
        self.ff = ff

    def format_to_extension(self, fmt: str) -> str:
        return "m4a" if fmt.lower() in {"aac", "m4a"} else fmt.lower()

    def build_filters(
        self,
        af: AudioFile,
        s: ProcessingSettings,
        measured: Optional[Dict[str, float]] = None,
    ) -> List[str]:
        filters: List[str] = []
        if s.normalize_loudness:
            if s.normalize_mode == "two-pass" and measured:
                filters.append(
                    f"loudnorm=I={s.target_i}:TP={s.target_tp}:LRA={s.target_lra}:measured_I={measured.get('input_i',0)}:measured_TP={measured.get('input_tp',0)}:measured_LRA={measured.get('input_lra',0)}:measured_thresh={measured.get('input_thresh',0)}:offset={measured.get('target_offset',0)}:linear=true:print_format=summary"
                )
            else:
                filters.append(
                    f"loudnorm=I={s.target_i}:TP={s.target_tp}:LRA={s.target_lra}:print_format=summary"
                )
        if s.fade_in_sec > 0:
            filters.append(f"afade=t=in:st=0:d={float(s.fade_in_sec):g}")
        if s.fade_out_sec > 0 and af.duration > 0:
            start = max(0.0, af.duration - float(s.fade_out_sec))
            filters.append(f"afade=t=out:st={start:g}:d={float(s.fade_out_sec):g}")
        return ["-af", ",".join(filters)] if filters else []

    def build_encoding_args(self, s: ProcessingSettings) -> List[str]:
        fmt = s.output_format.lower()
        if fmt == "wav":
            return [
                "-c:a",
                {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_s32le"}.get(
                    s.bit_depth, "pcm_s16le"
                ),
            ]
        if fmt == "flac":
            return ["-c:a", "flac"]
        if fmt in {"aac", "m4a"}:
            br = s.quality if s.quality.endswith("k") else "256k"
            return [
                "-c:a",
                "libfdk_aac" if self.ff.libfdk_aac_available else "aac",
                "-b:a",
                br,
            ]
        if fmt == "mp3":
            return [
                "-c:a",
                "libmp3lame",
                "-qscale:a",
                {"V0": "0", "V1": "1", "V2": "2", "V3": "3", "V4": "4"}.get(
                    str(s.quality).upper(), "2"
                ),
            ]
        if fmt == "ogg":
            q = max(0.0, min(10.0, float(s.quality) if s.quality.isdigit() else 6.0))
            return ["-c:a", "libvorbis", "-qscale:a", str(q)]
        if fmt == "opus":
            return ["-c:a", "libopus", "-b:a", "128k"] + (
                ["-ar", "48000"] if not s.sample_rate else []
            )
        return []

    def measure_loudness(
        self, af: AudioFile, s: ProcessingSettings
    ) -> Optional[Dict[str, float]]:
        if not self.ff.ffmpeg_path:
            return None
        cmd = [
            self.ff.ffmpeg_path,
            "-v",
            "error",
            "-i",
            af.path,
            "-af",
            f"loudnorm=I={s.target_i}:TP={s.target_tp}:LRA={s.target_lra}:print_format=json",
            "-f",
            "null",
            "-",
        ]
        try:
            timeout = max(30, min(300, int(af.duration * 2))) if af.duration > 0 else 30
            p = subprocess.run(
                cmd, capture_output=True, text=True, check=False, timeout=timeout
            )
            stderr = p.stderr or ""
            start, end = stderr.find("{"), stderr.rfind("}")
            if start != -1 and end > start:
                blob = json.loads(stderr[start : end + 1])
                return {
                    k: float(blob.get(k, 0))
                    for k in [
                        "input_i",
                        "input_tp",
                        "input_lra",
                        "input_thresh",
                        "target_offset",
                    ]
                }
        except (subprocess.TimeoutExpired, Exception):
            return None
        return None

    def build_command(
        self,
        af: AudioFile,
        s: ProcessingSettings,
        output_path: Path,
        resolved_md: Dict[str, str],
        measured: Optional[Dict[str, float]] = None,
    ) -> List[str]:
        assert self.ff.ffmpeg_path, "FFmpeg path not set"
        cmd = [
            self.ff.ffmpeg_path,
            "-y" if s.overwrite_existing else "-n",
            "-v",
            "error",
            "-hide_banner",
            "-i",
            af.path,
        ]
        if s.sample_rate:
            cmd.extend(["-ar", str(s.sample_rate)])
        if s.channels:
            cmd.extend(["-ac", str(s.channels)])
        cmd.extend(self.build_filters(af, s, measured))
        cmd.extend(s.metadata.to_args(resolved_md))
        cmd.extend(self.build_encoding_args(s))
        cmd.extend(["-progress", "pipe:1", "-nostats", "-v", "error"])
        if self.format_to_extension(s.output_format) in {"m4a", "aac"}:
            cmd.extend(["-f", "mp4"])
        cmd.append(str(output_path))
        return cmd

    def process_file(
        self,
        af: AudioFile,
        s: ProcessingSettings,
        output_path: Path,
        progress_callback: Optional[ProgressCallback] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> Tuple[bool, Optional[str]]:
        try:
            validate_settings(s)

            if not af.duration or af.duration <= 0:
                af.duration = FFMPEG.probe_duration(af.path)

            resolved = {
                "stem": Path(af.path).stem,
                "ext": self.format_to_extension(s.output_format),
                "name": af.name,
                "size_mb": f"{af.size/(1024*1024):.1f}",
                "duration_s": f"{af.duration:.1f}" if af.duration else "",
            }
            measured = (
                self.measure_loudness(af, s)
                if s.normalize_loudness and s.normalize_mode == "two-pass"
                else None
            )
            af.measured_loudness = measured
            cmd = self.build_command(af, s, output_path, resolved, measured)
            logging.debug(f"FFmpeg command: {' '.join(cmd)}")

            def progress_wrapper(percent: Optional[float] = None, **kwargs):
                if progress_callback and percent is not None:
                    progress_callback("progress", percent)

            rc, _, stderr = run_ffmpeg(
                cmd,
                on_progress=progress_wrapper,
                duration_sec=af.duration,
                stop_event=stop_event,
            )

            if rc == 0:
                return True, None
            else:
                last_line = (stderr.splitlines()[-1] if stderr else "").strip()
                return False, last_line or f"ffmpeg exited with {rc}"

        except Exception as e:
            return False, str(e)