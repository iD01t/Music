import unittest
import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from musicforge_pro.core import ProcessingSettings
from settings_validator import validate_settings


class TestSettingsValidator(unittest.TestCase):
    def setUp(self):
        self.settings = ProcessingSettings()

    def test_valid_settings(self):
        try:
            validate_settings(self.settings)
        except ValueError:
            self.fail("validate_settings() raised ValueError unexpectedly!")

    def test_invalid_lufs(self):
        self.settings.normalize_loudness = True
        self.settings.target_i = -100
        with self.assertRaises(ValueError):
            validate_settings(self.settings)

    def test_invalid_true_peak(self):
        self.settings.normalize_loudness = True
        self.settings.target_tp = 0
        with self.assertRaises(ValueError):
            validate_settings(self.settings)

    def test_invalid_lra(self):
        self.settings.normalize_loudness = True
        self.settings.target_lra = -1
        with self.assertRaises(ValueError):
            validate_settings(self.settings)

    def test_invalid_bit_depth(self):
        self.settings.output_format = "wav"
        self.settings.bit_depth = 12
        with self.assertRaises(ValueError):
            validate_settings(self.settings)

    def test_invalid_sample_rate(self):
        self.settings.sample_rate = 12345
        with self.assertRaises(ValueError):
            validate_settings(self.settings)

    def test_invalid_channels(self):
        self.settings.channels = 0
        with self.assertRaises(ValueError):
            validate_settings(self.settings)
        self.settings.channels = 9
        with self.assertRaises(ValueError):
            validate_settings(self.settings)

    def test_invalid_mp3_quality(self):
        self.settings.output_format = "mp3"
        self.settings.quality = "V5"
        with self.assertRaises(ValueError):
            validate_settings(self.settings)

    def test_invalid_aac_quality(self):
        self.settings.output_format = "aac"
        self.settings.quality = "bad"
        with self.assertRaises(ValueError):
            validate_settings(self.settings)


if __name__ == "__main__":
    unittest.main()
