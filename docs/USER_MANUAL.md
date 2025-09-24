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
