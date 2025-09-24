import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from musicforge_pro.core import ProcessingSettings

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
