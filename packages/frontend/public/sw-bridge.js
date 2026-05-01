// 8A MOBILE BRIDGE - Service Worker
// Basic offline support for bridge shell, local queue, and jsqr library

const CACHE_NAME = 'pranely-bridge-v1';
const OFFLINE_URL = '/bridge';

// Assets to cache for offline bridge functionality
const STATIC_ASSETS = [
  '/',
  '/bridge',
  '/manifest.json',
  // Cache jsqr library chunks for offline QR scanning
  '/_next/static/chunks/main-app.js',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).catch(() => {
      // Ignore cache errors during install
    })
  );
  // Activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  // Take control immediately
  self.clients.claim();
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;
  
  // Skip API requests (don't cache)
  if (event.request.url.includes('/api/')) return;
  
  // Skip WebSocket requests
  if (event.request.url.includes('ws://') || event.request.url.includes('wss://')) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Clone and cache successful responses
        if (response.ok) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // Return cached version if network fails
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // For navigation requests, return offline page
          if (event.request.mode === 'navigate') {
            return caches.match(OFFLINE_URL);
          }
          return new Response('Offline', { status: 503 });
        });
      })
  );
});

// Background sync for offline scans
self.addEventListener('sync', (event) => {
  if (event.tag === 'bridge-sync') {
    event.waitUntil(syncOfflineQueue());
  }
});

async function syncOfflineQueue() {
  // This would sync the offline queue when back online
  // For now, just log that sync was triggered
  console.log('[SW] Bridge sync triggered');
}

// Push notification support (optional)
self.addEventListener('push', (event) => {
  if (event.data) {
    const data = event.data.json();
    self.registration.showNotification(data.title || 'PRANELY', {
      body: data.body || 'Nueva actualización del bridge',
      icon: '/icons/icon-192.png',
      badge: '/icons/badge.png',
      tag: 'pranely-bridge',
    });
  }
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow('/bridge')
  );
});
