/**
 * Adaptador de ubicación: el GPS del navegador. Es el único archivo que lo
 * usa (lo vigila tests/arquitectura.test.ts). Traduce los errores del
 * navegador a mensajes para la persona.
 */
import type { Coordenadas } from "@/dominio/modelo";
import type { UbicacionRepositorio } from "@/aplicacion/puertos";

const MENSAJES: Record<number, string> = {
  1: "No dio permiso para usar su ubicación. Puede activarlo en el candado de la barra de direcciones.",
  2: "No se pudo saber dónde está. Pruebe de nuevo con el GPS encendido.",
  3: "La ubicación tardó demasiado. Pruebe de nuevo.",
};

export class UbicacionNavegador implements UbicacionRepositorio {
  actual(): Promise<Coordenadas> {
    const gps = globalThis.navigator?.geolocation;
    if (!gps) return Promise.reject(new Error("Este navegador no puede dar su ubicación."));
    return new Promise((resolver, rechazar) =>
      gps.getCurrentPosition(
        (p) => resolver({ latitud: p.coords.latitude, longitud: p.coords.longitude }),
        (e) => rechazar(new Error(MENSAJES[e.code] ?? "No se pudo obtener su ubicación.")),
        { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 },
      ),
    );
  }
}
