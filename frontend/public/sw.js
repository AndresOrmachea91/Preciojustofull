/*
 * Service worker de PrecioJusto: lo justo para que se pueda instalar en el
 * celular y abra aunque la señal en el mercado sea mala.
 *
 * - La página (navegación) va a la red primero; sin red, la última guardada.
 * - Los archivos de /assets/ llevan un hash en el nombre: se guardan y se
 *   sirven del caché (nunca cambian; una versión nueva trae otros nombres).
 * - La API NO se guarda: un precio viejo mostrado como actual sería mentir.
 */
const CACHE = "preciojusto-v1";

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(CACHE).then((c) => c.addAll(["/", "/manifest.json", "/icono-192.png"])));
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys().then((claves) => Promise.all(claves.filter((k) => k !== CACHE).map((k) => caches.delete(k)))),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (evento) => {
  const { request } = evento;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    evento.respondWith(
      fetch(request)
        .then((respuesta) => {
          const copia = respuesta.clone();
          caches.open(CACHE).then((c) => c.put("/", copia));
          return respuesta;
        })
        .catch(() => caches.match("/")),
    );
    return;
  }

  if (url.pathname.startsWith("/assets/")) {
    evento.respondWith(
      caches.match(request).then(
        (guardada) =>
          guardada ||
          fetch(request).then((respuesta) => {
            const copia = respuesta.clone();
            caches.open(CACHE).then((c) => c.put(request, copia));
            return respuesta;
          }),
      ),
    );
  }
});
