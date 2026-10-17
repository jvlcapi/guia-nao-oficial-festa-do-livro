// Keeps the site and the catalog on the device so the list works inside the fair tent, where the signal is weak.
// Network first: online visitors get the latest catalog. When the network takes longer than NETWORK_WAIT_MILLISECONDS
// (a phone that shows signal but moves no data), the saved copy answers and the network keeps updating it for next time.
const CACHE_NAME = "guia-nao-oficial-festa-do-livro-v1";
const NETWORK_WAIT_MILLISECONDS = 3000;

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(["./index.html"])));
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(names => Promise.all(names.filter(name => name !== CACHE_NAME).map(name => caches.delete(name))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET" || new URL(request.url).origin !== self.location.origin) return;
  const fromNetwork = fetchAndKeepCopy(request);
  event.waitUntil(fromNetwork.then(result => result.copySaved).catch(() => {}));
  event.respondWith(firstAnswer(request, fromNetwork.then(result => result.response)));
});

// One saved copy per file: the site's address is the same index.html, and a query such as "?fbclid=..." added by a
// social network, or "?versao=2" on the preview image, must not leave an older copy behind under another address.
function savedCopyAddress(request) {
  const address = new URL(request.url);
  address.search = "";
  if (address.pathname === new URL(self.registration.scope).pathname) address.pathname += "index.html";
  return address.href;
}

function pageAddress() {
  return new URL("./index.html", self.registration.scope).href;
}

function fetchAndKeepCopy(request) {
  return fetch(request).then(response => {
    let copySaved = Promise.resolve();
    if (response.ok) {
      const copy = response.clone();
      copySaved = caches.open(CACHE_NAME).then(cache => cache.put(savedCopyAddress(request), copy));
    }
    return { response, copySaved };
  });
}

function savedCopyOf(request) {
  return caches.open(CACHE_NAME).then(cache => cache.match(savedCopyAddress(request))
    .then(saved => saved || (request.mode === "navigate" ? cache.match(pageAddress()) : undefined)));
}

function firstAnswer(request, networkResponse) {
  return new Promise(resolve => {
    let answered = false;
    const answer = response => {
      if (answered || !response) return;
      answered = true;
      resolve(response);
    };
    const waitTimer = setTimeout(() => savedCopyOf(request).then(answer), NETWORK_WAIT_MILLISECONDS);
    networkResponse
      .then(response => {
        clearTimeout(waitTimer);
        answer(response);
      })
      .catch(() => {
        clearTimeout(waitTimer);
        savedCopyOf(request).then(saved => answer(saved || Response.error()));
      });
  });
}
