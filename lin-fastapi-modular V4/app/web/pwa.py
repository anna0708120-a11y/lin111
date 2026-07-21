"""
PWA 相关的两个文件内容：manifest.json（告诉系统这是个app、叫什么名字、图标在哪）
和 sw.js（service worker，负责让"加到主屏幕"后感觉像原生app，并做基本快取）。

service worker 刻意写得保守：网页本体每次都优先抢新版本，只有离线时才用快取版本；
只有图片/字体这种不常变的东西走快取优先。API请求完全不碰快取。
这样以后你/我继续更新代码，不会出现"明明部署了新版，手机上加到主屏幕的还是旧的"这种坑。
"""

MANIFEST_JSON = """{
  "name": "Lin",
  "short_name": "Lin",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "background_color": "#FAF8F5",
  "theme_color": "#C9897A",
  "icons": [
    {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}
  ]
}"""

SERVICE_WORKER_JS = """const CACHE_NAME = 'lin-v1';

self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { self.clients.claim(); });

self.addEventListener('fetch', (e) => {
  const req = e.request;

  // 网页本体：永远先试网络拿最新版，只有离线才退回快取
  if (req.mode === 'navigate' || req.destination === 'document') {
    e.respondWith(
      fetch(req)
        .then((res) => {
          caches.open(CACHE_NAME).then((c) => c.put(req, res.clone()));
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // 图片/字体这类不常变的静态资源：快取优先，比较快
  if (req.destination === 'image' || req.destination === 'font') {
    e.respondWith(
      caches.match(req).then(
        (cached) =>
          cached ||
          fetch(req).then((res) => {
            caches.open(CACHE_NAME).then((c) => c.put(req, res.clone()));
            return res;
          })
      )
    );
    return;
  }

  // 其他一律不碰（尤其是 /watch /logs /memory 这些 API），直接打网络
});
"""
