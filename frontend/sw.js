const CACHE = "search-shell-v21";
const SHELL = ["/", "/index.html", "/styles.css?v=21", "/app.js?v=21"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/thumb-proxy") || url.pathname.startsWith("/thumb/")) return;
  event.respondWith(
    fetch(new Request(event.request, { cache: "no-store" })).catch(() => caches.match(event.request))
  );
});
