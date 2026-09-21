/**
 * La regla no negociable del frontend, verificada sobre los archivos:
 * ningún componente, hook, caso de uso ni tipo del dominio llama a fetch
 * ni importa el cliente HTTP. Solo el adaptador de infraestructura sabe
 * que existe la red, y solo el componente del mapa sabe que existe Leaflet.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const RAIZ = join(__dirname, "..", "src");

function archivos(carpeta: string): string[] {
  const salida: string[] = [];
  for (const nombre of readdirSync(carpeta)) {
    const ruta = join(carpeta, nombre);
    if (statSync(ruta).isDirectory()) salida.push(...archivos(ruta));
    else if (/\.(ts|tsx)$/.test(nombre)) salida.push(ruta);
  }
  return salida;
}

function infracciones(carpeta: string, prohibidos: RegExp[]): string[] {
  return archivos(join(RAIZ, carpeta)).flatMap((ruta) => {
    const texto = readFileSync(ruta, "utf-8");
    return prohibidos.filter((p) => p.test(texto)).map((p) => `${ruta.replace(RAIZ, "src")} contiene ${p}`);
  });
}

const RED = [/\bfetch\s*\(/, /infraestructura\/http/, /XMLHttpRequest/];

describe("arquitectura del frontend", () => {
  it("ningún componente ni hook de la interfaz llama a fetch ni conoce el adaptador HTTP", () => {
    expect(infracciones("ui", RED)).toEqual([]);
  });

  it("los casos de uso y el dominio no conocen la red ni React ni Leaflet", () => {
    expect(infracciones("aplicacion", [...RED, /from "react"/, /from "leaflet"/])).toEqual([]);
    expect(infracciones("dominio", [...RED, /from "react"/, /from "leaflet"/, /@\/aplicacion/, /@\/infraestructura/])).toEqual([]);
  });

  it("solo el componente del mapa importa Leaflet", () => {
    const conLeaflet = archivos(RAIZ)
      .filter((r) => /from "leaflet"/.test(readFileSync(r, "utf-8")))
      .map((r) => r.replace(RAIZ, "src").replace(/\\/g, "/"));
    expect(conLeaflet).toEqual(["src/ui/componentes/MapaPuntosVenta.tsx"]);
  });

  it("solo el cliente HTTP llama a fetch", () => {
    const conFetch = archivos(RAIZ)
      .filter((r) => /\bfetch\s*\(/.test(readFileSync(r, "utf-8")))
      .map((r) => r.replace(RAIZ, "src").replace(/\\/g, "/"));
    expect(conFetch).toEqual(["src/infraestructura/http/clienteHttp.ts"]);
  });
});
