/* Service worker del manual. build.py reemplaza __VERSION__ y __ASSETS__.
   Estrategia: precarga completa en la instalación y "primero la caché" para todo.
   El contenido es estático: una versión nueva llega como un sw.js distinto (cambia VERSION),
   se instala en segundo plano y la página ofrece "Actualizar". */
const VERSION = "__VERSION__";
const CACHE = "manual-aiml-" + VERSION;
const ASSETS = __ASSETS__;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) =>
      // cache: "reload" evita guardar una copia vieja que estuviera en la caché HTTP.
      cache.addAll(ASSETS.map((url) => new Request(url, { cache: "reload" })))
    )
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith("manual-aiml-") && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("message", (event) => {
  if (event.data === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (req.mode === "navigate") {
    // Todas las vistas viven en la página raíz (rutas con #), así que cualquier navegación usa la copia guardada.
    // Se guarda "./" y no "index.html": muchos hostings redirigen /index.html a / y una respuesta
    // redirigida no se puede devolver a una navegación.
    event.respondWith(
      caches.open(CACHE)
        .then((cache) => cache.match(self.registration.scope))
        .then((hit) => hit || fetch(req))
    );
    return;
  }
  event.respondWith(
    caches.open(CACHE)
      .then((cache) => cache.match(req, { ignoreSearch: true }))
      .then((hit) => hit || fetch(req))
  );
});
