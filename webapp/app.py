#!/usr/bin/env python3
"""CAMDOWN — local web UI for fb_downloader.py (Facebook, YouTube & TikTok), built with Flask + Bootstrap.

Run:
    python webapp/app.py
Then open http://127.0.0.1:5000 in your browser (it opens automatically).
"""

import os
import sys
import threading
import uuid
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import load_config, resolve_output_dir, save_config  # noqa: E402
from fb_downloader import download  # noqa: E402

app = Flask(__name__)

IS_RENDER = bool(os.environ.get("RENDER"))

jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def run_job(job_id: str, url: str, output_dir: str, quality: str) -> None:
    def hook(d):
        with jobs_lock:
            job = jobs[job_id]
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                job["percent"] = round(downloaded / total * 100, 1) if total else job["percent"]
                job["log"].append(f"Downloading... {d.get('_percent_str', '').strip()} at {d.get('_speed_str', '').strip()}")
            elif d.get("status") == "finished":
                job["log"].append("Download finished, merging/post-processing...")

    with jobs_lock:
        jobs[job_id] = {"status": "running", "percent": 0, "log": [f"Starting: {url}"]}

    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        file_path = download(url, output_dir, quality, progress_hooks=[hook])
        with jobs_lock:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["percent"] = 100
            jobs[job_id]["file_path"] = str(file_path)
            jobs[job_id]["file_name"] = file_path.name
            jobs[job_id]["log"].append(f"Done! Saved to: {file_path}")
    except Exception as e:
        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["log"].append(f"Failed: {e}")


@app.route("/")
def index():
    config = load_config()
    return render_template(
        "index.html",
        default_output=str(resolve_output_dir()),
        default_quality=config["quality"],
        is_render=IS_RENDER,
    )


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip()
    quality = (data.get("quality") or load_config()["quality"]).strip()
    output_dir = str(resolve_output_dir(data.get("output")))

    if not url:
        return jsonify({"error": "URL is required"}), 400

    save_config(output_dir=data.get("output") or None, quality=quality)

    job_id = uuid.uuid4().hex
    thread = threading.Thread(target=run_job, args=(job_id, url, output_dir, quality), daemon=True)
    thread.start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": "Unknown job"}), 404
        return jsonify(job)


@app.route("/api/file/<job_id>")
def file(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or job.get("status") != "done" or "file_path" not in job:
        return jsonify({"error": "File not ready"}), 404
    return send_file(job["file_path"], as_attachment=True, download_name=job["file_name"])


if __name__ == "__main__":
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
