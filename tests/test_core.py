import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import subprocess
from pathlib import Path

# Add the project root to the path to allow imports from musicforge_pro
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from musicforge_pro.core import (
    FFmpegManager,
    AudioProcessor,
    ProcessingSettings,
    AudioFile,
    MetadataTemplate,
)
from musicforge_pro.utils import PresetManager


class TestFFmpegManager(unittest.TestCase):
    @patch("subprocess.run")
    @patch("musicforge_pro.core.FFmpegManager._find_executable")
    def test_ffmpeg_manager_initialization(self, mock_find_executable, mock_run):
        # Mock _find_executable to simulate finding ffmpeg and ffprobe
        def find_side_effect(name):
            if name == "ffmpeg":
                return "/usr/bin/ffmpeg"
            if name == "ffprobe":
                return "/usr/bin/ffprobe"
            return None

        mock_find_executable.side_effect = find_side_effect

        # Mock the result of _check_libfdk_aac
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="libfdk_aac"
        )

        manager = FFmpegManager()

        self.assertEqual(manager.ffmpeg_path, "/usr/bin/ffmpeg")
        self.assertEqual(manager.ffprobe_path, "/usr/bin/ffprobe")
        self.assertTrue(manager.libfdk_aac_available)
        self.assertEqual(mock_find_executable.call_count, 2)
        mock_run.assert_called_once_with(
            ["/usr/bin/ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )


class TestAudioProcessor(unittest.TestCase):
    def setUp(self):
        self.ffmpeg_manager = MagicMock()
        self.ffmpeg_manager.ffmpeg_path = "ffmpeg"
        self.processor = AudioProcessor(self.ffmpeg_manager)
        self.audio_file = AudioFile(
            path="/tmp/test.wav", name="test.wav", duration=10.0
        )

    def test_build_command_simple_wav(self):
        settings = ProcessingSettings(output_format="wav")
        cmd = self.processor.build_command(
            self.audio_file,
            settings,
            Path("/out/test.wav"),
            {"stem": "test", "ext": "wav"},
        )
        self.assertIn("-c:a", cmd)
        self.assertIn("pcm_s16le", cmd)

    def test_build_command_normalize(self):
        settings = ProcessingSettings(
            normalize_loudness=True, target_i=-18, target_tp=-2.0
        )
        cmd = self.processor.build_command(
            self.audio_file,
            settings,
            Path("/out/test.wav"),
            {"stem": "test", "ext": "wav"},
        )
        self.assertIn("-af", cmd)
        self.assertIn(
            "loudnorm=I=-18:TP=-2.0:LRA=11.0:print_format=summary",
            cmd[cmd.index("-af") + 1],
        )

    def test_build_command_metadata(self):
        settings = ProcessingSettings(
            metadata=MetadataTemplate(artist="Test Artist", title="Test Title")
        )
        cmd = self.processor.build_command(
            self.audio_file,
            settings,
            Path("/out/test.wav"),
            {
                "stem": "test",
                "ext": "wav",
                "artist": "Test Artist",
                "title": "Test Title",
            },
        )
        self.assertIn("-metadata", cmd)
        self.assertIn("artist=Test Artist", cmd)
        self.assertIn("title=Test Title", cmd)


if __name__ == "__main__":
    unittest.main()
