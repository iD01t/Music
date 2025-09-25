import subprocess
import threading
import os
import signal
import time
import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Tuple, TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from .core import ProcessingSettings, AudioFile

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg", ".opus", ".aiff", ".wma", ".mka"}
LOG_FILE = Path.home() / ".musicforge_log.txt"

def run_ffmpeg(
    cmd: List[str],
    on_progress: Optional[Callable[..., None]] = None,
    duration_sec: float = 0.0,
    timeout: Optional[int] = None,
    stop_event: Optional[threading.Event] = None,
) -> Tuple[int, str, str]:
    """
    Runs an FFmpeg command, captures its output, and reports progress.

    This function is an improved runner for FFmpeg processes that provides
    real-time progress reporting by parsing FFmpeg's progress output from stdout.

    Args:
        cmd: The FFmpeg command to execute as a list of strings.
        on_progress: A callback function to report progress. It will be called
            with keyword arguments parsed from FFmpeg's progress output
            (e.g., frame, fps, bitrate, speed, out_time_ms, etc.), plus
            'percent' and 'eta_sec' if they can be calculated.
        duration_sec: The total duration of the input file in seconds, used
            to calculate the progress percentage and ETA.
        timeout: An optional timeout for the process in seconds.
        stop_event: An optional threading.Event to signal cancellation.

    Returns:
        A tuple containing the return code, stdout, and stderr of the process.
    """
    kwargs: Dict[str, Any] = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
        **kwargs,
    )

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    def read_stderr() -> None:
        if proc.stderr:
            for line in proc.stderr:
                stderr_lines.append(line)

    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stderr_thread.start()

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
                except Exception:
                    proc.kill()

            stderr_thread.join(timeout=1)
            return -1, "".join(stdout_lines), "".join(stderr_lines)

        if proc.stdout is None:
            break

        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                break
            time.sleep(0.01)
            continue

        stdout_lines.append(line)
        line = line.strip()

        if on_progress and "=" in line:
            progress_data: Dict[str, Any] = {}
            parts = line.split("=")
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                progress_data[key] = value

                if key == "out_time_ms" and duration_sec > 0:
                    try:
                        out_ms = float(value)
                        percent = min(100.0, (out_ms / 1_000_000.0) / duration_sec * 100.0)
                        progress_data["percent"] = percent

                        speed_str = progress_data.get("speed", "1.0").rstrip("x")
                        speed = float(speed_str) if speed_str else 1.0
                        if speed > 0:
                            eta = (duration_sec - (out_ms / 1_000_000.0)) / speed
                            progress_data["eta_sec"] = eta
                    except (ValueError, ZeroDivisionError):
                        pass

                if progress_data:
                    on_progress(**progress_data)

    rc = proc.wait(timeout=timeout)
    stderr_thread.join(timeout=1)

    return rc, "".join(stdout_lines), "".join(stderr_lines)


def validate_settings(s: "ProcessingSettings") -> None:
    """
    Validates the given ProcessingSettings object and raises a ValueError on failure.
    """
    # Loudness settings
    if s.normalize_loudness:
        if not (-36.0 <= s.target_i <= -8.0):
            raise ValueError(f"Target LUFS must be between -36 and -8, but got {s.target_i}")
        if s.target_tp > -1.0:
            raise ValueError(f"Target true peak must be ≤ -1.0 dBTP, but got {s.target_tp}")
        if s.target_lra < 0:
            raise ValueError(f"Target LRA must be ≥ 0, but got {s.target_lra}")

    # Format-specific settings
    fmt = s.output_format.lower()
    if fmt == "wav":
        if s.bit_depth not in {16, 24, 32}:
            raise ValueError(f"WAV bit depth must be 16, 24, or 32, but got {s.bit_depth}")
    elif fmt == "mp3":
        if s.quality.upper() not in {"V0", "V1", "V2", "V3", "V4"}:
            raise ValueError(f"MP3 quality must be V0-V4, but got '{s.quality}'")
    elif fmt in {"aac", "m4a"}:
        if not s.quality.endswith("k"):
            raise ValueError(f"AAC quality must be a bitrate (e.g., '256k'), but got '{s.quality}'")
        try:
            br = int(s.quality[:-1])
            if not (64 <= br <= 320):
                raise ValueError("AAC bitrate must be between 64k and 320k.")
        except (ValueError, IndexError):
            raise ValueError(f"Invalid AAC bitrate format: '{s.quality}'")
    elif fmt == "ogg":
        try:
            q = int(s.quality)
            if not (0 <= q <= 10):
                raise ValueError("OGG quality must be an integer between 0 and 10.")
        except (ValueError, TypeError):
            raise ValueError(f"Invalid OGG quality format: '{s.quality}'")

    # General audio settings
    if s.sample_rate not in {22050, 32000, 44100, 48000, 88200, 96000}:
        raise ValueError(f"Invalid sample rate: {s.sample_rate}. Must be one of the common rates.")
    if not (1 <= s.channels <= 8):
        raise ValueError(f"Channels must be between 1 and 8, but got {s.channels}")

    # Filesystem settings
    if s.output_directory:
        p = Path(s.output_directory)
        if p.exists() and not p.is_dir():
            raise ValueError(f"Output path '{s.output_directory}' exists and is not a directory.")

    # Template validation
    try:
        s.filename_template.format(stem="test", ext="wav", index=1, artist="art", title="tit")
    except KeyError as e:
        raise ValueError(f"Invalid placeholder in filename template: {e}")
    except Exception as e:
        raise ValueError(f"Invalid filename template format: {e}")

