#!/usr/bin/env python3
"""Desktop GUI for fb_downloader.py, built with Tkinter (no extra dependencies).

Run:
    python fb_downloader_gui.py
"""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from config import load_config, save_config
from fb_downloader import download

QUALITIES = ["2160", "1080", "720", "480", "360"]
LOGO_PATH = Path(__file__).resolve().parent / "images" / "logo" / "CAMBO .png"

ACCENT = "#6366f1"
BG = "#f4f6fb"
CARD_BG = "#ffffff"
TEXT = "#1e293b"
MUTED = "#64748b"
LOG_BG = "#0f172a"
LOG_FG = "#94e2b8"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CAMDOWN")
        self.geometry("600x560")
        self.minsize(560, 520)
        self.configure(bg=BG)

        self.log_queue: queue.Queue = queue.Queue()
        config = load_config()
        self.output_dir = tk.StringVar(value=str(Path(__file__).resolve().parent / config["output_dir"]))
        self.quality = tk.StringVar(value=config["quality"])
        self.url_var = tk.StringVar()

        self._load_logo()
        self._build_style()
        self._build_widgets()
        self.output_dir.trace_add("write", self._save_preferences)
        self.quality.trace_add("write", self._save_preferences)
        self.after(100, self._drain_log_queue)

    def _save_preferences(self, *_args):
        save_config(output_dir=self.output_dir.get().strip(), quality=self.quality.get())

    def _load_logo(self):
        self.logo_img = None
        self.logo_icon = None
        if LOGO_PATH.exists():
            try:
                full = tk.PhotoImage(file=str(LOGO_PATH))
                factor = max(1, full.width() // 72)
                self.logo_img = full.subsample(factor, factor)
                self.iconphoto(True, full.subsample(max(1, full.width() // 32)))
            except tk.TclError:
                self.logo_img = None

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD_BG)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 16, "bold"))
        style.configure("Section.TLabel", background=CARD_BG, foreground=MUTED, font=("Segoe UI", 9, "bold"))

        style.configure("TEntry", padding=6, fieldbackground="#ffffff")
        style.configure("TCombobox", padding=6)

        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="white",
            font=("Segoe UI", 11, "bold"),
            padding=10,
            borderwidth=0,
        )
        style.map("Accent.TButton", background=[("active", "#4f46e5"), ("disabled", "#a5a6f5")])

        style.configure("TButton", padding=6)
        style.configure(
            "Accent.Horizontal.TProgressbar", troughcolor="#e2e8f0", background=ACCENT, thickness=8
        )

    def _build_widgets(self):
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill="x", padx=24, pady=(24, 12))

        if self.logo_img:
            tk.Label(header, image=self.logo_img, bg=BG).pack(side="left", padx=(0, 12))
        header_text = ttk.Frame(header, style="TFrame")
        header_text.pack(side="left", anchor="center")
        ttk.Label(header_text, text="CAMDOWN", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header_text, text="Facebook · YouTube · TikTok · Instagram · Pinterest", style="Muted.TLabel"
        ).pack(anchor="w")

        card = ttk.Frame(self, style="Card.TFrame")
        card.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        inner = ttk.Frame(card, style="Card.TFrame")
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(inner, text="VIDEO URL", style="Section.TLabel").pack(anchor="w")
        url_row = ttk.Frame(inner, style="Card.TFrame")
        url_row.pack(fill="x", pady=(4, 14))
        url_entry = ttk.Entry(url_row, textvariable=self.url_var)
        url_entry.pack(side="left", fill="x", expand=True)
        self._add_paste_menu(url_entry)
        ttk.Button(url_row, text="Clear", command=lambda: self.url_var.set("")).pack(side="left", padx=(6, 0))

        row = ttk.Frame(inner, style="Card.TFrame")
        row.pack(fill="x", pady=(0, 14))

        col_left = ttk.Frame(row, style="Card.TFrame")
        col_left.pack(side="left", fill="x", expand=True)
        ttk.Label(col_left, text="SAVE TO", style="Section.TLabel").pack(anchor="w")
        folder_row = ttk.Frame(col_left, style="Card.TFrame")
        folder_row.pack(fill="x", pady=(4, 0))
        folder_entry = ttk.Entry(folder_row, textvariable=self.output_dir)
        folder_entry.pack(side="left", fill="x", expand=True)
        self._add_paste_menu(folder_entry)
        ttk.Button(folder_row, text="Browse", command=self._browse_folder).pack(side="left", padx=(6, 0))
        ttk.Label(
            col_left, text="Videos are auto-sorted into a subfolder per platform", style="Card.TLabel"
        ).pack(anchor="w", pady=(4, 0))

        col_right = ttk.Frame(row, style="Card.TFrame")
        col_right.pack(side="left", padx=(14, 0))
        ttk.Label(col_right, text="QUALITY", style="Section.TLabel").pack(anchor="w")
        ttk.Combobox(
            col_right, textvariable=self.quality, values=QUALITIES, state="readonly", width=8
        ).pack(pady=(4, 0))

        self.download_btn = ttk.Button(
            inner, text="Download", style="Accent.TButton", command=self._start_download
        )
        self.download_btn.pack(fill="x", pady=(4, 14))

        self.progress = ttk.Progressbar(inner, style="Accent.Horizontal.TProgressbar", mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 14))

        ttk.Label(inner, text="ACTIVITY LOG", style="Section.TLabel").pack(anchor="w")
        log_frame = tk.Frame(inner, bg=LOG_BG)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))
        self.log_text = tk.Text(
            log_frame, height=10, state="disabled", wrap="word",
            bg=LOG_BG, fg=LOG_FG, insertbackground=LOG_FG,
            relief="flat", padx=10, pady=10, font=("Consolas", 9),
        )
        self.log_text.pack(fill="both", expand=True)

        ttk.Label(
            self, text="សូមទាញយកតែវីឌេអូដែលអ្នកមានសិទ្ធិ ឬបានទទួលការអនុញ្ញាតប៉ុណ្ណោះ", style="Muted.TLabel"
        ).pack(pady=(0, 14))

    def _add_paste_menu(self, entry: ttk.Entry):
        menu = tk.Menu(entry, tearoff=0)
        menu.add_command(label="Cut", command=lambda: entry.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: entry.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: entry.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: entry.selection_range(0, "end"))
        entry.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_dir.get() or ".")
        if folder:
            self.output_dir.set(folder)

    def _append_log(self, text: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _drain_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if item == "__DONE__":
                    self._on_download_finished()
                else:
                    self._append_log(item)
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(
                "Missing URL", "Please paste a Facebook, YouTube, TikTok, Instagram, or Pinterest video URL."
            )
            return

        output_dir = self.output_dir.get().strip() or "downloads"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        self.download_btn.configure(state="disabled")
        self.progress.start(12)
        self._append_log(f"Starting download: {url}")

        thread = threading.Thread(
            target=self._run_download, args=(url, output_dir, self.quality.get()), daemon=True
        )
        thread.start()

    def _run_download(self, url: str, output_dir: str, quality: str):
        def hook(d):
            if d.get("status") == "downloading":
                pct = d.get("_percent_str", "").strip()
                speed = d.get("_speed_str", "").strip()
                self.log_queue.put(f"Downloading... {pct} at {speed}")
            elif d.get("status") == "finished":
                self.log_queue.put("Download finished, merging/post-processing...")

        try:
            download(url, output_dir, quality, progress_hooks=[hook])
            self.log_queue.put("Done! Saved to: " + str(Path(output_dir).resolve()))
        except Exception as e:
            self.log_queue.put(f"Failed: {e}")
        finally:
            self.log_queue.put("__DONE__")

    def _on_download_finished(self):
        self.progress.stop()
        self.download_btn.configure(state="normal")


if __name__ == "__main__":
    App().mainloop()
