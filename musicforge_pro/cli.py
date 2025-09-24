import argparse
import csv
import sys
from pathlib import Path
import logging

from .core import (
    ProcessingSettings,
    AudioFile,
    AudioProcessor,
    FFMPEG,
    settings_validator_available,
    validate_settings as external_validate_settings,
)
from .utils import PresetManager, AUDIO_EXTS
from .helpers import ensure_eula_accepted

APP_NAME = "Music Forge Pro Max"
APP_VERSION = "1.0.0"


def build_cli_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="musicforge",
        description=f"{APP_NAME} {APP_VERSION} — FFmpeg batch audio studio",
    )
    p.add_argument(
        "--gui", action="store_true", help="Force launch GUI even if CLI args are present"
    )
    p.add_argument("--input", "-i", help="Input file or folder (for CLI mode)")
    p.add_argument("--output", "-o", help="Output folder (CLI mode)")
    p.add_argument(
        "--format",
        "-f",
        dest="fmt",
        choices=["wav", "mp3", "flac", "aac", "m4a", "ogg", "opus"],
        help="Output format",
    )
    p.add_argument(
        "--quality",
        "-q",
        help="Quality (mp3: V0..V4, aac/m4a: e.g., 256k, ogg: 0..10)",
    )
    p.add_argument("--bit-depth", type=int, default=None, help="WAV bit depth: 16/24/32")
    p.add_argument("--sr", "--sample-rate", type=int, default=None, help="Sample rate Hz")
    p.add_argument("--ch", "--channels", type=int, default=None, help="Number of audio channels")
    p.add_argument(
        "--normalize", action="store_true", help="Enable loudness normalization"
    )
    p.add_argument(
        "--mode", choices=["one-pass", "two-pass"], default=None, help="Normalization mode"
    )
    p.add_argument(
        "--lufs", type=float, default=None, help="Target integrated loudness, e.g., -16.0"
    )
    p.add_argument("--tp", type=float, default=None, help="True peak ceiling, e.g., -1.5")
    p.add_argument(
        "--lra", type=float, default=None, help="Target loudness range, e.g., 11.0"
    )
    p.add_argument("--fade-in", type=float, default=None, help="Fade-in duration seconds")
    p.add_argument(
        "--fade-out", type=float, default=None, help="Fade-out duration seconds"
    )
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    p.add_argument(
        "--template", help="Filename template, e.g., '{artist} - {title}.{ext}'"
    )
    p.add_argument(
        "--meta",
        nargs="*",
        help="Metadata k=v pairs, e.g., artist='Name' title='{stem}'",
    )
    p.add_argument("--parallel", type=int, default=1, help="Parallel workers")
    p.add_argument(
        "--watch", help="Watch a folder and auto-process new files (polling)"
    )
    p.add_argument("--poll", type=int, default=10, help="Watch polling seconds")
    p.add_argument("--preset", help="Use a built-in preset by name")
    p.add_argument("--report", help="CSV report output path")
    p.add_argument(
        "--manual", action="store_true", help="Print the in-app user manual and exit"
    )
    p.add_argument(
        "--power-guide",
        action="store_true",
        help="Print the power user guide & cookbook and exit",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned outputs and settings without processing",
    )
    p.add_argument(
        "--preset-list", action="store_true", help="List available presets and exit"
    )
    p.add_argument(
        "--test-progress",
        action="store_true",
        help="Test progress parsing with simulated ffmpeg output",
    )
    p.add_argument(
        "--accept-eula",
        action="store_true",
        help="Accept the EULA non-interactively (useful for headless/CI runs).",
    )
    return p


def _validate_cli_settings(s: "ProcessingSettings"):
    if settings_validator_available and external_validate_settings:
        try:
            external_validate_settings(s)
            return
        except ValueError as e:
            raise ValueError(f"Settings validation failed: {e}") from e

    # Fallback validation
    if s.normalize_loudness:
        if not (-36.0 <= s.target_i <= -8.0):
            raise ValueError(f"--lufs must be between -36 and -8, got {s.target_i}")
        if s.target_tp > -1.0:
            raise ValueError(f"--tp must be ≤ -1.0 dBTP, got {s.target_tp}")
        if s.target_lra < 0:
            raise ValueError(f"--lra must be ≥ 0, got {s.target_lra}")
    if s.bit_depth not in (16, 24, 32):
        raise ValueError(f"--bit-depth must be 16/24/32, got {s.bit_depth}")
    if s.sample_rate not in (22050, 32000, 44100, 48000, 88200, 96000):
        raise ValueError(f"--sr must be a common rate, got {s.sample_rate}")
    if not (1 <= s.channels <= 8):
        raise ValueError(f"--ch must be 1..8, got {s.channels}")


def parse_kv_pairs(pairs: list[str] | None) -> dict[str, str]:
    out = {}
    if not pairs:
        return out
    for item in pairs:
        if "=" not in item:
            continue
        safe = item.replace(r"\=", "\uE000")
        key, val = safe.split("=", 1)
        val = val.replace("\uE000", "=").strip()
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1].replace(r"\"", '"').replace(r"\'", "'")
        out[key.strip()] = val
    return out