class PresetManager:
    def __init__(self, user_preset_dir: Optional[Path] = None):
        self.user_preset_dir = user_preset_dir or Path.home() / ".musicforge" / "presets"
        self.user_preset_dir.mkdir(parents=True, exist_ok=True)

    def list_builtin(self) -> List[str]:
        return ["CD Quality", "Broadcast (EBU)", "Streaming (Spotify)", "Voiceover"]

    def load_builtin(self, name: str) -> "ProcessingSettings":
        from .core import ProcessingSettings, MetadataTemplate
        s = ProcessingSettings()
        if name == "CD Quality":
            s.output_format = "wav"
            s.bit_depth = 16
            s.sample_rate = 44100
        elif name == "Broadcast (EBU)":
            s.output_format = "wav"
            s.bit_depth = 24
            s.sample_rate = 48000
            s.normalize_loudness = True
            s.target_i = -23.0
            s.target_tp = -1.0
        elif name == "Streaming (Spotify)":
            s.output_format = "mp3"
            s.quality = "V0"
            s.normalize_loudness = True
            s.target_i = -14.0
            s.target_tp = -1.0
        elif name == "Voiceover":
            s.output_format = "mp3"
            s.quality = "V2"
            s.normalize_loudness = True
            s.target_i = -19.0
            s.target_tp = -1.5
            s.metadata = MetadataTemplate(artist="", title="{stem}", album="", year="", genre="Podcast", comment="")
        return s

    def list_user_presets(self) -> List[str]:
        return sorted([p.stem for p in self.user_preset_dir.glob("*.json")])

    def save_user_preset(self, name: str, settings: "ProcessingSettings") -> None:
        path = self.user_preset_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(settings.to_json())

    def load_user_preset(self, name: str) -> "ProcessingSettings":
        from .core import ProcessingSettings
        path = self.user_preset_dir / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Preset '{name}' not found.")
        with open(path, "r", encoding="utf-8") as f:
            return ProcessingSettings.from_json(f.read())


class SessionStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or Path.home() / ".musicforge" / "session.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Tuple[Optional["ProcessingSettings"], Optional[str]]:
        from .core import ProcessingSettings
        if not self.path.exists():
            return None, None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                settings = ProcessingSettings.from_json(json.dumps(data.get("settings", {})))
                geometry = data.get("geometry")
                return settings, geometry
        except (json.JSONDecodeError, TypeError):
            return None, None

    def save(self, settings: "ProcessingSettings", geometry: Optional[str] = None) -> None:
        data = {"settings": json.loads(settings.to_json()), "geometry": geometry}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


class FolderWatcher(threading.Thread):
    def __init__(self, path: Path, poll_interval: int, callback: Callable[[Iterable[str]], None]):
        super().__init__(daemon=True)
        self.path = path
        self.poll_interval = poll_interval
        self.callback = callback
        self._stop_event = threading.Event()
        self._known_files = set(self._scan())

    def _scan(self) -> set[str]:
        return {str(p) for p in self.path.rglob("*") if p.suffix.lower() in AUDIO_EXTS}

    def run(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(self.poll_interval)
            current_files = self._scan()
            new_files = current_files - self._known_files
            if new_files:
                self.callback(sorted(list(new_files)))
                self._known_files = current_files

    def stop(self) -> None:
        self._stop_event.set()