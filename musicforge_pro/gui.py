import os
import csv
import queue
import threading
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Any, Dict, Iterable

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    tk_available = True
except ImportError:
    tk_available = False

if tk_available:
    from .core import (
        AudioProcessor,
        FFMPEG,
        AudioFile,
        ProcessingSettings,
        ProcessingStatus,
        MetadataTemplate,
    )
    from .utils import PresetManager, SessionStore, FolderWatcher, AUDIO_EXTS, LOG_FILE
    from .helpers import (
        open_url,
        ensure_ffmpeg_present_or_prompt,
        guided_ffmpeg_install,
        _get_embedded_eula_text,
        DOWNLOADS_LANDING_URL,
        DOWNLOAD_LINKS,
        open_ffmpeg_download_page,
    )

    class MusicForgeApp(tk.Tk):
        def __init__(self) -> None:
            super().__init__()
            self.title("Music Forge Pro Max — Desktop")
            self.geometry("1400x900")
            self.minsize(1200, 800)
            self._log_lock = threading.Lock()

            self.user_manual = self._load_doc("docs/USER_MANUAL.md")
            self.power_guide = self._load_doc("docs/POWER_GUIDE.md")
            self.cookbook = self._load_doc("docs/COOKBOOK.txt")

            self.proc = AudioProcessor(FFMPEG)
            self.preset_mgr = PresetManager()
            self.session = SessionStore()
            self.settings = ProcessingSettings()
            self.audio_files: List[AudioFile] = []
            self._log_queue: "queue.Queue[Tuple[str,str]]" = queue.Queue()
            self._stop_event = threading.Event()
            self._threads: List[threading.Thread] = []
            self._watcher: Optional[FolderWatcher] = None

            self.output_dir_var = tk.StringVar(value=self.settings.output_directory or "")
            self.format_var = tk.StringVar(value=self.settings.output_format)
            self.quality_var = tk.StringVar(value=self.settings.quality)
            self.bit_depth_var = tk.IntVar(value=self.settings.bit_depth)
            self.sample_rate_var = tk.IntVar(value=self.settings.sample_rate)
            self.channels_var = tk.IntVar(value=self.settings.channels)
            self.normalize_var = tk.BooleanVar(value=self.settings.normalize_loudness)
            self.normalize_mode_var = tk.StringVar(value=self.settings.normalize_mode)
            self.target_i_var = tk.DoubleVar(value=self.settings.target_i)
            self.target_tp_var = tk.DoubleVar(value=self.settings.target_tp)
            self.target_lra_var = tk.DoubleVar(value=self.settings.target_lra)
            self.fade_in_var = tk.DoubleVar(value=self.settings.fade_in_sec)
            self.fade_out_var = tk.DoubleVar(value=self.settings.fade_out_sec)
            self.overwrite_var = tk.BooleanVar(value=self.settings.overwrite_existing)
            self.parallelism_var = tk.IntVar(value=self.settings.parallelism)
            self.template_var = tk.StringVar(value=self.settings.filename_template)
            self.meta_artist = tk.StringVar(value=self.settings.metadata.artist)
            self.meta_title = tk.StringVar(value=self.settings.metadata.title)
            self.meta_album = tk.StringVar(value=self.settings.metadata.album)
            self.meta_year = tk.StringVar(value=self.settings.metadata.year)
            self.meta_genre = tk.StringVar(value=self.settings.metadata.genre)
            self.meta_comment = tk.StringVar(value=self.settings.metadata.comment)

            self._build_menu()
            self.after(300, self._startup_ffmpeg_check)
            self._build_tabs()
            self._wire_events()
            self._load_session()
            self._check_ffmpeg()
            self.after(50, self._drain_log_queue)

        def _load_doc(self, path: str) -> str:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                messagebox.showwarning("Docs Missing", f"Could not load documentation file: {path}")
                return f"{path} not found."

        def _build_menu(self) -> None:
            menubar = tk.Menu(self)
            file_menu = tk.Menu(menubar, tearoff=0)
            file_menu.add_command(label="Add Files…", command=self._add_files)
            file_menu.add_command(label="Add Folder…", command=self._add_folder)
            file_menu.add_separator()
            file_menu.add_command(label="Save Preset…", command=self._save_preset)
            file_menu.add_command(label="Load Preset…", command=self._load_preset)
            file_menu.add_separator()
            file_menu.add_command(label="Export Report…", command=self._export_report)
            file_menu.add_separator()
            file_menu.add_command(label="Quit", command=self._on_quit)
            menubar.add_cascade(label="File", menu=file_menu)
            help_menu = tk.Menu(menubar, tearoff=0)
            help_menu.add_command(label="FFmpeg Help", command=self._show_ffmpeg_help)
            help_menu.add_command(label="Download Links…", command=self._show_downloads)
            help_menu.add_command(label="Get Music Forge…", command=lambda: open_url(DOWNLOADS_LANDING_URL))
            help_menu.add_command(label="Download FFmpeg…", command=lambda: open_ffmpeg_download_page())
            help_menu.add_command(label="Guided FFmpeg Install…", command=lambda: guided_ffmpeg_install())
            help_menu.add_command(label="View EULA…", command=lambda: messagebox.showinfo("EULA", _get_embedded_eula_text()))
            help_menu.add_command(label="About", command=self._show_about)
            help_menu.add_command(label="Check FFmpeg", command=self._check_ffmpeg_dialog, accelerator="Ctrl+K")
            self.bind_all("<Control-k>", lambda e: self._check_ffmpeg_dialog())
            help_menu.add_command(label="User Manual", command=self._show_manual)
            help_menu.add_command(label="Power Guide", command=self._show_power_guide)
            menubar.add_cascade(label="Help", menu=help_menu)
            self.config(menu=menubar)

        def _build_tabs(self) -> None:
            self.tabs = ttk.Notebook(self)
            self.tabs.pack(fill="both", expand=True, padx=8, pady=8)
            self.tab_batch = ttk.Frame(self.tabs)
            self.tabs.add(self.tab_batch, text="🎵 Batch Processor")
            ctrl = ttk.LabelFrame(self.tab_batch, text="⚙️ Processing Settings")
            ctrl.pack(fill="x", padx=12, pady=12)
            row1 = ttk.Frame(ctrl)
            row1.pack(fill="x", padx=12, pady=8)
            ttk.Label(row1, text="Format:").pack(side="left")
            self.format_combo = ttk.Combobox(row1, textvariable=self.format_var, width=10, values=["wav","mp3","flac","aac","m4a","ogg"], state="readonly")
            self.format_combo.pack(side="left", padx=(4, 12))
            ttk.Label(row1, text="Quality:").pack(side="left")
            self.quality_combo = ttk.Combobox(row1, textvariable=self.quality_var, width=10, values=["V0","V1","V2","V3","V4","192k","224k","256k","320k","3","4","5","6","7","8","9","10"])
            self.quality_combo.pack(side="left", padx=(4, 12))
            ttk.Label(row1, text="Bit Depth (WAV):").pack(side="left")
            self.bit_depth_combo = ttk.Combobox(row1, textvariable=self.bit_depth_var, width=6, values=["16","24","32"], state="readonly")
            self.bit_depth_combo.pack(side="left", padx=(4, 12))
            row2 = ttk.Frame(ctrl); row2.pack(fill="x", padx=8, pady=4)
            ttk.Label(row2, text="Sample Rate (Hz):").pack(side="left")
            ttk.Entry(row2, textvariable=self.sample_rate_var, width=10).pack(side="left", padx=(4, 12))
            ttk.Label(row2, text="Channels:").pack(side="left")
            ttk.Spinbox(row2, from_=1, to=8, textvariable=self.channels_var, width=6).pack(side="left", padx=(4, 12))
            ttk.Checkbutton(row2, text="Overwrite existing", variable=self.overwrite_var).pack(side="left", padx=(4, 12))
            ttk.Label(row2, text="Output Folder:").pack(side="left")
            ttk.Entry(row2, textvariable=self.output_dir_var, width=44).pack(side="left", padx=4)
            ttk.Button(row2, text="Browse…", command=self._choose_output_dir).pack(side="left", padx=(6, 0))
            row3 = ttk.Frame(ctrl); row3.pack(fill="x", padx=8, pady=4)
            ttk.Checkbutton(row3, text="Loudness normalize (EBU R128)", variable=self.normalize_var).pack(side="left")
            ttk.Label(row3, text="Mode:").pack(side="left", padx=(8,0))
            self.normalize_mode_combo = ttk.Combobox(row3, textvariable=self.normalize_mode_var, width=10, values=["one-pass","two-pass"], state="readonly")
            self.normalize_mode_combo.pack(side="left", padx=(4, 12))
            ttk.Label(row3, text="I:").pack(side="left"); ttk.Entry(row3, textvariable=self.target_i_var, width=6).pack(side="left", padx=(0,8))
            ttk.Label(row3, text="TP:").pack(side="left"); ttk.Entry(row3, textvariable=self.target_tp_var, width=6).pack(side="left", padx=(0,8))
            ttk.Label(row3, text="LRA:").pack(side="left"); ttk.Entry(row3, textvariable=self.target_lra_var, width=6).pack(side="left", padx=(0,8))
            ttk.Label(row3, text="Fade in (s):").pack(side="left", padx=(12,0)); ttk.Entry(row3, textvariable=self.fade_in_var, width=6).pack(side="left")
            ttk.Label(row3, text="Fade out (s):").pack(side="left", padx=(6,0)); ttk.Entry(row3, textvariable=self.fade_out_var, width=6).pack(side="left")
            ttk.Label(row3, text="Parallel workers:").pack(side="left", padx=(12,0))
            workers_spinbox = ttk.Spinbox(row3, from_=1, to=max(1, os.cpu_count() or 4), textvariable=self.parallelism_var, width=6)
            workers_spinbox.pack(side="left")
            ttk.Label(row3, text="Filename template:").pack(side="left", padx=(12,0)); ttk.Entry(row3, textvariable=self.template_var, width=40).pack(side="left")
            actions = ttk.Frame(self.tab_batch)
            actions.pack(fill="x", padx=12, pady=(0,12))
            ttk.Button(actions, text="📁 Add Files…", command=self._add_files).pack(side="left", padx=(0,6))
            ttk.Button(actions, text="📂 Add Folder…", command=self._add_folder).pack(side="left", padx=(0,6))
            ttk.Button(actions, text="🗑️ Clear", command=self._clear_queue).pack(side="left", padx=(0,6))
            ttk.Button(actions, text="📊 Export Report…", command=self._export_report).pack(side="left", padx=(0,12))
            ttk.Button(actions, text="▶️ Start", command=self._start_processing).pack(side="right", padx=(6,0))
            ttk.Button(actions, text="⏹️ Stop", command=self._stop_processing).pack(side="right")
            tv_wrap = ttk.Frame(self.tab_batch)
            tv_wrap.pack(fill="both", expand=True, padx=12, pady=(0,12))
            columns = ("format","duration","size","status","error","output")
            self.tree = ttk.Treeview(tv_wrap, columns=columns, show="headings", selectmode="extended")
            for col, label, width in [("format","Format",90), ("duration","Duration (s)",120), ("size","Size (MB)",100), ("status","Status",180), ("error","Error",440), ("output","Output",360)]:
                self.tree.heading(col, text=label)
                self.tree.column(col, width=width, anchor="center" if col in {"format","duration","size","status"} else "w")
            yscroll = ttk.Scrollbar(tv_wrap, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscrollcommand=yscroll.set); self.tree.pack(side="left", fill="both", expand=True); yscroll.pack(side="left", fill="y")
            bottom = ttk.Frame(self.tab_batch)
            bottom.pack(fill="x", padx=12, pady=(0,12))
            self.progress = ttk.Progressbar(bottom, mode="determinate")
            self.progress.pack(side="left", fill="x", expand=True, padx=(0,12))
            self.ffmpeg_label = ttk.Label(bottom, text="FFmpeg: checking…")
            self.ffmpeg_label.pack(side="right")
            self.tab_meta = ttk.Frame(self.tabs)
            self.tabs.add(self.tab_meta, text="🏷️ Metadata")
            meta = ttk.LabelFrame(self.tab_meta, text="🏷️ Tag Template")
            meta.pack(fill="x", padx=12, pady=12)
            def ml(parent: tk.Widget, text: str, var: tk.StringVar) -> None:
                row = ttk.Frame(parent); row.pack(fill="x", padx=8, pady=4)
                ttk.Label(row, text=text, width=12).pack(side="left")
                ttk.Entry(row, textvariable=var, width=60).pack(side="left", padx=(4,12))
            ml(meta, "Artist:", self.meta_artist)
            ml(meta, "Title:", self.meta_title)
            ml(meta, "Album:", self.meta_album)
            ml(meta, "Year:", self.meta_year)
            ml(meta, "Genre:", self.meta_genre)
            ml(meta, "Comment:", self.meta_comment)
            ttk.Label(meta, text="Placeholders: {stem}, {ext}, {index}, {artist}, {title}").pack(anchor="w", padx=16, pady=(0,8))
            self.tab_preset = ttk.Frame(self.tabs)
            self.tabs.add(self.tab_preset, text="⚙️ Presets")
            pr = ttk.LabelFrame(self.tab_preset, text="📦 Built‑in Presets")
            pr.pack(fill="x", padx=12, pady=12)
            self.preset_list = tk.Listbox(pr, height=6); self.preset_list.pack(fill="x", padx=8, pady=8)
            for name in self.preset_mgr.list_builtin():
                self.preset_list.insert("end", name)
            ttk.Button(pr, text="Load Selected", command=self._load_builtin_preset).pack(padx=8, pady=(0,8))
            usr = ttk.LabelFrame(self.tab_preset, text="User Presets"); usr.pack(fill="x", padx=8, pady=8)
            self.user_preset_list = tk.Listbox(usr, height=6); self.user_preset_list.pack(fill="x", padx=8, pady=8)
            self._refresh_user_presets()
            btns = ttk.Frame(usr); btns.pack(fill="x", padx=8, pady=(0,8))
            ttk.Button(btns, text="Save Current as…", command=self._save_preset).pack(side="left")
            ttk.Button(btns, text="Load Selected", command=self._load_user_preset).pack(side="left", padx=(8,0))
            self.tab_watch = ttk.Frame(self.tabs)
            self.tabs.add(self.tab_watch, text="👁️ Folder Watch")
            watch = ttk.LabelFrame(self.tab_watch, text="👁️ Auto‑Ingest")
            watch.pack(fill="x", padx=12, pady=12)
            self.watch_path_var = tk.StringVar(value="")
            self.poll_var = tk.IntVar(value=10)
            roww = ttk.Frame(watch); roww.pack(fill="x", padx=8, pady=4)
            ttk.Label(roww, text="Folder:").pack(side="left")
            ttk.Entry(roww, textvariable=self.watch_path_var, width=48).pack(side="left", padx=(4,8))
            ttk.Button(roww, text="Choose…", command=self._choose_watch_folder).pack(side="left")
            ttk.Label(roww, text="Poll (s):").pack(side="left", padx=(12,0))
            ttk.Spinbox(roww, from_=1, to=3600, textvariable=self.poll_var, width=6).pack(side="left", padx=(4,0))
            roww2 = ttk.Frame(watch); roww2.pack(fill="x", padx=8, pady=4)
            ttk.Button(roww2, text="Start Watch", command=self._start_watch).pack(side="left")
            ttk.Button(roww2, text="Stop Watch", command=self._stop_watch).pack(side="left", padx=(8,0))
            self.tab_diag = ttk.Frame(self.tabs)
            self.tabs.add(self.tab_diag, text="🔧 Diagnostics")
            dtop = ttk.Frame(self.tab_diag); dtop.pack(fill="x", padx=8, pady=8)
            ttk.Button(dtop, text="Refresh FFmpeg Info", command=self._refresh_diag).pack(side="left")
            self.diag_text = tk.Text(self.tab_diag, wrap="word", height=20); self.diag_text.pack(fill="both", expand=True, padx=8, pady=(0,8))
            self.tab_log = ttk.Frame(self.tabs)
            self.tabs.add(self.tab_log, text="📋 Log")
            self.log_text = tk.Text(self.tab_log, wrap="word", height=12); self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        def _wire_events(self):
            self.protocol("WM_DELETE_WINDOW", self._on_quit)
            self.format_combo.bind("<<ComboboxSelected>>", lambda e: self._on_format_changed())

        def _load_session(self):
            s, geo = self.session.load()
            if s:
                self._apply_settings_to_ui(s)
                self.settings = s
            if geo:
                try:
                    self.geometry(geo)
                except Exception:
                    pass

        def _on_quit(self):
            if any(af.status == ProcessingStatus.PROCESSING for af in self.audio_files):
                if not messagebox.askyesno("Quit", "Processing is still running. Quit anyway?"):
                    return
            try:
                self.session.save(self.settings, geometry=self.geometry())
            except Exception:
                pass
            self.destroy()

        def _log(self, msg: str, level: str = "info"):
            self._log_queue.put((level, msg))
            try:
                with self._log_lock, open(LOG_FILE, "a", encoding="utf-8") as fp:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    fp.write(f"[{ts}] {level.upper()}: {msg}\n")
            except Exception:
                pass

        def _drain_log_queue(self):
            try:
                while True:
                    level, msg = self._log_queue.get_nowait()
                    ts = datetime.now().strftime("%H:%M:%S")
                    if hasattr(self, "log_text"):
                        self.log_text.insert("end", f"[{ts}] {level.upper()}: {msg}\n")
                        self.log_text.see("end")
            except queue.Empty:
                pass
            finally:
                self.after(120, self._drain_log_queue)

        def _add_files(self):
            types = [("Audio files", "*.wav *.mp3 *.flac *.aac *.m4a *.ogg *.aiff *.wma *.mka *.opus"), ("All files", "*.*")]
            files = filedialog.askopenfilenames(title="Add Audio Files", filetypes=types)
            if files: self._enqueue_files(files)

        def _add_folder(self):
            d = filedialog.askdirectory(title="Add Folder")
            if not d: return
            paths = []
            for root, _, filenames in os.walk(d):
                for fn in filenames:
                    if Path(fn).suffix.lower() in AUDIO_EXTS:
                        paths.append(str(Path(root) / fn))
            self._enqueue_files(paths)

        def _enqueue_files(self, paths: Iterable[str]) -> None:
            added = 0
            for p in paths:
                p = str(Path(p))
                if not Path(p).exists(): continue
                st = os.stat(p)
                af = AudioFile(path=p, name=Path(p).name, size=int(st.st_size), format=(Path(p).suffix.lstrip(".") or "").lower())
                af.duration = FFMPEG.probe_duration(p)
                self.audio_files.append(af)
                self._add_tree_item(af)
                added += 1
            if added:
                self._log(f"Added {added} file(s) to queue.", "info")

        def _add_tree_item(self, af: AudioFile) -> None:
            self.tree.insert("", "end", iid=af.path, values=(
                af.format.upper(),
                f"{af.duration:.1f}" if af.duration else "",
                f"{af.size / (1024*1024):.1f}",
                af.status.value,
                af.error_message or "",
                af.output_path or "",
            ))

        def _clear_queue(self) -> None:
            self.audio_files.clear()
            self.tree.delete(*self.tree.get_children())
            self.progress["value"] = 0

        def _start_processing(self) -> None:
            self._stop_event.clear()
            self._sync_settings_from_ui()

            if not FFMPEG.is_available():
                messagebox.showerror("FFmpeg Missing", "FFmpeg/FFprobe not found.\nInstall from https://ffmpeg.org/download.html")
                return
            if not self.audio_files:
                messagebox.showinfo("No Files", "Add files to the queue first.")
                return

            for af in self.audio_files:
                af.status = ProcessingStatus.QUEUED
                af.error_message = None
                af.output_path = None
                self._update_tree_row(af)

            t = threading.Thread(target=self._dispatcher, daemon=True)
            t.start()
            self._threads.append(t)
            self._log("Started processing.", "info")

        def _dispatcher(self) -> None:
            work_q: "queue.Queue[AudioFile]" = queue.Queue()
            for af in self.audio_files:
                work_q.put(af)
            active: List[threading.Thread] = []

            def start_job():
                if work_q.empty(): return
                af = work_q.get()
                af.status = ProcessingStatus.PROCESSING
                self._update_tree_row(af)
                thread = threading.Thread(target=self._run_one, args=(af,), daemon=True)
                thread.start()
                active.append(thread)

            max_workers = self.settings.parallelism
            if (self.settings.normalize_loudness and self.settings.normalize_mode == "two-pass"):
                max_workers = min(max_workers, max(1, (os.cpu_count() or 4) // 2))

            for _ in range(max_workers):
                start_job()

            while active:
                for t in list(active):
                    if not t.is_alive():
                        active.remove(t)
                        if not work_q.empty() and not self._stop_event.is_set():
                            start_job()
                self._update_overall_progress()
                time.sleep(0.05)

            self._update_overall_progress(force_done=True)
            self._log("All processing finished.", "info")

        def _run_one(self, af: AudioFile) -> None:
            try:
                outp = self._output_path_for(af)
                if outp.exists() and not self.settings.overwrite_existing:
                    af.status = ProcessingStatus.SKIPPED
                    af.output_path = str(outp)
                    af.error_message = "File exists, skipping"
                    self._update_tree_row(af); return

                if str(outp.resolve()) == str(Path(af.path).resolve()):
                    af.status = ProcessingStatus.FAILED
                    af.error_message = "Would overwrite source; refusing to process"
                    self._update_tree_row(af); return

                if outp.exists() and not self.settings.overwrite_existing:
                    base = outp.stem
                    ext = outp.suffix
                    counter = 1
                    while outp.exists():
                        outp = outp.parent / f"{base}_{counter:03d}{ext}"
                        counter += 1
                    af.output_path = str(outp)

                outp.parent.mkdir(parents=True, exist_ok=True)
                af.output_path = str(outp)

                def cb(kind: str, value: float) -> None:
                    if kind == "progress":
                        self._update_tree_status_text(af, f"Processing {value:5.1f}%")

                ok, err = self.proc.process_file(af, self.settings, outp, progress_callback=cb, stop_event=self._stop_event)
                if ok:
                    af.status = ProcessingStatus.COMPLETED
                    af.error_message = None
                else:
                    af.status = ProcessingStatus.SKIPPED if err == "Cancelled" else ProcessingStatus.FAILED
                    af.error_message = err
                self._update_tree_row(af)
            except Exception as e:
                af.status = ProcessingStatus.FAILED
                af.error_message = str(e)
                self._update_tree_row(af)

        def _output_path_for(self, af: AudioFile) -> Path:
            ext = self.proc.format_to_extension(self.settings.output_format)
            src = Path(af.path)
            placeholders = {
                "stem": src.stem,
                "ext": ext,
                "index": 1,
                "artist": self.meta_artist.get().format(stem=src.stem, ext=ext, index=1) if self.meta_artist.get() else "",
                "title": self.meta_title.get().format(stem=src.stem, ext=ext, index=1) if self.meta_title.get() else src.stem,
            }
            fname = self.template_var.get().format(**placeholders)
            outdir = Path(self.output_dir_var.get() or self.settings.output_directory or src.parent)
            return outdir / fname

        def _stop_processing(self) -> None:
            self._stop_event.set()
            self._log("Stop requested. Running jobs will finish or cancel shortly.", "warn")

        def _update_overall_progress(self, force_done: bool = False) -> None:
            total = len(self.audio_files)
            if total == 0:
                self.progress["value"] = 0; return
            if force_done:
                self.progress["value"] = 100; return
            done = sum(1 for af in self.audio_files if af.status == ProcessingStatus.COMPLETED)
            running = sum(1 for af in self.audio_files if af.status == ProcessingStatus.PROCESSING)
            pct = (done / total) * 100.0 + (running / total) * 15.0
            self.progress["value"] = min(100.0, pct)

        def _show_manual(self):
            win = tk.Toplevel(self); win.title("User Manual"); win.geometry("900x700")
            txt = tk.Text(win, wrap="word"); txt.pack(fill="both", expand=True); txt.insert("1.0", self.user_manual); txt.config(state="disabled")

        def _show_power_guide(self):
            win = tk.Toplevel(self); win.title("Power Guide"); win.geometry("900x700")
            txt = tk.Text(win, wrap="word")
            txt.pack(fill="both", expand=True)
            txt.insert("1.0", self.power_guide + "\n\n" + self.cookbook)
            txt.config(state="disabled")

        def _show_ffmpeg_help(self):
            pass
        def _show_downloads(self):
            pass
        def _show_about(self):
            pass
        def _check_ffmpeg_dialog(self):
            pass
        def _startup_ffmpeg_check(self):
            pass
        def _check_ffmpeg(self):
            pass
        def _apply_settings_to_ui(self, s):
            pass
        def _save_preset(self):
            pass
        def _load_preset(self):
            pass
        def _export_report(self):
            pass
        def _update_tree_row(self, af: AudioFile) -> None:
            if self.tree.exists(af.path):
                self.tree.item(af.path, values=(
                    af.format.upper(),
                    f"{af.duration:.1f}" if af.duration else "",
                    f"{af.size / (1024*1024):.1f}",
                    af.status.value,
                    af.error_message or "",
                    af.output_path or "",
                ))
        def _update_tree_status_text(self, af: AudioFile, text_status: str) -> None:
            if self.tree.exists(af.path):
                vals = list(self.tree.item(af.path, "values"))
                vals[3] = text_status
                self.tree.item(af.path, values=tuple(vals))
        def _choose_output_dir(self) -> None:
            d = filedialog.askdirectory(title="Choose Output Folder")
            if d: self.output_dir_var.set(d)
        def _choose_watch_folder(self) -> None:
            d = filedialog.askdirectory(title="Choose Watch Folder")
            if d: self.watch_path_var.set(d)
        def _refresh_user_presets(self) -> None:
            self.user_preset_list.delete(0, "end")
            for name in self.preset_mgr.list_user_presets():
                self.user_preset_list.insert("end", name)
        def _load_builtin_preset(self) -> None:
            sel: Tuple[int, ...] = self.preset_list.curselection()
            if not sel: return
            name: str = self.preset_list.get(sel[0])
            s = self.preset_mgr.load_builtin(name)
            self._apply_settings_to_ui(s)
            self.settings = s
            self._log(f"Loaded preset: {name}", "info")
        def _load_user_preset(self) -> None:
            sel: Tuple[int, ...] = self.user_preset_list.curselection()
            if not sel:
                messagebox.showinfo("Presets", "Select a user preset to load."); return
            name: str = self.user_preset_list.get(sel[0])
            try:
                s = self.preset_mgr.load_user_preset(name)
                self._apply_settings_to_ui(s); self.settings = s
                self._log(f"Loaded user preset: {name}", "info")
            except Exception as e:
                messagebox.showerror("Preset Error", str(e))
        def _on_format_changed(self) -> None:
            fmt = self.format_var.get().lower()
            if fmt == "mp3":
                self.quality_combo.configure(values=["V0","V1","V2","V3","V4"])
                if self.quality_var.get() not in {"V0","V1","V2","V3","V4"}:
                    self.quality_var.set("V2")
            elif fmt in {"aac","m4a"}:
                self.quality_combo.configure(values=["192k","224k","256k","320k"])
                if not str(self.quality_var.get()).endswith("k"):
                    self.quality_var.set("256k")
            elif fmt == "ogg":
                self.quality_combo.configure(values=[str(i) for i in range(0,11)])
                if self.quality_var.get() not in {str(i) for i in range(0,11)}:
                    self.quality_var.set("6")
            elif fmt == "opus":
                self.quality_combo.configure(values=["64k","96k","128k","160k","192k","256k","320k"])
                if not str(self.quality_var.get()).endswith("k"):
                    self.quality_var.set("128k")
            else:
                self.quality_combo.configure(values=[])
            self.bit_depth_combo.configure(state="readonly" if fmt == "wav" else "disabled")
        def _start_watch(self) -> None:
            path = self.watch_path_var.get().strip()
            if not path:
                messagebox.showinfo("Watch", "Choose a folder to watch."); return
            folder = Path(path)
            if not folder.exists():
                messagebox.showerror("Watch", "Folder does not exist."); return
            if self._watcher:
                self._watcher.stop(); self._watcher = None
            self._watcher = FolderWatcher(folder, self.poll_var.get(), self._enqueue_files)
            self._watcher.start()
            self._log(f"Started watching: {folder} (poll {self.poll_var.get()}s)", "info")
        def _stop_watch(self) -> None:
            if self._watcher:
                self._watcher.stop()
                self._watcher = None
                self._log("Stopped watching folder.", "info")
        def _refresh_diag(self) -> None:
            if not FFMPEG.is_available():
                txt = "FFmpeg: Not Found\n\nInstall from https://ffmpeg.org/download.html"
            else:
                vi = FFMPEG.get_version_info()
                txt = (
                    f"FFmpeg: {vi.get('ffmpeg_version','?')}\n"
                    f"FFprobe: {vi.get('ffprobe_version','?')}\n"
                    f"ffmpeg path: {vi.get('ffmpeg_path','?')}\n"
                    f"ffprobe path: {vi.get('ffprobe_path','?')}\n"
                )
            self.diag_text.delete("1.0", "end")
            self.diag_text.insert("1.0", txt)

else:
    class MusicForgeApp:
        def __init__(self):
            raise RuntimeError("Tkinter is not available, cannot run the GUI.")

def gui_main() -> int:
    if not tk_available:
        print("Tkinter is not available in this environment. Use CLI mode.", file=sys.stderr)
        return 1
    app = MusicForgeApp()
    app.mainloop()
    return 0
