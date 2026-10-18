/**
 * @vitest-environment jsdom
 *
 * C133 (ofertas del casero con candado, "¿Lo viste así?", ofertas en la
 * lista) y C134 (entrar a un mercado), con los adaptadores en memoria.
 */
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  PRESENTACIONES_POR_UNIDAD,
  filtrarDirectorio,
  ofertasParaLista,
  textoAhorroOferta,
  textoDiferenciaCiudad,
  textoVence,
  tituloPuesto,
  type EntradaDirectorio,
  type Mercado,
  type Oferta,
  type Producto,
} from "@/dominio/modelo";
import App from "@/ui/App";
import { elegirProducto } from "./ayudas";

beforeEach(() => {
  window.location.hash = "";
});
afterEach(cleanup);

const oferta = (cambios: Partial<Oferta> = {}): Oferta => ({
  id: 1, codigoProducto: "tomate", nombreProducto: "Tomate", unidadBase: "kg", codigoMercado: "rodriguez",
  nombreMercado: "Mercado Rodríguez", numeroPuesto: "14", nombrePuesto: "Verduras", monto: 12, presentacion: "kilo",
  precioPorUnidadBase: 12, desde: "2026-10-18T10:00:00Z", hasta: "2026-10-19T10:00:00Z", nota: "",
  precioSistema: 14.35, procedenciaSistema: "observado", ahorroPorUnidad: 2.35, ahorroRelativo: 0.1638,
  confirmaron: 0, desmintieron: 0, ...cambios,
});

const mercado = (codigo: string, nombre: string, cambios: Partial<Mercado> = {}): Mercado => ({
  codigo, nombre, tipo: "mercado", zona: "Centro", macrodistrito: "Centro", codigoPadre: null, nivelPrecio: "minorista",
  ...cambios,
});

describe("reglas de la oferta y del directorio", () => {
  it("dice cuánto ahorra frente al precio del sistema y de cuál", () => {
    expect(textoAhorroOferta(oferta())).toBe(
      "Bs 2,35 menos por kilo que el precio observado de Mercado Rodríguez (−16 %)",
    );
    expect(tituloPuesto("14", "Verduras")).toBe("Puesto 14 · Verduras");
    expect(tituloPuesto("14")).toBe("Puesto 14");
  });

  it("dice cuánto le queda a la oferta", () => {
    const ahora = new Date("2026-10-18T10:00:00Z");
    expect(textoVence("2026-10-18T15:00:00Z", ahora)).toBe("vence en 5 h");
    expect(textoVence("2026-10-19T10:00:00Z", ahora)).toBe("vence mañana");
    expect(textoVence("2026-10-21T10:00:00Z", ahora)).toBe("vence en 3 días");
    expect(textoVence("2026-10-18T09:00:00Z", ahora)).toBe("venció");
  });

  it("encuentra la oferta que más ahorra para cada producto de la lista, por la cantidad pedida", () => {
    const papa: Producto = {
      codigo: "papa", nombre: "Papa", categoria: "tuberculo", esPerecedero: false, unidadBase: "kg",
      diasConservacion: 60, presentaciones: PRESENTACIONES_POR_UNIDAD.kg,
    };
    const tomate: Producto = { ...papa, codigo: "tomate", nombre: "Tomate" };
    const r = ofertasParaLista(
      [{ codigoProducto: "papa", cantidad: 2, presentacion: "arroba" }, { codigoProducto: "tomate", cantidad: 1, presentacion: "kilo" }],
      [papa, tomate],
      [
        oferta({ id: 1 }),
        oferta({ id: 2, codigoProducto: "papa", ahorroPorUnidad: 0.5 }),
        oferta({ id: 3, codigoProducto: "papa", ahorroPorUnidad: 0.8 }),
        oferta({ id: 4, codigoProducto: "arroz" }),
      ],
    );
    // 2 arrobas = 23 kg × 0,80 = 18,40; el tomate, 1 kg × 2,35.
    expect(r.map((x) => [x.oferta.id, x.ahorro])).toEqual([[3, 18.4], [1, 2.35]]);
  });

  it("filtra el directorio sin tildes, deja fuera los sectores y pone primero lo que tiene ofertas", () => {
    const entradas: EntradaDirectorio[] = [
      { mercado: mercado("lanza", "Mercado Lanza"), puestos: 0, ofertas: 0, sectores: 0 },
      { mercado: mercado("rodriguez", "Mercado Rodríguez", { zona: "San Pedro" }), puestos: 2, ofertas: 1, sectores: 1 },
      { mercado: mercado("rod_cub", "Rodríguez cubierto", { codigoPadre: "rodriguez" }), puestos: 0, ofertas: 0, sectores: 0 },
      { mercado: mercado("ketal", "Ketal", { tipo: "supermercado" }), puestos: 0, ofertas: 0, sectores: 0 },
    ];
    expect(filtrarDirectorio(entradas, "").map((e) => e.mercado.codigo)).toEqual(["rodriguez", "ketal", "lanza"]);
    expect(filtrarDirectorio(entradas, "RODRIGUEZ").map((e) => e.mercado.codigo)).toEqual(["rodriguez"]);
    expect(filtrarDirectorio(entradas, "san pedro").map((e) => e.mercado.codigo)).toEqual(["rodriguez"]);
    expect(filtrarDirectorio(entradas, "", "supermercado").map((e) => e.mercado.codigo)).toEqual(["ketal"]);
  });

  it("lee la diferencia con la ciudad", () => {
    expect(textoDiferenciaCiudad(0.062)).toBe("6 % más caro que la ciudad");
    expect(textoDiferenciaCiudad(-0.03)).toBe("3 % más barato que la ciudad");
    expect(textoDiferenciaCiudad(0.001)).toBe("igual que la ciudad");
    expect(textoDiferenciaCiudad(null)).toBeNull();
  });
});

