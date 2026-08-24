#!/usr/bin/env python3
"""CAMDOWN background server — runs the local web API silently for the browser extension.

Also serves the full web UI at http://127.0.0.1:5000. Shows a system tray
icon so you can tell it's running, open the web UI, or quit it.

Run:
    python camdown_server.py
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path

import pystray
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from webapp.app import app  # noqa: E402


def resource_path(*parts: str) -> Path:
    """Locate a bundled read-only asset, whether run from source or a PyInstaller .exe."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


LOGO_PATH = resource_path("images", "logo", "CAMBO .png")


def run_flask() -> None:
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)


def open_ui(icon, item) -> None:
    webbrowser.open("http://127.0.0.1:5000")


def quit_app(icon, item) -> None:
    icon.stop()
    os._exit(0)


def main() -> None:
    threading.Thread(target=run_flask, daemon=True).start()

    image = Image.open(LOGO_PATH) if LOGO_PATH.exists() else Image.new("RGB", (64, 64), "black")
    menu = pystray.Menu(
        pystray.MenuItem("Open CAMDOWN", open_ui, default=True),
        pystray.MenuItem("Quit", quit_app),
    )
    pystray.Icon("CAMDOWN", image, "CAMDOWN — running in background", menu).run()


if __name__ == "__main__":
    main()
