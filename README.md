# Music Forge Pro Max

Music Forge Pro Max is a powerful, free, and open-source audio processing tool built with Python, Tkinter, and FFmpeg. It provides a comprehensive set of features for converting, normalizing, and processing audio files in batches.

## Features

*   **Batch Processing:** Process multiple audio files at once.
*   **Format Conversion:** Convert between a wide range of audio formats, including WAV, MP3, FLAC, AAC, M4A, and Ogg.
*   **Loudness Normalization:** Normalize audio files to a target loudness using the EBU R128 standard.
*   **Metadata Editing:** Edit the metadata of your audio files using templates.
*   **Presets:** Save and load your favorite processing settings as presets.
*   **Folder Watching:** Automatically process new audio files as they are added to a folder.
*   **GUI and CLI:** Use the application through a graphical user interface or a command-line interface.

## Getting Started

To run the application, simply execute the `musicforge.py` script:

```bash
./musicforge.py
```

This will launch the graphical user interface. You can also use the command-line interface by passing the `--help` flag to see the available options:

```bash
./musicforge.py --help
```

## Dependencies

*   Python 3
*   Tkinter
*   FFmpeg

FFmpeg must be installed and available in your system's PATH. You can download it from the official website: https://ffmpeg.org/download.html