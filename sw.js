// ══════════════════════════════════════════
//  SGC 社内ポータル Service Worker
//  バージョンを変えると全キャッシュが更新されます
// ══════════════════════════════════════════
var CACHE_VERSION = 'sgc-portal-v6';

// キャッシュするファイル（全ページ + 主要アセット）
var PRECACHE_URLS = [
  './index.html',
  './main.html',
  './portal-theme.css',
  './price.html',
  './market.html',
  './diamond.html',
  './gemstone.html',
  './coin.html',
  './register.html',
  './schedule.html',
  './contacts.html',
  './news.html',
  './youtube.html',
  './manifest.json',
  './image/sgc-icon.png',
  './image/sgc-logo.png',
  './data/tanaka_price.json',
  './data/exchange_rate.json',
  './data/diamonds_2025.json',
  './data/diamonds_2026.json',
  './data/gemstones.json',
  './data/coins.json',
  './data/rapaport.json',
  './data/calibrations.json',
  './data/cuts.json',
  './data/models.json',
  './data/exhibition.json'
];

// ────────────────────────────────────
//  インストール: 必須ファイルをキャッシュ
// ────────────────────────────────────
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(function(cache) {
      // 個別にaddして1ファイル失敗でもインストール継続
      return Promise.allSettled(
        PRECACHE_URLS.map(function(url) {
          return cache.add(url).catch(function(err) {
            console.warn('SW: precache miss:', url, err);
          });
        })
      );
    })
  );
});

// ────────────────────────────────────
//  アクティベート: 古いキャッシュを削除
// ────────────────────────────────────
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames
          .filter(function(name) { return name !== CACHE_VERSION; })
          .map(function(name) { return caches.delete(name); })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// ────────────────────────────────────
//  フェッチ: Network First戦略
//  （外部URL: Google Apps Script等は必ずネットワーク優先）
// ────────────────────────────────────
self.addEventListener('fetch', function(event) {
  var url = event.request.url;

  // 外部リクエストはキャッシュしない
  if (
    url.includes('script.google.com') ||
    url.includes('fonts.googleapis.com') ||
    url.includes('fonts.gstatic.com') ||
    url.includes('sgc-gold.co.jp') ||
    url.includes('cdn.jsdelivr.net') ||
    url.includes('cdnjs.cloudflare.com') ||
    url.includes('googleapis.com')
  ) {
    event.respondWith(fetch(event.request));
    return;
  }

  // GETリクエストのみキャッシュ対象
  if (event.request.method !== 'GET') return;

  // data/*.json は Stale-While-Revalidate（キャッシュを即返しつつバックグラウンド更新）
  if (url.includes('/data/')) {
    event.respondWith(
      caches.open(CACHE_VERSION).then(function(cache) {
        return cache.match(event.request).then(function(cached) {
          var fetchPromise = fetch(event.request).then(function(response) {
            if (response && response.status === 200) {
              cache.put(event.request, response.clone());
            }
            return response;
          }).catch(function() { return cached; });
          return cached || fetchPromise;
        });
      })
    );
    return;
  }

  // HTML・画像等は Network First（キャッシュフォールバック）
  if (url.startsWith(self.location.origin) || url.includes('sgc-gold.github.io')) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          if (response && response.status === 200) {
            var responseClone = response.clone();
            caches.open(CACHE_VERSION).then(function(cache) {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(function() {
          return caches.match(event.request).then(function(cached) {
            return cached || caches.match('./index.html');
          });
        })
    );
    return;
  }

  event.respondWith(fetch(event.request));
});

// ────────────────────────────────────
//  メッセージ受信: SKIP_WAITING（アップデート適用）
// ────────────────────────────────────
self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
