/*
 * The Coop — Service Worker
 * Offline-capable PWA for the woods outside East Glacier.
 *
 * Strategy:
 * - Static assets: cache-first (CSS, JS, fonts, icons)
 * - HTML pages: network-first, fall back to cache
 * - API GETs: network-first, cache response for offline reads
 * - API POSTs: if offline, queue in IndexedDB, sync when back online
 */

const CACHE_VERSION = 2;
const STATIC_CACHE = `coop-static-v${CACHE_VERSION}`;
const DYNAMIC_CACHE = `coop-dynamic-v${CACHE_VERSION}`;
const QUEUE_STORE = "offline-queue";
const QUEUE_DB = "coop-offline";

// Pages to precache for offline shell
const PRECACHE = [
  "/",
  "/hours/",
  "/hours/log/",
  "/inventory/",
  "/approvals/",
  "/manifest.json",
];

// ── Install — precache app shell ────────────────────────────────────

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

// ── Activate — clean old caches ─────────────────────────────────────

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== STATIC_CACHE && k !== DYNAMIC_CACHE)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch — route requests to the right strategy ────────────────────

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET/POST, skip external URLs
  if (url.origin !== self.location.origin) return;

  // API POST/PUT — queue if offline
  if (url.pathname.startsWith("/api/") && event.request.method !== "GET") {
    event.respondWith(networkOrQueue(event.request));
    return;
  }

  // API GET — network first, cache fallback
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirstWithCache(event.request, DYNAMIC_CACHE));
    return;
  }

  // Static assets — cache first
  if (
    url.pathname.startsWith("/static/") ||
    url.pathname === "/manifest.json" ||
    url.pathname === "/sw.js"
  ) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // HTML pages — network first, cache fallback
  if (event.request.mode === "navigate" || event.request.headers.get("accept")?.includes("text/html")) {
    event.respondWith(networkFirstWithCache(event.request, DYNAMIC_CACHE));
    return;
  }

  // Everything else — network with cache fallback
  event.respondWith(cacheFirst(event.request));
});

// ── Strategies ──────────────────────────────────────────────────────

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Offline and not cached — return a basic offline response
    return new Response("Offline", { status: 503, statusText: "Offline" });
  }
}

async function networkFirstWithCache(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;

    // If it's a page request, return the cached homepage as a shell
    if (request.mode === "navigate") {
      const shell = await caches.match("/");
      if (shell) return shell;
    }

    return new Response("Offline — this page hasn't been cached yet", {
      status: 503,
      headers: { "Content-Type": "text/html" },
    });
  }
}

// ── Offline Queue — store failed writes, replay later ───────────────

async function networkOrQueue(request) {
  try {
    return await fetch(request);
  } catch {
    // Offline — queue the request for later
    const body = await request.text();
    await queueRequest({
      url: request.url,
      method: request.method,
      headers: Object.fromEntries(request.headers.entries()),
      body: body,
      timestamp: Date.now(),
    });

    // Return a synthetic success so the UI doesn't break
    return new Response(
      JSON.stringify({
        ok: true,
        queued: true,
        message: "Saved offline — will sync when back online",
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

// ── IndexedDB helpers for the offline queue ─────────────────────────

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(QUEUE_DB, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(QUEUE_STORE, {
        keyPath: "id",
        autoIncrement: true,
      });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function queueRequest(data) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, "readwrite");
    tx.objectStore(QUEUE_STORE).add(data);
    tx.oncomplete = () => {
      resolve();
      // Notify all clients about the queued item
      self.clients.matchAll().then((clients) => {
        clients.forEach((client) =>
          client.postMessage({ type: "QUEUED", message: data.url })
        );
      });
    };
    tx.onerror = () => reject(tx.error);
  });
}

async function getQueuedRequests() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, "readonly");
    const req = tx.objectStore(QUEUE_STORE).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function clearQueuedRequest(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, "readwrite");
    tx.objectStore(QUEUE_STORE).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

// ── Sync — replay queued requests when back online ──────────────────

async function replayQueue() {
  const queued = await getQueuedRequests();
  if (queued.length === 0) return;

  let synced = 0;
  for (const item of queued) {
    try {
      const response = await fetch(item.url, {
        method: item.method,
        headers: item.headers,
        body: item.body,
      });
      if (response.ok) {
        await clearQueuedRequest(item.id);
        synced++;
      }
    } catch {
      // Still offline — stop trying
      break;
    }
  }

  if (synced > 0) {
    self.clients.matchAll().then((clients) => {
      clients.forEach((client) =>
        client.postMessage({
          type: "SYNCED",
          count: synced,
        })
      );
    });
  }
}

// Listen for online event from clients
self.addEventListener("message", (event) => {
  if (event.data === "REPLAY_QUEUE") {
    replayQueue();
  }
});

// Background sync if the browser supports it
self.addEventListener("sync", (event) => {
  if (event.tag === "replay-queue") {
    event.waitUntil(replayQueue());
  }
});
