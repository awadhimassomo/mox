// Service Worker for Moex

const CACHE_NAME = 'Moex-cache-v6';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/website/manifest.webmanifest',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/favicon.ico',
  '/riders/static/img/logo.png'
];

// Install event - cache assets
self.addEventListener('install', event => {
  // Force the waiting service worker to become the active service worker
  self.skipWaiting();
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        
        // Use Promise.all with individual promises that can fail independently
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

// Fetch event - serve from cache if available
self.addEventListener('fetch', event => {
  // Skip cross-origin requests like the Tailwind CDN
  if (!event.request.url.startsWith(self.location.origin) && 
      !event.request.url.includes('cdn.jsdelivr.net')) {
    return;
  }
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        
        // Clone the request because it's a one-time use
        const fetchRequest = event.request.clone();
        
        return fetch(fetchRequest)
          .then(response => {
            // Check if we received a valid response
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            // Clone the response because it's a one-time use
            const responseToCache = response.clone();
            
            // Cache new resources
            caches.open(CACHE_NAME)
              .then(cache => {
                // Don't cache API calls or dynamic content
                if (!event.request.url.includes('/api/')) {
                  cache.put(event.request, responseToCache);
                }
              })
              .catch(error => {
                console.warn('Failed to update cache for', event.request.url, error);
              });
            
            return response;
          })
          .catch(error => {
            console.warn('Fetch failed:', error);
            // For navigational requests, try to return the offline page
            if (event.request.mode === 'navigate') {
              return caches.match('/');
            }
            throw error;
          });
      })
  );
});

// Activate event - clean up old caches and take control immediately
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  
  // Take control of all clients as soon as it activates
  event.waitUntil(
    Promise.all([
      clients.claim(),
      // Clean up old caches
      caches.keys()
        .then(cacheNames => {
          return Promise.all(
            cacheNames.map(cacheName => {
              if (cacheWhitelist.indexOf(cacheName) === -1) {
                return caches.delete(cacheName);
              }
            })
          );
        })
    ])
  );
});