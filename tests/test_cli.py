import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from musicforge_pro.cli import build_cli_parser, parse_kv_pairs, collect_audio_paths
from musicforge_pro.core import ProcessingSettings


class TestCli(unittest.TestCase):
    def test_build_cli_parser(self):
        parser = build_cli_parser()
        args = parser.parse_args(["-i", "input", "-o", "output", "--format", "mp3"])
        self.assertEqual(args.input, "input")
        self.assertEqual(args.output, "output")
        self.assertEqual(args.fmt, "mp3")

    def test_parse_kv_pairs(self):
        pairs = ["artist=Me", "title=My Song", "year=2023"]
        data = parse_kv_pairs(pairs)
        self.assertEqual(data, {"artist": "Me", "title": "My Song", "year": "2023"})

        pairs_with_quotes = ["artist='Me'", 'title="My Song"']
        data_with_quotes = parse_kv_pairs(pairs_with_quotes)
        self.assertEqual(data_with_quotes, {"artist": "Me", "title": "My Song"})

    @patch("pathlib.Path.is_file")
    @patch("pathlib.Path.rglob")
    def test_collect_audio_paths(self, mock_rglob, mock_is_file):
        # Test with a folder
        mock_is_file.return_value = False
        mock_rglob.return_value = [
            MagicMock(suffix=".wav"),
            MagicMock(suffix=".mp3"),
            MagicMock(suffix=".txt"),
        ]
        paths = collect_audio_paths("/fake/dir")
        self.assertEqual(len(paths), 2)

        # Test with a single file
        mock_is_file.return_value = True
        paths = collect_audio_paths("/fake/file.wav")
        self.assertEqual(paths, ["/fake/file.wav"])


if __name__ == "__main__":
    unittest.main()
