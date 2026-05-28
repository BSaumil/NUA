// NUA POS service worker — offline-first cache for static shell
const CACHE = 'nua-shell-v1';
const SHELL = ['/', '/pos', '/manifest.json'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // Network-first for API; cache-first for static
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
  } else if (e.request.method === 'GET') {
    e.respondWith(
      caches.match(e.request).then(hit => hit || fetch(e.request).then(resp => {
        const respClone = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, respClone)).catch(() => {});
        return resp;
      }).catch(() => caches.match('/')))
    );
  }
});
