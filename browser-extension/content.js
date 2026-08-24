(function () {
  const API_BASE = "http://127.0.0.1:5000";
  const DOWNLOAD_ICON =
    '<svg viewBox="0 0 24 24"><path d="M12 16l-6-6h4V4h4v6h4l-6 6zM4 18h16v2H4z"/></svg>';

  let btn = null;
  let toast = null;
  let pollTimer = null;

  function hasVideo() {
    return document.querySelector("video") !== null;
  }

  function ensureUI() {
    if (btn) return;

    btn = document.createElement("div");
    btn.id = "camdown-btn";
    btn.title = "Download this video with CAMDOWN";
    btn.innerHTML = DOWNLOAD_ICON;
    btn.addEventListener("click", startDownload);
    document.documentElement.appendChild(btn);

    toast = document.createElement("div");
    toast.id = "camdown-toast";
    document.documentElement.appendChild(toast);
  }

  function removeUI() {
    if (btn) { btn.remove(); btn = null; }
    if (toast) { toast.remove(); toast = null; }
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  function showToast(text, isError) {
    if (!toast) return;
    toast.textContent = text;
    toast.classList.toggle("camdown-error", !!isError);
    toast.style.display = "block";
  }

  function hideToastLater(delay) {
    setTimeout(() => { if (toast) toast.style.display = "none"; }, delay || 4000);
  }

  function setBusy(busy) {
    if (btn) btn.classList.toggle("camdown-busy", busy);
  }

  async function startDownload() {
    if (pollTimer) return; // a download is already in progress
    const url = window.location.href;
    setBusy(true);
    showToast("Starting download...");

    let res;
    try {
      res = await fetch(`${API_BASE}/api/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, quality: "1080" }),
      });
    } catch (e) {
      setBusy(false);
      showToast("CAMDOWN app isn't running. Start the CAMDOWN web server first.", true);
      hideToastLater(6000);
      return;
    }

    const data = await res.json();
    if (data.error) {
      setBusy(false);
      showToast("Failed: " + data.error, true);
      hideToastLater(6000);
      return;
    }

    pollTimer = setInterval(() => poll(data.job_id), 1000);
  }

  async function poll(jobId) {
    let res, job;
    try {
      res = await fetch(`${API_BASE}/api/status/${jobId}`);
      job = await res.json();
    } catch (e) {
      clearInterval(pollTimer);
      pollTimer = null;
      setBusy(false);
      return;
    }

    if (job.error) {
      clearInterval(pollTimer);
      pollTimer = null;
      setBusy(false);
      return;
    }

    showToast(`Downloading... ${job.percent}%`);

    if (job.status === "done") {
      clearInterval(pollTimer);
      pollTimer = null;
      setBusy(false);
      showToast("✓ Done! Saved.");
      hideToastLater();
    } else if (job.status === "error") {
      clearInterval(pollTimer);
      pollTimer = null;
      setBusy(false);
      const lastLine = job.log && job.log.length ? job.log[job.log.length - 1] : "Unknown error";
      showToast("Failed: " + lastLine, true);
      hideToastLater(6000);
    }
  }

  function sync() {
    if (hasVideo()) {
      ensureUI();
    } else {
      removeUI();
    }
  }

  sync();
  const observer = new MutationObserver(sync);
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