async function ingresar(correo: string, contrasena: string) {
  fireEvent.click(await screen.findByRole("link", { name: "Ingresar" }));
  fireEvent.change(screen.getByLabelText("Correo"), { target: { value: correo } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: contrasena } });
  fireEvent.submit(screen.getByRole("button", { name: "Ingresar" }).closest("form")!);
  await screen.findByRole("button", { name: "Salir" });
}

function irA(nombre: string) {
  const secciones = screen.getByRole("navigation", { name: "Secciones" });
  fireEvent.click(within(secciones).getByRole("link", { name: nombre }));
}

describe("entrar a un mercado", () => {
  it("del directorio a la ficha: precios por producto, puestos y ofertas", async () => {
    render(<App />);
    irA("Mercados");
    const lugares = await screen.findByRole("list", { name: "Lugares" });
    const rodriguez = within(lugares).getByText("Mercado Rodríguez").closest("a")!;
    expect(rodriguez.textContent).toMatch(/1 oferta/);
    expect(rodriguez.textContent).toMatch(/2 puestos/);
    // El sector no aparece suelto: se entra por su mercado.
    expect(within(lugares).queryByText("Mercado Rodríguez - sector cubierto")).toBeNull();

    window.location.hash = rodriguez.getAttribute("href")!;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    expect(await screen.findByRole("heading", { name: "Mercado Rodríguez" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Mercado Rodríguez - sector cubierto" })).toBeDefined();
    const papas = screen.getByRole("table", { name: "Precios de Tubérculo" });
    expect(within(papas).getByText("Papa holandesa")).toBeDefined();

    fireEvent.click(screen.getByRole("tab", { name: /Puestos/ }));
    const puesto = screen.getByRole("article", { name: "Puesto 14 · Verduras Doña Rosa" });
    expect(within(puesto).getByText(/Pasillo de verduras/)).toBeDefined();
    expect(within(puesto).getByRole("article", { name: "Oferta de Tomate" })).toBeDefined();

    fireEvent.click(screen.getByRole("tab", { name: /Ofertas/ }));
    expect(screen.getByText(/menos por kilo que el precio observado de Mercado Rodríguez/)).toBeDefined();
  });

  it("desde el mapa se entra al mercado", async () => {
    render(<App />);
    const entrar = await screen.findByText("Tocá un punto del mapa para ver su precio y de dónde sale.");
    expect(entrar).toBeDefined();
    expect(screen.getByText(/Anillo dorado: un casero tiene una oferta/)).toBeDefined();
  });
});

describe("ofertas de hoy", () => {
  it("se ordenan por el ahorro real y sin sesión invitan a ingresar para confirmarlas", async () => {
    render(<App />);
    irA("Ofertas de hoy");
    const ofertas = await screen.findAllByRole("article", { name: /^Oferta de / });
    expect(ofertas.map((o) => o.getAttribute("aria-label"))).toEqual(["Oferta de Tomate", "Oferta de Arroz de primera"]);
    expect(within(ofertas[0]).getByText("Declarada por el vendedor")).toBeDefined();
    expect(within(ofertas[0]).getByText("Ingrese para decir si la vio así")).toBeDefined();
  });

  it("dos desmentidos de personas distintas la pausan y el administrador la reactiva", async () => {
    render(<App />);
    await ingresar("vecino@correo.bo", "vecino1234");
    irA("Ofertas de hoy");
    let tomate = await screen.findByRole("article", { name: "Oferta de Tomate" });
    fireEvent.click(within(tomate).getByRole("button", { name: "No estaba así" }));
    expect(await within(tomate).findByText(/Si otra persona tampoco la ve así/)).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: "Salir" }));
    await ingresar("admin@preciojusto.bo", "admin1234");
    irA("Ofertas de hoy");
    tomate = await screen.findByRole("article", { name: "Oferta de Tomate" });
    fireEvent.click(within(tomate).getByRole("button", { name: "No estaba así" }));
    expect(await within(tomate).findByText(/queda pausada hasta que la revisen/)).toBeDefined();

    irA("Administración");
    fireEvent.click(await screen.findByRole("tab", { name: "Ofertas en revisión" }));
    const tabla = await screen.findByRole("table", { name: "Ofertas en revisión" });
    expect(within(tabla).getByText(/2 dijeron que no/)).toBeDefined();
    fireEvent.click(within(tabla).getByRole("button", { name: "Reactivar" }));
    expect(await screen.findByText(/vuelve a mostrarse/)).toBeDefined();
  });

  it("el vecino confirma en un toque", async () => {
    render(<App />);
    await ingresar("vecino@correo.bo", "vecino1234");
    irA("Ofertas de hoy");
    const arroz = await screen.findByRole("article", { name: "Oferta de Arroz de primera" });
    fireEvent.click(within(arroz).getByRole("button", { name: "Sí" }));
    expect(await within(arroz).findByText(/su confirmación ayuda/)).toBeDefined();
    expect(within(arroz).getByText("1 la vio así")).toBeDefined();
  });
});

