import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from musicforge_pro.gui import MusicForgeApp
from musicforge_pro.core import ProcessingSettings


class TestGUI(unittest.TestCase):
    @patch("tkinter.Tk")
    def setUp(self, mock_tk):
        self.app = MusicForgeApp()

    @patch("tkinter.messagebox")
    def test_show_about(self, mock_messagebox):
        self.app._show_about()
        mock_messagebox.showinfo.assert_called_once()

    @patch("tkinter.messagebox")
    @patch("musicforge_pro.gui.FFMPEG")
    def test_check_ffmpeg_dialog_available(self, mock_ffmpeg, mock_messagebox):
        mock_ffmpeg.is_available.return_value = True
        mock_ffmpeg.get_version_info.return_value = {
            "ffmpeg_version": "4.2.2",
            "ffprobe_version": "4.2.2",
        }
        self.app._check_ffmpeg_dialog()
        mock_messagebox.showinfo.assert_called_once()

    @patch("tkinter.messagebox")
    @patch("musicforge_pro.gui.FFMPEG")
    def test_check_ffmpeg_dialog_not_available(self, mock_ffmpeg, mock_messagebox):
        mock_ffmpeg.is_available.return_value = False
        self.app._check_ffmpeg_dialog()
        mock_messagebox.showwarning.assert_called_once()

    @patch("tkinter.filedialog")
    def test_save_preset(self, mock_filedialog):
        mock_filedialog.asksaveasfilename.return_value = "/fake/path.json"
        with patch.object(self.app.preset_mgr, "save_user_preset") as mock_save:
            self.app._save_preset()
            mock_save.assert_called_once()

    @patch("tkinter.filedialog")
    def test_load_preset(self, mock_filedialog):
        mock_filedialog.askopenfilename.return_value = "/fake/path.json"
        with patch.object(
            self.app.preset_mgr, "load_user_preset"
        ) as mock_load, patch.object(
            self.app, "_apply_settings_to_ui"
        ) as mock_apply:
            mock_load.return_value = ProcessingSettings()
            self.app._load_preset()
            mock_load.assert_called_once()
            mock_apply.assert_called_once()


if __name__ == "__main__":
    unittest.main()