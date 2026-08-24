// Minimal service worker: exists only so the browser considers CAMDOWN an
// installable PWA. No offline caching — this tool needs the network anyway.

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