describe("el casero y sus ofertas", () => {
  it("una oferta más cara que el sistema no se publica; una más barata sí, y vence sola", async () => {
    render(<App />);
    await ingresar("vendedora@preciojusto.bo", "puesto1234");
    fireEvent.click(await screen.findByRole("tab", { name: "Mis ofertas" }));
    const form = await screen.findByRole("form", { name: "Publicar una oferta" });
    await elegirProducto("Papa holandesa", "Producto en oferta", form);
    fireEvent.change(within(form).getByLabelText("Precio de oferta (Bs)"), { target: { value: "9" } });
    fireEvent.submit(form);
    expect(await within(form).findByText(/no es más barato que el precio/)).toBeDefined();

    fireEvent.change(within(form).getByLabelText("Precio de oferta (Bs)"), { target: { value: "6" } });
    fireEvent.click(within(form).getByRole("button", { name: "24 horas" }));
    fireEvent.submit(form);
    const tabla = await screen.findByRole("table", { name: "Mis ofertas" });
    const fila = (await within(tabla).findByText(/Papa holandesa a Bs 6,00/)).closest("tr")!;
    expect(fila.textContent).toMatch(/Activa/);
    expect(fila.textContent).toMatch(/vence mañana|vence en 2\d h/);
  });

  it("registra su puesto con número, nombre y rubros", async () => {
    render(<App />);
    await ingresar("vendedora@preciojusto.bo", "puesto1234");
    fireEvent.click(await screen.findByRole("tab", { name: "Datos del puesto" }));
    const form = await screen.findByRole("form", { name: "Datos del puesto" });
    expect((within(form).getByLabelText("Número del puesto") as HTMLInputElement).value).toBe("14");
    fireEvent.change(within(form).getByLabelText("Nombre (opcional)"), { target: { value: "Verduras Rosa" } });
    fireEvent.click(within(form).getByLabelText("Tubérculo"));
    fireEvent.submit(form);
    expect(await screen.findByText(/Guardado: Puesto 14 · Verduras Rosa/)).toBeDefined();
  });
});

describe("ofertas en la lista de compras", () => {
  it("avisa que el tomate de la lista está en oferta y cuánto se ahorra", async () => {
    render(<App />);
    await ingresar("vecino@correo.bo", "vecino1234");
    fireEvent.click(screen.getByRole("link", { name: "Mis listas y reportes" }));
    fireEvent.click(await screen.findByRole("button", { name: "Nueva lista" }));
    const form = screen.getByRole("form", { name: "Nueva lista" });
    fireEvent.change(within(form).getByLabelText("Nombre de la lista"), { target: { value: "Ensalada" } });
    await elegirProducto("Tomate", "Agregar un producto", form);
    fireEvent.change(within(form).getByLabelText("Cantidad de Tomate"), { target: { value: "2" } });
    fireEvent.change(within(form).getByLabelText("Presentación de Tomate"), { target: { value: "kilo" } });
    fireEvent.submit(form);

    const tarjeta = await screen.findByRole("article", { name: "Lista Ensalada" });
    fireEvent.click(within(tarjeta).getByRole("button", { name: "¿Dónde conviene?" }));
    const ofertas = await within(tarjeta).findByRole("region", { name: "Ofertas para esta lista" });
    // 2 kg × (14,35 − 12) = 4,70.
    expect(ofertas.textContent).toMatch(/Tomate.*Mercado Rodríguez.*Puesto 14.*Bs 4,70/);
  });
});
