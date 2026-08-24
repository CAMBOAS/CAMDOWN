#!/usr/bin/env python3
"""Desktop GUI for fb_downloader.py, built with CustomTkinter for a modern look.

Run:
    python fb_downloader_gui.py
"""

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from config import load_config, resolve_output_dir, save_config
from fb_downloader import download

QUALITIES = ["2160", "1080", "720", "480", "360"]


def resource_path(*parts: str) -> Path:
    """Locate a bundled read-only asset, whether run from source or a PyInstaller .exe."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


LOGO_PATH = resource_path("images", "logo", "CAMBO .png")

BG = "#0f172a"
CARD_BG = "#f8fafc"
ACCENT = "#6366f1"
ACCENT_HOVER = "#4f46e5"
TEXT = "#1e293b"
MUTED = "#94a3b8"
LOG_BG = "#0f172a"
LOG_FG = "#94e2b8"
ENTRY_BG = "#ffffff"
ENTRY_BORDER = "#e2e8f0"

ctk.set_appearance_mode("light")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CAMDOWN")
        self.geometry("620x720")
        self.minsize(580, 660)
        self.configure(fg_color=BG)

        self.log_queue: queue.Queue = queue.Queue()
        config = load_config()
        self.output_dir = tk.StringVar(value=str(resolve_output_dir()))
        self.quality = tk.StringVar(value=config["quality"])
        self.quality_display = tk.StringVar(value=f"{config['quality']}p")
        self.url_var = tk.StringVar()

        self._set_window_icon()
        self._build_header()
        self._build_card()

        self.output_dir.trace_add("write", self._save_preferences)
        self.quality_display.trace_add("write", self._on_quality_change)
        self.after(100, self._drain_log_queue)

    def _set_window_icon(self):
        if LOGO_PATH.exists():
            try:
                full = tk.PhotoImage(file=str(LOGO_PATH))
                self.iconphoto(True, full.subsample(max(1, full.width() // 32)))
            except tk.TclError:
                pass

    def _save_preferences(self, *_args):
        save_config(output_dir=self.output_dir.get().strip(), quality=self.quality.get())

    def _on_quality_change(self, *_args):
        self.quality.set(self.quality_display.get().rstrip("p"))
        self._save_preferences()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(36, 20))

        if LOGO_PATH.exists():
            img = Image.open(LOGO_PATH)
            self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(72, 72))
            ctk.CTkLabel(header, image=self.logo_img, text="").pack()

        ctk.CTkLabel(
            header, text="CAMDOWN", font=ctk.CTkFont(size=26, weight="bold"), text_color="#f8fafc"
        ).pack(pady=(12, 2))
        ctk.CTkLabel(
            header,
            text="Facebook · YouTube · TikTok · Instagram · Pinterest",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
        ).pack()

    def _build_card(self):
        card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=20)
        card.pack(fill="both", expand=True, padx=28, pady=(0, 28))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=28, pady=28)

        self._section_label(inner, "Video URL")
        url_row = ctk.CTkFrame(inner, fg_color="transparent")
        url_row.pack(fill="x", pady=(6, 16))
        url_entry = ctk.CTkEntry(
            url_row, textvariable=self.url_var, placeholder_text="Paste a video link...",
            corner_radius=10, fg_color=ENTRY_BG, border_color=ENTRY_BORDER, height=38,
        )
        url_entry.pack(side="left", fill="x", expand=True)
        self._add_paste_menu(url_entry)
        ctk.CTkButton(
            url_row, text="✕", width=38, height=38, corner_radius=10,
            fg_color=ENTRY_BG, hover_color="#fef2f2", text_color=MUTED,
            border_color=ENTRY_BORDER, border_width=1,
            command=lambda: self.url_var.set(""),
        ).pack(side="left", padx=(8, 0))

        self._section_label(inner, "Save to")
        folder_row = ctk.CTkFrame(inner, fg_color="transparent")
        folder_row.pack(fill="x", pady=(6, 4))
        folder_entry = ctk.CTkEntry(
            folder_row, textvariable=self.output_dir, corner_radius=10,
            fg_color=ENTRY_BG, border_color=ENTRY_BORDER, height=38,
        )
        folder_entry.pack(side="left", fill="x", expand=True)
        self._add_paste_menu(folder_entry)
        ctk.CTkButton(
            folder_row, text="Browse", width=80, height=38, corner_radius=10,
            fg_color=ENTRY_BG, hover_color="#f1f5f9", text_color=TEXT,
            border_color=ENTRY_BORDER, border_width=1,
            command=self._browse_folder,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            inner, text="Auto-sorted into a subfolder per platform", anchor="w",
            font=ctk.CTkFont(size=11), text_color=MUTED,
        ).pack(fill="x", pady=(0, 16))

        self._section_label(inner, "Quality")
        ctk.CTkOptionMenu(
            inner, values=[f"{q}p" for q in QUALITIES], variable=self.quality_display,
            corner_radius=10, fg_color=ENTRY_BG, button_color="#e2e8f0", button_hover_color="#cbd5e1",
            text_color=TEXT, dropdown_fg_color=ENTRY_BG, dropdown_text_color=TEXT,
            height=38, anchor="w",
        ).pack(fill="x", pady=(6, 20))

        self.download_btn = ctk.CTkButton(
            inner, text="Download", height=48, corner_radius=999,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=ctk.CTkFont(size=15, weight="bold"),
            command=self._start_download,
        )
        self.download_btn.pack(fill="x", pady=(0, 14))

        self.progress = ctk.CTkProgressBar(
            inner, corner_radius=999, height=8, progress_color=ACCENT, fg_color="#e2e8f0",
        )
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 20))

        self._section_label(inner, "Activity Log")
        self.log_text = ctk.CTkTextbox(
            inner, corner_radius=12, fg_color=LOG_BG, text_color=LOG_FG,
            font=ctk.CTkFont(family="Consolas", size=12), wrap="word", height=180,
        )
        self.log_text.pack(fill="both", expand=True, pady=(6, 0))
        self.log_text.insert("end", "Waiting for a link...")
        self.log_text.configure(state="disabled")

    def _section_label(self, parent, text: str):
        ctk.CTkLabel(
            parent, text=text.upper(), anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color=MUTED
        ).pack(fill="x")

    def _add_paste_menu(self, entry: ctk.CTkEntry):
        # CTkEntry is a wrapper; the real tkinter.Entry (which actually receives
        # clicks/keys) lives at entry._entry, so bindings must target that directly.
        target = getattr(entry, "_entry", entry)

        def paste(_event=None):
            try:
                clip = entry.clipboard_get()
            except tk.TclError:
                return "break"
            try:
                target.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            target.insert("insert", clip)
            return "break"

        menu = tk.Menu(entry, tearoff=0)
        menu.add_command(label="Cut", command=lambda: target.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: target.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=paste)
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: target.select_range(0, "end"))
        target.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
        target.bind("<Control-v>", paste)
        target.bind("<Control-V>", paste)

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_dir.get() or ".")
        if folder:
            self.output_dir.set(folder)

    def _append_log(self, text: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self, text: str):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", text + "\n")
        self.log_text.configure(state="disabled")

    def _drain_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if item == "__DONE__":
                    self._on_download_finished()
                elif isinstance(item, tuple) and item[0] == "progress":
                    self.progress.set(item[1])
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
        self.progress.set(0)
        self._clear_log(f"Starting download: {url}")

        thread = threading.Thread(
            target=self._run_download, args=(url, output_dir, self.quality.get()), daemon=True
        )
        thread.start()

    def _run_download(self, url: str, output_dir: str, quality: str):
        def hook(d):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    self.log_queue.put(("progress", downloaded / total))
                pct = d.get("_percent_str", "").strip()
                speed = d.get("_speed_str", "").strip()
                self.log_queue.put(f"Downloading... {pct} at {speed}")
            elif d.get("status") == "finished":
                self.log_queue.put(("progress", 1.0))
                self.log_queue.put("Download finished, merging/post-processing...")

        try:
            file_paths = download(url, output_dir, quality, progress_hooks=[hook])
            for path in file_paths:
                self.log_queue.put("Saved: " + str(path))
            self.log_queue.put(f"Done! {len(file_paths)} file(s) saved.")
        except Exception as e:
            self.log_queue.put(f"Failed: {e}")
        finally:
            self.log_queue.put("__DONE__")

    def _on_download_finished(self):
        self.download_btn.configure(state="normal")


if __name__ == "__main__":
    App().mainloop()
