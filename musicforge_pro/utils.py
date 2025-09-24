import os
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .core import ProcessingSettings

AUDIO_EXTS = {
    ".wav",
    ".mp3",
    ".flac",
    ".aac",
    ".m4a",
    ".ogg",
    ".aiff",
    ".wma",
    ".mka",
    ".opus",
    ".mp2",
    ".mpa",
    ".ac3",
}

DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
    "Streaming WAV 48k/24b": {
        "output_format": "wav",
        "bit_depth": 24,
        "sample_rate": 48000,
        "channels": 2,
        "normalize_loudness": True,
        "normalize_mode": "two-pass",
        "target_i": -16.0,
        "target_tp": -1.5,
        "target_lra": 11.0,
    },
    "Podcast MP3 (V2)": {
        "output_format": "mp3",
        "quality": "V2",
        "sample_rate": 48000,
        "channels": 2,
        "normalize_loudness": True,
        "normalize_mode": "one-pass",
        "target_i": -16.0,
        "target_tp": -1.5,
        "target_lra": 11.0,
    },
    "Hi‑Fi FLAC (no normalize)": {
        "output_format": "flac",
        "sample_rate": 48000,
        "channels": 2,
        "normalize_loudness": False,
    },
    "Mobile AAC 256k": {
        "output_format": "m4a",
        "quality": "256k",
        "sample_rate": 44100,
        "channels": 2,
        "normalize_loudness": False,
    },
    "OGG Vorbis Q6": {
        "output_format": "ogg",
        "quality": "6",
        "sample_rate": 48000,
        "channels": 2,
        "normalize_loudness": True,
        "normalize_mode": "one-pass",
        "target_i": -16.0,
        "target_tp": -1.5,
        "target_lra": 11.0,
    },
}

SESSION_FILE = Path.home() / ".musicforge_pro_session.json"
LOG_FILE = Path.home() / ".musicforge_pro.log"

LOCALE = {
    "en": {
        "add_files": "Add Files…",
        "add_folder": "Add Folder…",
        "start": "Start",
        "stop": "Stop",
        "clear": "Clear",
        "export_report": "Export Report…",
        "user_manual": "User Manual",
        "show_manual": "Show Manual",
    },
    "fr": {
        "add_files": "Ajouter des fichiers…",
        "add_folder": "Ajouter un dossier…",
        "start": "Démarrer",
        "stop": "Arrêter",
        "clear": "Vider",
        "export_report": "Exporter le rapport…",
        "user_manual": "Manuel d’utilisateur",
        "show_manual": "Afficher le manuel",
    },
}


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

    def save(
        self, settings: ProcessingSettings, geometry: Optional[str] = None
    ) -> None:
        data = {"settings": json.loads(settings.to_json()), "geometry": geometry or ""}
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


class FolderWatcher(threading.Thread):
    def __init__(
        self, folder: Path, poll_seconds: int, on_new: Callable[[List[str]], None]
    ) -> None:
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
