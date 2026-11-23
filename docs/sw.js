// Service worker mínimo: permite instalar la app; no guarda nada en caché (los datos siempre vienen de la app).
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
