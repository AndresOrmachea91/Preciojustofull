/**
 * El adaptador HTTP contra un servidor simulado.
 *
 * Se reemplaza `fetch` por un servidor de mentira que responde con la forma
 * EXACTA de la API real (snake_case, procedencia obligatoria, nivel de
 * precio) y se verifica que el adaptador traduzca al dominio sin perder
 * nada. Es la única prueba del frontend que sabe que existe `fetch`, y es
 * así a propósito: es la prueba del único archivo que lo usa.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClienteHttp, ErrorApi } from "@/infraestructura/http/clienteHttp";
import { PreciosApi } from "@/infraestructura/http/PreciosApi";

const MERCADOS = [
  {
    codigo: "rodriguez", nombre: "Mercado Rodríguez", tipo: "mercado", zona: "Cotahuma",
    macrodistrito: "Cotahuma", codigo_padre: null, nivel_precio: "minorista",
    latitud: -16.500192, longitud: -68.138992, publica_rango: true,
  },
  {
    codigo: "rodriguez_cubierto", nombre: "Mercado Rodríguez - sector cubierto", tipo: "mercado",
    zona: "Cotahuma", macrodistrito: "Cotahuma", codigo_padre: "rodriguez", nivel_precio: "minorista",
    latitud: -16.500676, longitud: -68.139072, publica_rango: true,
  },
  {
    codigo: "makro_centro", nombre: "Makro", tipo: "mayorista", zona: "Centro",
    macrodistrito: "Centro", codigo_padre: null, nivel_precio: "mayorista",
    latitud: -16.493233, longitud: -68.14427, publica_rango: false,
  },
];

const PRECIO = {
  codigo_producto: "arroz_primera", codigo_mercado: "rodriguez", periodo: "2026-07",
  rango: { minimo: 13.64, maximo: 16.01, centro: 14.83 }, unidad: "kg", confianza: "medio",
  procedencia: "estimado", observaciones_usadas: 104, fecha_observacion_mas_reciente: null,
  conflictos: ["Estimado desde la referencia de ciudad la_paz con factor 1.00; no es una medición en rodriguez"],
};

const COMPARAR = [
  { codigo_mercado: "rodriguez", nombre_mercado: "Mercado Rodríguez", tipo: "mercado", zona: "Cotahuma", nivel_precio: "minorista", precio: PRECIO },
  { codigo_mercado: "makro_centro", nombre_mercado: "Makro", tipo: "mayorista", zona: "Centro", nivel_precio: "mayorista",
    precio: { ...PRECIO, codigo_mercado: "makro_centro", rango: { minimo: 11.3, maximo: 13.26, centro: 12.28 } } },
];

/** Servidor simulado: enruta por URL y registra lo que le pidieron. */
function servidorSimulado() {
  const pedidos: string[] = [];
  const fetchFalso = vi.fn(async (entrada: RequestInfo | URL) => {
    const url = String(entrada);
    pedidos.push(url);
    const responder = (cuerpo: unknown, status = 200) =>
      new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } });
    if (url.endsWith("/mercados")) return responder(MERCADOS);
    if (url.includes("/precios/arroz_primera/comparar")) return responder(COMPARAR);
    if (url.includes("/precios/no_existe/comparar")) return responder({ detail: "No existe el producto no_existe" }, 404);
    return responder({ detail: "ruta no simulada" }, 404);
  });
  vi.stubGlobal("fetch", fetchFalso);
  return { pedidos };
}

afterEach(() => vi.unstubAllGlobals());

describe("PreciosApi contra un servidor simulado", () => {
  const api = () => new PreciosApi(new ClienteHttp("http://api.local/api/v1"));

  it("trae los puntos de venta con coordenadas, macrodistrito, padre y nivel", async () => {
    const { pedidos } = servidorSimulado();
    const mercados = await api().mercados();

    expect(pedidos).toEqual(["http://api.local/api/v1/mercados"]);
    expect(mercados).toHaveLength(3);
    expect(mercados[0]).toEqual({
      codigo: "rodriguez", nombre: "Mercado Rodríguez", tipo: "mercado", zona: "Cotahuma",
      macrodistrito: "Cotahuma", codigoPadre: null, nivelPrecio: "minorista",
      latitud: -16.500192, longitud: -68.138992,
    });
    expect(mercados[1].codigoPadre).toBe("rodriguez");
    expect(mercados[2].nivelPrecio).toBe("mayorista");
  });

  it("trae la comparación con procedencia y nivel de precio, sin perder ninguno", async () => {
    servidorSimulado();
    const filas = await api().compararMercados("arroz_primera");

    expect(filas).toHaveLength(2);
    expect(filas[0].precio.procedencia).toBe("estimado");
    expect(filas[0].precio.observacionesUsadas).toBe(104);
    expect(filas[0].precio.fechaObservacionMasReciente).toBeNull();
    expect(filas[0].mercado.nivelPrecio).toBe("minorista");
    expect(filas[1].mercado.nivelPrecio).toBe("mayorista");
    expect(filas[0].precio.conflictos[0]).toContain("no es una medición en rodriguez");
  });

  it("un error de la API llega como ErrorApi con su estado, no como JSON roto", async () => {
    servidorSimulado();
    await expect(api().compararMercados("no_existe")).rejects.toBeInstanceOf(ErrorApi);
    await expect(api().compararMercados("no_existe")).rejects.toMatchObject({ estado: 404 });
  });
});
