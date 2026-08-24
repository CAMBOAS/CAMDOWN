const form = document.getElementById("download-form");
const btn = document.getElementById("download-btn");
const spinner = document.getElementById("btn-spinner");
const progressBar = document.getElementById("progress-bar");
const logBox = document.getElementById("log");
const urlInput = document.getElementById("url");
const clearUrlBtn = document.getElementById("clear-url");
const saveFileBtn = document.getElementById("save-file");

let pollTimer = null;

function appendLog(lines) {
  logBox.textContent = lines.join("\n");
  logBox.scrollTop = logBox.scrollHeight;
}

function setBusy(busy) {
  btn.disabled = busy;
  spinner.classList.toggle("d-none", !busy);
}

async function poll(jobId) {
  const res = await fetch(`/api/status/${jobId}`);
  const job = await res.json();
  if (job.error) {
    clearInterval(pollTimer);
    setBusy(false);
    return;
  }

  appendLog(job.log);
  progressBar.style.width = `${job.percent}%`;

  if (job.status === "done" || job.status === "error") {
    clearInterval(pollTimer);
    setBusy(false);
    progressBar.classList.toggle("bg-danger", job.status === "error");
    if (job.status === "done") {
      saveFileBtn.href = `/api/file/${jobId}`;
      saveFileBtn.classList.remove("d-none");
    }
  }
}

clearUrlBtn.addEventListener("click", () => {
  urlInput.value = "";
  urlInput.focus();
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = document.getElementById("url").value.trim();
  const output = document.getElementById("output")?.value.trim() || "";
  const quality = document.getElementById("quality").value;

  if (!url) return;

  setBusy(true);
  progressBar.classList.remove("bg-danger");
  progressBar.style.width = "0%";
  saveFileBtn.classList.add("d-none");
  appendLog([`Starting: ${url}`]);

  const res = await fetch("/api/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, output, quality }),
  });
  const data = await res.json();

  if (data.error) {
    appendLog([`Failed: ${data.error}`]);
    setBusy(false);
    return;
  }

  pollTimer = setInterval(() => poll(data.job_id), 800);
});
