import subprocess
import threading
import os
import signal
import time
from typing import Callable, Dict, List, Optional, Any, Tuple

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
