// ══════════════════════════════════════════
//  SGC 社内ポータル Service Worker
//  バージョンを変えると全キャッシュが更新されます
// ══════════════════════════════════════════
var CACHE_VERSION = 'sgc-portal-v1';

// キャッシュするファイル（起動に必要な最低限のファイル）
var PRECACHE_URLS = [
  './index.html',
  './manifest.json'
];

// ────────────────────────────────────
//  インストール: 必須ファイルをキャッシュ
// ────────────────────────────────────
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(function(cache) {
      return cache.addAll(PRECACHE_URLS);
    }).then(function() {
      // 即座にアクティブ化（waitingをスキップ）
      return self.skipWaiting();
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

  // Google Apps Script / 外部リクエストはキャッシュしない
  if (
    url.includes('script.google.com') ||
    url.includes('fonts.googleapis.com') ||
    url.includes('fonts.gstatic.com') ||
    url.includes('sgc-gold.co.jp') ||
    url.includes('raw.githubusercontent.com')
  ) {
    event.respondWith(fetch(event.request));
    return;
  }

  // 同一オリジンのファイルは Network First（キャッシュフォールバック）
  if (event.request.method === 'GET' && url.startsWith(self.location.origin)) {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          // 成功したらキャッシュを更新
          if (response && response.status === 200) {
            var responseClone = response.clone();
            caches.open(CACHE_VERSION).then(function(cache) {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(function() {
          // ネットワーク失敗時はキャッシュから返す
          return caches.match(event.request).then(function(cached) {
            return cached || caches.match('./index.html');
          });
        })
    );
    return;
  }

  // その他はそのまま通す
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
