// Service Worker for Moex PWA

const CACHE_NAME = 'Moex-cache-v3';
const urlsToCache = [
  '/',
  '/static/website/manifest.webmanifest',
  '/static/website/images/favicon.ico',
  '/static/website/images/bg.jpg',
  '/static/website/images/icons/icon-192x192.png',
  '/static/website/images/icons/icon-512x512.png',
  '/riders/static/img/logo.png'
];

// Install service worker and cache resources
self.addEventListener('install', event => {
  // Force the waiting service worker to become active
  self.skipWaiting();
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        
        // Use Promise.allSettled with individual promises that can fail independently
        return Promise.allSettled(
          urlsToCache.map(url => 
            fetch(url, { mode: 'no-cors' })
              .then(response => cache.put(url, response))
              .catch(error => {
                console.warn(`Failed to cache ${url}: ${error.message}`);
              })
          )
        );
      })
  );
});

// Cache and return requests
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request).then(
          response => {
            // Check if we received a valid response
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone the response
            const responseToCache = response.clone();

            caches.open(CACHE_NAME)
              .then(cache => {
                // Don't cache API calls or external resources
                if (event.request.url.indexOf('/api/') === -1) {
                  cache.put(event.request, responseToCache);
                }
              });

            return response;
          }
        );
      })
  );
});

// Update service worker and clear old caches
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