def collect_audio_paths(inp: str) -> list[str]:
    p = Path(inp)
    if p.is_file():
        return [str(p)]
    return [str(f) for f in p.rglob("*") if f.suffix.lower() in AUDIO_EXTS]


def cli_main(argv: list[str]) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    if not ensure_eula_accepted(cli_accept=args.accept_eula):
        print("EULA not accepted. Use --accept-eula to run headless.", file=sys.stderr)
        return 2

    if args.manual:
        try:
            with open("docs/USER_MANUAL.md", "r", encoding="utf-8") as f:
                print(f.read())
        except FileNotFoundError:
            print("USER_MANUAL.md not found in docs/", file=sys.stderr)
        return 0
    if args.power_guide:
        try:
            with open("docs/POWER_GUIDE.md", "r", encoding="utf-8") as f:
                print(f.read())
        except FileNotFoundError:
            print("POWER_GUIDE.md not found in docs/", file=sys.stderr)
        return 0

    if args.preset_list:
        print("Available presets:")
        for name in PresetManager().list_builtin():
            print(f"  - {name}")
        return 0

    if not args.input or not args.output:
        parser.print_help()
        return 2

    if not FFMPEG.is_available():
        print(
            "FFmpeg/FFprobe not found. Install from https://ffmpeg.org/download.html",
            file=sys.stderr,
        )
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
            try:
                s = pm.load_user_preset(args.preset)
            except Exception:
                print(f"Preset not found: {args.preset}", file=sys.stderr)

    # Override with CLI flags
    if args.fmt:
        s.output_format = args.fmt
    if args.quality:
        s.quality = args.quality
    if args.bit_depth is not None:
        s.bit_depth = args.bit_depth
    if args.sr is not None:
        s.sample_rate = args.sr
    if args.ch is not None:
        s.channels = args.ch
    if args.normalize:
        s.normalize_loudness = True
    if args.mode:
        s.normalize_mode = args.mode
    if args.lufs is not None:
        s.target_i = args.lufs
    if args.tp is not None:
        s.target_tp = args.tp
    if args.lra is not None:
        s.target_lra = args.lra
    if args.fade_in is not None:
        s.fade_in_sec = args.fade_in
    if args.fade_out is not None:
        s.fade_out_sec = args.fade_out
    if args.overwrite:
        s.overwrite_existing = True
    if args.template:
        s.filename_template = args.template
    if args.parallel:
        s.parallelism = max(1, args.parallel)

    try:
        _validate_cli_settings(s)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    md_pairs = parse_kv_pairs(args.meta)
    for k, v in md_pairs.items():
        if hasattr(s.metadata, k):
            setattr(s.metadata, k, v)

    outdir = Path(args.output)
    if args.dry_run:
        print("DRY RUN - Planned outputs and settings:")
        # ... (dry run logic)
        return 0

    if not outdir.exists():
        outdir.mkdir(parents=True, exist_ok=True)

    proc = AudioProcessor(FFMPEG)
    total = len(files)
    ok_count = 0
    fail_count = 0
    rows = []

    for idx, fp in enumerate(files, start=1):
        src = Path(fp)
        ext = proc.format_to_extension(s.output_format)
        placeholders = {
            "stem": src.stem,
            "ext": ext,
            "index": idx,
            "artist": s.metadata.artist.format(stem=src.stem, ext=ext, index=idx) if s.metadata.artist else "",
            "title": s.metadata.title.format(stem=src.stem, ext=ext, index=idx) if s.metadata.title else src.stem,
        }
        fname = s.filename_template.format(**placeholders)
        dst = outdir / fname

        if dst.exists() and not s.overwrite_existing:
            base = dst.stem
            ext_suf = dst.suffix
            counter = 1
            while dst.exists():
                dst = outdir / f"{base}_{counter:03d}{ext_suf}"
                counter += 1

        af = AudioFile(path=str(src), name=src.name, size=int(src.stat().st_size), format=src.suffix.lstrip(".").lower())

        def cb(kind: str, value: float) -> None:
            if kind == "progress":
                pct = f"{value:5.1f}%"
                print(f"[{idx}/{total}] {src.name} -> {fname} {pct}", end="\r")

        ok, err = proc.process_file(af, s, dst, progress_callback=cb)

        if ok:
            ok_count += 1
            rows.append([src.name, af.format.upper(), f"{af.size/(1024*1024):.1f}", f"{af.duration:.1f}" if af.duration else "", "COMPLETED", "", str(dst)])
            print(f"\n[{idx}/{total}] {src.name} -> {fname}  DONE")
        else:
            fail_count += 1
            rows.append([src.name, af.format.upper(), f"{af.size/(1024*1024):.1f}", f"{af.duration:.1f}" if af.duration else "", "FAILED", err or "", str(dst)])
            print(f"\n[{idx}/{total}] {src.name} -> {fname}  ERROR: {err}")

    if args.report:
        try:
            with open(args.report, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["File", "Format", "Size (MB)", "Duration (s)", "Status", "Error", "Output"])
                w.writerows(rows)
            print(f"Report written: {args.report}")
        except Exception as e:
            print(f"Report error: {e}", file=sys.stderr)

    print(f"\nDone. OK={ok_count} FAILED={fail_count}")
    return 0 if fail_count == 0 else 1
