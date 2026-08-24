#!/usr/bin/env python3
"""CAMDOWN — download videos from Facebook, YouTube, TikTok, Instagram, or Pinterest using yt-dlp.

Usage:
    python fb_downloader.py <video_url> [-o OUTPUT_DIR] [-q QUALITY]
    python fb_downloader.py -f urls.txt [-o OUTPUT_DIR]

Only download videos you own or have permission to download.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

from config import get_app_root, load_config, resolve_output_dir, save_config

try:
    import yt_dlp
except ImportError:
    print("Missing dependency. Install it first:\n  pip install -r requirements.txt")
    sys.exit(1)

PLATFORM_DOMAINS = {
    "Facebook": ("facebook.com", "fb.watch"),
    "YouTube": ("youtube.com", "youtu.be"),
    "TikTok": ("tiktok.com",),
    "Instagram": ("instagram.com",),
    "Pinterest": ("pinterest.com", "pin.it"),
}


def detect_platform(url: str) -> str:
    """Map a URL's domain to a platform folder name, e.g. 'facebook.com' -> 'Facebook'."""
    host = urlparse(url).netloc.lower()
    for prefix in ("www.", "m.", "mobile."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    for platform, domains in PLATFORM_DOMAINS.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return platform
    return "Other"


def find_ffmpeg() -> str | None:
    """Return a directory containing an ffmpeg binary: PATH, winget (Windows), then a bundled static build."""
    on_path = shutil.which("ffmpeg")
    if on_path:
        return str(Path(on_path).parent)

    winget_root = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    if winget_root.is_dir():
        for candidate in winget_root.glob("Gyan.FFmpeg*/**/ffmpeg.exe"):
            return str(candidate.parent)

    try:
        import imageio_ffmpeg
        return str(Path(imageio_ffmpeg.get_ffmpeg_exe()).parent)
    except ImportError:
        return None


def find_cookies_file() -> str | None:
    """Locate a cookies.txt (Netscape format) for authenticating with sites like YouTube.

    Checks, in order: the COOKIES_FILE env var, Render's secret-file mount point,
    and a cookies.txt next to this script (kept out of git via .gitignore).
    """
    env_path = os.environ.get("COOKIES_FILE")
    if env_path and Path(env_path).is_file():
        return env_path

    candidates = [
        Path("/etc/secrets/cookies.txt"),
        get_app_root() / "cookies.txt",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def download(url: str, output_dir: str, quality: str, progress_hooks=None) -> Path:
    """Download url into output_dir/<platform>/ and return the path of the final video file."""
    platform_dir = Path(output_dir) / detect_platform(url)
    ydl_opts = {
        "outtmpl": str(platform_dir / "%(title)s.%(ext)s"),
        "format": f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "progress_hooks": progress_hooks or [],
    }
    ffmpeg_dir = find_ffmpeg()
    if ffmpeg_dir:
        ydl_opts["ffmpeg_location"] = ffmpeg_dir
    cookies_file = find_cookies_file()
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = Path(ydl.prepare_filename(info))
        merged = filename.with_suffix(".mp4")
        return merged if merged.exists() else filename


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser(
        description="CAMDOWN — download Facebook, YouTube, TikTok, Instagram, or Pinterest videos."
    )
    parser.add_argument("url", nargs="?", help="Facebook, YouTube, TikTok, Instagram, or Pinterest video URL")
    parser.add_argument("-f", "--file", help="Text file with one URL per line")
    parser.add_argument(
        "-o", "--output", default=None,
        help=f"Output directory (default: saved preference, currently '{config['output_dir']}')",
    )
    parser.add_argument(
        "-q", "--quality", default=None,
        help=f"Max video height in px (default: saved preference, currently '{config['quality']}')",
    )
    parser.add_argument(
        "--set-default", action="store_true",
        help="Remember --output/--quality as the new default for next time",
    )
    args = parser.parse_args()

    if not args.url and not args.file:
        parser.error("Provide a URL or use -f to pass a file of URLs.")

    quality = args.quality or config["quality"]
    output_dir = str(resolve_output_dir(args.output))
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if args.set_default:
        save_config(output_dir=args.output, quality=args.quality)

    urls = []
    if args.url:
        urls.append(args.url)
    if args.file:
        urls.extend(
            line.strip() for line in Path(args.file).read_text(encoding="utf-8").splitlines() if line.strip()
        )

    for url in urls:
        print(f"\n== Downloading ({detect_platform(url)}): {url} ==")
        try:
            download(url, output_dir, quality)
        except Exception as e:
            print(f"Failed to download {url}: {e}")


if __name__ == "__main__":
    main()
