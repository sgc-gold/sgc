// SGC shared SSO: protected HTML, JSON and API data are never cached offline.
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(
  caches.keys().then(keys=>Promise.all(keys.filter(k=>/^sgc-portal-v[0-9]+$/.test(k)).map(k=>caches.delete(k))))
    .then(()=>self.clients.claim())
));
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin||url.pathname.startsWith('/auth/'))return;
  event.respondWith(fetch(event.request,{cache:'no-store'}));
});
self.addEventListener('message',event=>{if(event.data?.type==='SKIP_WAITING')self.skipWaiting();});
