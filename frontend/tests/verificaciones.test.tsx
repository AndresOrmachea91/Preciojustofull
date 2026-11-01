/**
 * @vitest-environment jsdom
 *
 * Limpieza del 20 de octubre: lugares con el mismo precio en una sola
 * tarjeta, "¿Lo vio aquí? Diga a cuánto" en el panel del mapa, y qué falta
 * medir primero (A4230) con su planilla de la próxima ronda.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { planillaDeLaRonda } from "@/aplicacion/casosUso/administracion/operarSistema";
import { VerMapa } from "@/aplicacion/casosUso/publico/verMapa";
import {
  PRESENTACIONES_POR_UNIDAD,
  agruparPorPrecio,
  type Mercado,
  type PlanDeVerificacion,
  type Precio,
  type PrecioEnMercado,
  type Producto,
} from "@/dominio/modelo";
import { crearContenedor } from "@/infraestructura/contenedor";
import { PreciosMemoria } from "@/infraestructura/memoria/PreciosMemoria";
import { PanelPunto } from "@/ui/componentes/PanelPunto";
import { QueFaltaMedir, VariacionPorProducto } from "@/ui/componentes/PlanVerificacion";

afterEach(cleanup);

const TOMATE: Producto = {
  codigo: "tomate", nombre: "Tomate", categoria: "hortaliza", esPerecedero: true, unidadBase: "kg",
  diasConservacion: 5, presentaciones: PRESENTACIONES_POR_UNIDAD.kg,
};

const lugar = (codigo: string, tipo: Mercado["tipo"] = "mercado"): Mercado => ({
  codigo, nombre: `Mercado ${codigo}`, tipo, zona: "Centro", macrodistrito: "Centro", codigoPadre: null,
  nivelPrecio: "minorista",
});

function conPrecio(mercado: Mercado, base: Precio, cambios: Partial<Precio> = {}): PrecioEnMercado {
  return { mercado, precio: { ...base, ...cambios } };
}

describe("lugares con el mismo precio", () => {
  it("los estimados iguales van juntos y lo observado siempre aparte", async () => {
    const { marcadores } = await new VerMapa(new PreciosMemoria(), new PreciosMemoria()).ejecutar("tomate");
    const base = marcadores.find((m) => m.precio)!.precio!;
    const estimado = { ...base, procedencia: "estimado" as const };
    const items = [
      conPrecio(lugar("a"), estimado),
      conPrecio(lugar("b"), estimado),
      conPrecio(lugar("c"), { ...base, procedencia: "observado" }),
      conPrecio(lugar("d"), { ...base, procedencia: "observado" }),
      conPrecio(lugar("e"), estimado, { rango: { ...estimado.rango, maximo: estimado.rango.maximo + 1 } }),
    ];
    const grupos = agruparPorPrecio(items);
    expect(grupos.map((g) => g.items.map((x) => x.mercado.codigo))).toEqual([["a", "b"], ["c"], ["d"], ["e"]]);
  });
});

describe("¿Lo vio aquí? Diga a cuánto", () => {
  async function ketal() {
    const memoria = new PreciosMemoria();
    const { marcadores } = await new VerMapa(memoria, memoria).ejecutar("tomate");
    return marcadores.find((m) => m.mercado.codigo === "mercado_san_pedro")!;
  }

  it("sin sesión invita a ingresar", async () => {
    render(<PanelPunto marcador={await ketal()} producto={TOMATE} contenedor={crearContenedor("memoria")} />);
    expect(screen.getByText(/así deja de ser un estimado/)).toBeDefined();
    expect(screen.getByRole("link", { name: "Ingrese" })).toBeDefined();
  });

  it("con sesión el precio viene escrito y se envía como un reporte pendiente", async () => {
    const contenedor = crearContenedor("memoria");
    const usuario = await contenedor.sesion.ingresar("vecino@correo.bo", "vecino1234");
    const antes = (await contenedor.reportarPrecio.misReportes()).length;
    const marcador = await ketal();
    render(<PanelPunto marcador={marcador} producto={TOMATE} contenedor={contenedor} usuario={usuario} />);

    const caja = screen.getByLabelText("¿Lo vio aquí? Diga a cuánto") as HTMLInputElement;
    expect(caja.value).toBe(marcador.precio!.rango.centro.toFixed(2));
    fireEvent.change(caja, { target: { value: "9,50" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await screen.findByText(/queda pendiente hasta que un administrador lo revise/);
    const despues = await contenedor.reportarPrecio.misReportes();
    expect(despues.length).toBe(antes + 1);
  });
});

const PLAN: PlanDeVerificacion = {
  fecha: "2026-10-20",
  productos: [
    { producto: TOMATE, puntaje: 0.3, lugaresSinDato: 2, lugaresConDatoViejo: 0, lugaresAlDia: 0, cambioMensual: 0.15,
      anchoRelativo: 0.16, motivos: ["nadie lo midió todavía en ningún lugar", "cambia en promedio 15 % de un mes a otro"] },
    { producto: { ...TOMATE, codigo: "arroz", nombre: "Arroz" }, puntaje: 0, lugaresSinDato: 0, lugaresConDatoViejo: 0,
      lugaresAlDia: 2, cambioMensual: 0.01, anchoRelativo: 0.1, motivos: [] },
  ],
  lugares: [
    { mercado: lugar("rodriguez"), productosAlDia: 0, productosTotal: 2 },
    { mercado: lugar("lanza"), productosAlDia: 1, productosTotal: 2 },
  ],
  variaciones: [
    { producto: TOMATE, cambioMensual: 0.15, mayorSubida: 0.3, mayorBajada: -0.2, meses: 13, nivel: "minorista" },
  ],
};

describe("qué falta medir primero (A4230)", () => {
  it("lista lo pendiente con sus motivos y no lo que ya está al día", () => {
    render(<QueFaltaMedir plan={PLAN} />);
    expect(screen.getByText("Tomate")).toBeDefined();
    expect(screen.getByText(/nadie lo midió todavía en ningún lugar · cambia en promedio 15 %/)).toBeDefined();
    expect(screen.queryByText("Arroz")).toBeNull();
  });

  it("muestra cuánto se mueve cada precio al mes (A5020)", () => {
    render(<VariacionPorProducto plan={PLAN} />);
    expect(screen.getByText("15,0 %")).toBeDefined();
  });

  it("la planilla de la ronda trae una fila por producto pendiente y lugar, con el monto en blanco", () => {
    const csv = planillaDeLaRonda(PLAN, { fecha: "2026-10-21" }).trim().split("\n");
    expect(csv[0]).toBe("fecha;mercado;producto;monto;presentacion;cantidad;variedad;observador;tipo;puesto");
    expect(csv.slice(1)).toEqual([
      "2026-10-21;rodriguez;tomate;;kilo;;;;cotizado;",
      "2026-10-21;lanza;tomate;;kilo;;;;cotizado;",
    ]);
  });

  it("la página ¿Qué tan confiable es? dice qué parte del mapa está medida", async () => {
    window.location.hash = "#/confiabilidad";
    const { default: App } = await import("@/ui/App");
    render(<App />);
    await waitFor(() => expect(screen.getByText(/de los precios del mapa salen de una medición/)).toBeDefined());
    expect(await screen.findByRole("heading", { name: "Lo que falta medir primero" })).toBeDefined();
    window.location.hash = "";
  });
});
