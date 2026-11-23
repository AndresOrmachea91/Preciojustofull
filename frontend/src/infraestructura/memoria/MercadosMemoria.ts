/**
 * Mercados por dentro, puestos y ofertas en memoria (C133, C134): el plan B
 * de la demo y el adaptador de las pruebas. Aplica los mismos candados que
 * el backend —vence sola, máximo tres, más barata que el precio del sistema,
 * dos desmentidos la pausan— para que la interfaz se comporte igual sin red.
 */
import type {
  AlmacenSesion,
  CatalogoRepositorio,
  DatosDistribuidora,
  DatosPuesto,
  HistorialRepositorio,
  NuevoArticulo,
  MercadosRepositorio,
  NuevaOferta,
  NuevoCombo,
  OfertasRepositorio,
  OfertasVendedorRepositorio,
  PrecioRepositorio,
  RevisionOfertasRepositorio,
} from "@/aplicacion/puertos";
import {
  MAXIMO_OFERTAS_ACTIVAS, disponibilidadPara, ofertasQueCuentan,
  type ReporteInventario,
  type ArticuloInventario,
  type PuestosDeMercado,
  type EntradaDirectorio,
  type FichaMercado,
  type MiOferta,
  type Oferta,
  type OfertaEnRevision,
  type PlanDeVerificacion,
  type PrioridadDeProducto,
  type VariacionDeProducto,
  type PrecioDeProducto,
  type PrecioDelPuesto,
  type Puesto,
  type ResultadoConfirmacion,
} from "@/dominio/modelo";
import { idDeSesion } from "@/infraestructura/memoria/CuentasMemoria";

interface OfertaGuardada {
  id: number;
  idVendedor: number;
  codigoMercado: string;
  numeroPuesto: string | null;
  codigoProducto: string;
  monto: number;
  presentacion: string;
  factor: number;
  desde: number;
  hasta: number;
  nota: string;
  estado: "activa" | "en_revision" | "retirada";
  combo?: string | null;
}

const HORA = 3_600_000;
// En la demo la única vendedora (Rosa) es del Rodríguez: es su mercado. En
// la API el mercado sale de la cuenta, que asigna el administrador.
const MERCADO_DE_LA_DEMO = "rodriguez";

// La vendedora de la demo (Rosa, id 2) tiene el 14 del Rodríguez; el 22 lo
// registró el administrador y todavía no tiene dueño.
const PUESTOS: (Puesto & { idVendedor: number | null })[] = [
  { id: 1, codigoMercado: "rodriguez", numero: "14", nombre: "Verduras Doña Rosa", rubros: ["hortaliza", "fruta"], referencia: "Pasillo de verduras, frente a la puerta 2", registrado: true, foto: null, esLocal: false, idVendedor: 2, celular: null },
  { id: 2, codigoMercado: "rodriguez", numero: "22", nombre: "Papas del Norte", rubros: ["tuberculo"], referencia: "", registrado: true, foto: null, esLocal: false, idVendedor: null, celular: null },
  { id: 3, codigoMercado: "lanza", numero: "3", nombre: "Abarrotes Mary", rubros: ["abarrote"], referencia: "Planta baja, entrada por la Figueroa", registrado: true, foto: null, esLocal: false, idVendedor: 98, celular: null },
];

// Lo que tiene cada puesto de la demo (por id de puesto): no todos venden lo mismo.
type ArticuloGuardado = {
  codigoProducto: string; monto: number; presentacion: string; factor: number;
  disponibilidad: ArticuloInventario["disponibilidad"]; cantidad?: number | null; minimo?: number | null;
};
const INVENTARIO: Record<number, ArticuloGuardado[]> = {
  1: [
    { codigoProducto: "tomate", monto: 13, presentacion: "kilo", factor: 1, disponibilidad: "hay", cantidad: 24, minimo: 5 },
    { codigoProducto: "papa", monto: 85, presentacion: "arroba", factor: 11.5, disponibilidad: "poco", cantidad: 2, minimo: 3 },
  ],
  2: [{ codigoProducto: "papa", monto: 80, presentacion: "arroba", factor: 11.5, disponibilidad: "hay", cantidad: 14, minimo: 3 }],
  3: [
    { codigoProducto: "arroz", monto: 8.2, presentacion: "kilo", factor: 1, disponibilidad: "hay", cantidad: 40, minimo: 8 },
    { codigoProducto: "papa", monto: 84, presentacion: "arroba", factor: 11.5, disponibilidad: "agotado", cantidad: 0, minimo: 3 },
  ],
};

// Lo último que se supo en algunos puestos (campo y lo que declaró el casero).
const PRECIOS_DE_PUESTO: (PrecioDelPuesto & { codigoMercado: string; numero: string })[] = [
  { codigoMercado: "rodriguez", numero: "14", codigoProducto: "tomate", nombreProducto: "Tomate", monto: 6.5, unidad: "libra", precioPorUnidadBase: 14.13, unidadBase: "kg", fecha: "2026-09-14", fuente: "campo" },
  { codigoMercado: "rodriguez", numero: "22", codigoProducto: "papa", nombreProducto: "Papa holandesa", monto: 80, unidad: "arroba", precioPorUnidadBase: 6.96, unidadBase: "kg", fecha: "2026-09-14", fuente: "vendedor" },
];

export class MercadosMemoria
  implements MercadosRepositorio, OfertasRepositorio, OfertasVendedorRepositorio, RevisionOfertasRepositorio
{
  private readonly registro = PUESTOS.map((p) => ({ ...p }));
  private readonly ofertas: OfertaGuardada[];
  private readonly confirmaciones = new Map<string, boolean>();
  private readonly inventarios = new Map<number, ArticuloGuardado[]>(
    Object.entries(INVENTARIO).map(([id, lista]) => [Number(id), lista.map((a) => ({ ...a }))]),
  );
  private siguiente = 3;

  constructor(
    private readonly almacen: AlmacenSesion,
    private readonly catalogo: CatalogoRepositorio,
    private readonly precios: PrecioRepositorio & HistorialRepositorio,
    private readonly ahora: () => number = () => Date.now(),
  ) {
    const t = this.ahora();
    this.ofertas = [
      { id: 1, idVendedor: 2, codigoMercado: "rodriguez", numeroPuesto: "14", codigoProducto: "tomate", monto: 12, presentacion: "kilo", factor: 1, desde: t - 3 * HORA, hasta: t + 21 * HORA, nota: "Hasta agotar", estado: "activa" },
      { id: 2, idVendedor: 98, codigoMercado: "lanza", numeroPuesto: "3", codigoProducto: "arroz", monto: 7.9, presentacion: "kilo", factor: 1, desde: t - HORA, hasta: t + 45 * HORA, nota: "", estado: "activa" },
    ];
  }

  // --- público ---------------------------------------------------------------

  async directorio(): Promise<EntradaDirectorio[]> {
    const mercados = await this.catalogo.mercados();
    const vigentes = await this.vigentes();
    return mercados.map((m) => ({
      mercado: m,
      puestos: this.registro.filter((p) => p.codigoMercado === m.codigo).length,
      ofertas: vigentes.filter((o) => o.codigoMercado === m.codigo).length,
      sectores: mercados.filter((x) => x.codigoPadre === m.codigo).length,
    }));
  }

  /** Los puestos del mercado con su inventario: primero los que tienen el producto buscado. */
  async puestos(codigoMercado: string, filtro?: { producto?: string; articulos?: number }): Promise<PuestosDeMercado> {
    const mercados = await this.catalogo.mercados();
    const mercado = mercados.find((m) => m.codigo === codigoMercado);
    if (!mercado) throw new Error(`No existe el mercado ${codigoMercado}`);
    const codigos = [codigoMercado, ...mercados.filter((m) => m.codigoPadre === codigoMercado).map((m) => m.codigo)];
    const buscado = filtro?.producto;
    const puestos = await Promise.all(
      this.registro
        .filter((p) => codigos.includes(p.codigoMercado))
        .map(async ({ idVendedor, ...puesto }) => {
          const todos = (await this.articulos(puesto.id ?? 0)).sort(
            (a, b) =>
              Number(a.codigoProducto !== buscado) - Number(b.codigoProducto !== buscado) ||
              Number(a.disponibilidad === "agotado") - Number(b.disponibilidad === "agotado") ||
              a.nombreProducto.localeCompare(b.nombreProducto),
          );
          const tiene = todos.some((a) => a.codigoProducto === buscado && a.disponibilidad !== "agotado");
          const articulos = filtro?.articulos ? todos.slice(0, filtro.articulos) : todos;
          return { puesto, articulos, total: todos.length, tiene, atendido: idVendedor !== null };
        }),
    );
    puestos.sort((a, b) => Number(b.tiene) - Number(a.tiene) || Number(b.atendido) - Number(a.atendido));
    return { mercado, puestos: puestos.map(({ puesto, articulos, total }) => ({ puesto, articulos, total })) };
  }

  /**
   * La misma regla que el backend, más corta: incertidumbre (cuánto se mueve
   * el precio de la ciudad + ancho del rango) por la parte de lugares sin
   * un dato medido.
   */
  async verificaciones(): Promise<PlanDeVerificacion> {
    const mercados = (await this.catalogo.mercados()).filter((m) => m.nivelPrecio === "minorista");
    const productos = await this.catalogo.productos();
    const prioridades: PrioridadDeProducto[] = [];
    const variaciones: VariacionDeProducto[] = [];
    const alDia = new Map<string, number>();
    for (const producto of productos) {
      const serie = (await this.precios.historial(producto.codigo)).puntos.filter((x) => x.nivel === "minorista");
      const cambios = serie.slice(1).map((x, i) => x.precio / serie[i].precio - 1);
      const cambio = cambios.length >= 2 ? cambios.reduce((s, c) => s + Math.abs(c), 0) / cambios.length : null;
      if (cambio !== null) {
        variaciones.push({
          producto,
          cambioMensual: Math.round(cambio * 10_000) / 10_000,
          mayorSubida: Math.max(0, ...cambios),
          mayorBajada: Math.min(0, ...cambios),
          meses: serie.length,
          nivel: "minorista",
        });
      }
      const precios = (await this.precios.compararMercados(producto.codigo)).filter((x) => x.mercado.nivelPrecio === "minorista");
      const medidos = precios.filter((x) => x.precio.procedencia === "observado");
      for (const x of medidos) alDia.set(x.mercado.codigo, (alDia.get(x.mercado.codigo) ?? 0) + 1);
      const referencia = precios[0]?.precio.rango;
      const ancho = referencia && referencia.centro ? (referencia.maximo - referencia.minimo) / referencia.centro : null;
      const sinDato = mercados.length - medidos.length;
      const faltante = mercados.length ? sinDato / mercados.length : 0;
      prioridades.push({
        producto,
        puntaje: Math.round(((cambio ?? 0) + (ancho ?? 0)) * faltante * 10_000) / 10_000,
        lugaresSinDato: sinDato,
        lugaresConDatoViejo: 0,
        lugaresAlDia: medidos.length,
        cambioMensual: cambio,
        anchoRelativo: ancho,
        motivos: medidos.length === 0 ? ["nadie lo midió todavía en ningún lugar"] : [`sin medir en ${sinDato} de ${mercados.length} lugares`],
      });
    }
    return {
      fecha: new Date(this.ahora()).toISOString().slice(0, 10),
      productos: prioridades.sort((a, b) => b.puntaje - a.puntaje || a.producto.nombre.localeCompare(b.producto.nombre)),
      lugares: mercados
        .map((m) => ({ mercado: m, productosAlDia: alDia.get(m.codigo) ?? 0, productosTotal: productos.length }))
        .sort((a, b) => a.productosAlDia - b.productosAlDia || a.mercado.nombre.localeCompare(b.mercado.nombre)),
      variaciones: variaciones.sort((a, b) => b.cambioMensual - a.cambioMensual),
    };
  }

  async ficha(codigoMercado: string): Promise<FichaMercado> {
    const mercados = await this.catalogo.mercados();
    const mercado = mercados.find((m) => m.codigo === codigoMercado);
    if (!mercado) throw new Error(`No existe el mercado ${codigoMercado}`);
    const productos = await this.catalogo.productos();
    const precios: PrecioDeProducto[] = [];
    for (const producto of productos) {
      const todos = await this.precios.compararMercados(producto.codigo);
      const aqui = todos.find((x) => x.mercado.codigo === codigoMercado);
      if (!aqui) continue;
      // La "ciudad" de la demo: el promedio de los lugares del mismo nivel.
      const pares = todos.filter((x) => x.mercado.nivelPrecio === mercado.nivelPrecio);
      const ciudad = pares.reduce((s, x) => s + x.precio.rango.centro, 0) / pares.length;
      precios.push({
        codigoProducto: producto.codigo,
        nombreProducto: producto.nombre,
        categoria: producto.categoria,
        precio: aqui.precio,
        ciudad: Math.round(ciudad * 100) / 100,
        diferencia:
          aqui.precio.procedencia === "observado" ? Math.round((aqui.precio.rango.centro / ciudad - 1) * 10_000) / 10_000 : null,
      });
    }
    const ofertas = await this.vigentes({ mercado: codigoMercado });
    return {
      mercado,
      padre: mercados.find((m) => m.codigo === mercado.codigoPadre) ?? null,
      sectores: mercados.filter((m) => m.codigoPadre === codigoMercado),
      factorMercado: 1,
      precios,
      puestos: this.registro
        .filter((p) => p.codigoMercado === codigoMercado)
        .map(({ idVendedor: _, ...puesto }) => ({
          puesto,
          precios: PRECIOS_DE_PUESTO.filter((x) => x.codigoMercado === codigoMercado && x.numero === puesto.numero),
          ofertas: ofertas.filter((o) => o.numeroPuesto === puesto.numero),
        })),
      ofertas,
      observados: precios.filter((p) => p.precio.procedencia === "observado").length,
      estimados: precios.filter((p) => p.precio.procedencia === "estimado").length,
      productosSinPrecio: productos.length - precios.length,
      datoMasReciente:
        precios
          .map((p) => (p.precio.procedencia === "observado" ? p.precio.fechaObservacionMasReciente : null))
          .filter((f): f is string => f !== null)
          .sort()
          .pop() ?? null,
    };
  }

  async vigentes(filtro?: { mercado?: string; producto?: string }): Promise<Oferta[]> {
    const ahora = this.ahora();
    const vistas: Oferta[] = [];
    for (const o of this.ofertas) {
      if (o.estado !== "activa" || o.desde > ahora || o.hasta <= ahora) continue;
      if (filtro?.mercado && o.codigoMercado !== filtro.mercado) continue;
      if (filtro?.producto && o.codigoProducto !== filtro.producto) continue;
      const vista = await this.vista(o);
      if (vista) vistas.push(vista);
    }
    return vistas.sort((a, b) => b.ahorroRelativo - a.ahorroRelativo);
  }

  async confirmar(idOferta: number, laVioAsi: boolean): Promise<ResultadoConfirmacion> {
    const yo = this.sesion();
    const oferta = this.ofertas.find((o) => o.id === idOferta && o.estado === "activa" && o.hasta > this.ahora());
    if (!oferta) throw new Error(`No existe la oferta ${idOferta}`);
    if (oferta.idVendedor === yo) throw new Error("No puede confirmar su propia oferta");
    this.confirmaciones.set(`${idOferta}:${yo}`, laVioAsi);
    const { confirmaron, desmintieron } = this.cuenta(idOferta);
    const pausada = desmintieron >= 2;
    if (pausada) oferta.estado = "en_revision";
    return { confirmaron, desmintieron, pausada };
  }

  // --- vendedor ----------------------------------------------------------------

  async miPuesto(): Promise<Puesto | null> {
    const yo = this.sesion();
    const suyo = this.registro.find((p) => p.idVendedor === yo);
    if (!suyo) return null;
    const { idVendedor: _, ...puesto } = suyo;
    return puesto;
  }

  async guardarMiPuesto(datos: DatosPuesto): Promise<Puesto> {
    const yo = this.sesion();
    const numero = datos.numero.trim().toUpperCase();
    const mercado = datos.codigoMercado ?? this.registro.find((p) => p.idVendedor === yo)?.codigoMercado ?? MERCADO_DE_LA_DEMO;
    const ocupado = this.registro.find((p) => p.codigoMercado === mercado && p.numero === numero);
    if (ocupado && ocupado.idVendedor !== null && ocupado.idVendedor !== yo) {
      throw new Error(`Ya existe un puesto en este mercado con el código ${numero}`);
    }
    const suyo = this.registro.find((p) => p.idVendedor === yo) ?? ocupado;
    const nuevo = { id: suyo?.id ?? this.registro.length + 1, codigoMercado: mercado, numero, nombre: datos.nombre, rubros: datos.rubros, referencia: datos.referencia, registrado: true, foto: suyo?.foto ?? null, esLocal: false, idVendedor: yo, celular: suyo?.celular ?? null };
    if (suyo) Object.assign(suyo, nuevo);
    else this.registro.push(nuevo);
    const { idVendedor: _, ...puesto } = nuevo;
    return puesto;
  }

  async registrarDistribuidora(datos: DatosDistribuidora): Promise<Puesto> {
    const yo = this.sesion();
    if (!datos.nombre.trim()) throw new Error("La distribuidora necesita un nombre");
    const codigo = `dist_${datos.nombre.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
    const suyo = this.registro.find((p) => p.idVendedor === yo);
    const nuevo = { id: suyo?.id ?? this.registro.length + 1, codigoMercado: codigo, numero: "LOCAL", nombre: datos.nombre.trim(), rubros: datos.rubros, referencia: datos.referencia, registrado: true, foto: suyo?.foto ?? null, esLocal: true, idVendedor: yo, celular: datos.celular?.replace(/\D/g, "").replace(/^591/, "") || null };
    if (suyo) Object.assign(suyo, nuevo);
    else this.registro.push(nuevo);
    const { idVendedor: _, ...puesto } = nuevo;
    return puesto;
  }

  async ponerFoto(imagen: string): Promise<Puesto> {
    const suyo = this.registro.find((p) => p.idVendedor === this.sesion());
    if (!suyo) throw new Error("Primero registre su puesto; después la foto");
    // En la demo la foto se guarda tal cual (data URL): no hay servidor de archivos.
    suyo.foto = imagen;
    const { idVendedor: _, ...puesto } = suyo;
    return puesto;
  }

  async inventario(): Promise<ArticuloInventario[]> {
    const suyo = this.registro.find((p) => p.idVendedor === this.sesion());
    if (!suyo) throw new Error("Primero registre su puesto: el inventario es de su puesto");
    return this.articulos(suyo.id ?? 0);
  }

  async guardarArticulo(a: NuevoArticulo): Promise<ArticuloInventario> {
    const suyo = this.registro.find((p) => p.idVendedor === this.sesion());
    if (!suyo) throw new Error("Primero registre su puesto: el inventario es de su puesto");
    if (!(a.monto > 0)) throw new Error("El precio tiene que ser mayor a cero");
    const producto = (await this.catalogo.productos()).find((p) => p.codigo === a.codigoProducto);
    const presentacion = producto?.presentaciones.find((p) => p.codigo === a.presentacion);
    if (!producto || !presentacion) throw new Error("Elija el producto y su presentación");
    const id = suyo.id ?? 0;
    const lista = this.inventarios.get(id) ?? [];
    const cantidad = a.cantidad ?? null;
    const minimo = a.minimo ?? null;
    const disponibilidad = cantidad === null ? a.disponibilidad : disponibilidadPara(cantidad, minimo);
    const nuevo = { codigoProducto: a.codigoProducto, monto: a.monto, presentacion: a.presentacion, factor: presentacion.factor, disponibilidad, cantidad, minimo };
    const i = lista.findIndex((x) => x.codigoProducto === a.codigoProducto);
    if (i >= 0) lista[i] = nuevo;
    else lista.push(nuevo);
    this.inventarios.set(id, lista);
    return (await this.articulos(id)).find((x) => x.codigoProducto === a.codigoProducto)!;
  }

  async ajustarCantidad(codigoProducto: string, cambio: number): Promise<ArticuloInventario> {
    const suyo = this.registro.find((p) => p.idVendedor === this.sesion());
    if (!suyo) throw new Error("Primero registre su puesto: el inventario es de su puesto");
    const id = suyo.id ?? 0;
    const articulo = (this.inventarios.get(id) ?? []).find((x) => x.codigoProducto === codigoProducto);
    if (!articulo) throw new Error("Ese producto no está en su puesto");
    articulo.cantidad = Math.max(0, Math.round(((articulo.cantidad ?? 0) + cambio) * 100) / 100);
    articulo.disponibilidad = disponibilidadPara(articulo.cantidad, articulo.minimo ?? null);
    return (await this.articulos(id)).find((x) => x.codigoProducto === codigoProducto)!;
  }

  /** En la demo sin servidor no hay precio del mercado con que comparar: solo las alertas. */
  async reporteInventario(): Promise<ReporteInventario> {
    const articulos = await this.inventario();
    const renglones = articulos.map((a) => ({
      articulo: a,
      sugerencia: { tipo: "sin_referencia" as const, texto: "Todavía no hay un precio del mercado para comparar.", precioSugerido: null, precioMercado: null, diferencia: null },
      alertas: a.disponibilidad === "agotado" ? ["Se acabó: los compradores lo ven como agotado."]
        : a.disponibilidad === "poco" ? ["Queda poco: conviene reponer."] : [],
    }));
    const conCantidad = articulos.filter((a) => a.cantidad !== null);
    return {
      renglones,
      productos: articulos.length,
      conCantidad: conCantidad.length,
      valorTotal: Math.round(conCantidad.reduce((t, a) => t + (a.cantidad ?? 0) * a.monto, 0) * 100) / 100,
      agotados: articulos.filter((a) => a.disponibilidad === "agotado").length,
      quedaPoco: articulos.filter((a) => a.disponibilidad === "poco").length,
      paraRevisarPrecio: 0,
      sinActualizar: 0,
      consejos: ["Anote cuánto le queda de cada producto: el sistema le avisará antes de que se acabe."],
    };
  }

  async quitarArticulo(codigoProducto: string): Promise<void> {
    const suyo = this.registro.find((p) => p.idVendedor === this.sesion());
    if (!suyo) return;
    const id = suyo.id ?? 0;
    this.inventarios.set(id, (this.inventarios.get(id) ?? []).filter((x) => x.codigoProducto !== codigoProducto));
  }

  private async articulos(idPuesto: number): Promise<ArticuloInventario[]> {
    const productos = await this.catalogo.productos();
    return (this.inventarios.get(idPuesto) ?? []).flatMap((a) => {
      const producto = productos.find((p) => p.codigo === a.codigoProducto);
      if (!producto) return [];
      return [
        {
          codigoProducto: a.codigoProducto,
          nombreProducto: producto.nombre,
          categoria: producto.categoria,
          monto: a.monto,
          presentacion: a.presentacion,
          precioPorUnidadBase: Math.round((a.monto / a.factor) * 100) / 100,
          unidadBase: producto.unidadBase,
          disponibilidad: a.disponibilidad,
          actualizadoEn: null,
          cantidad: a.cantidad ?? null,
          minimo: a.minimo ?? null,
        },
      ];
    });
  }

  async misOfertas(): Promise<MiOferta[]> {
    const yo = this.sesion();
    const productos = await this.catalogo.productos();
    const ahora = this.ahora();
    return this.ofertas
      .filter((o) => o.idVendedor === yo)
      .sort((a, b) => b.desde - a.desde)
      .map((o) => {
        const { confirmaron, desmintieron } = this.cuenta(o.id);
        return {
          id: o.id,
          codigoProducto: o.codigoProducto,
          nombreProducto: productos.find((p) => p.codigo === o.codigoProducto)?.nombre ?? o.codigoProducto,
          monto: o.monto,
          presentacion: o.presentacion,
          precioPorUnidadBase: o.monto / o.factor,
          desde: new Date(o.desde).toISOString(),
          hasta: new Date(o.hasta).toISOString(),
          nota: o.nota,
          combo: o.combo ?? null,
          estado: o.estado === "activa" && o.hasta <= ahora ? "vencida" : o.estado,
          confirmaron,
          desmintieron,
        };
      });
  }

  async publicarOferta(nueva: NuevaOferta): Promise<void> {
    this.exigirLugarLibre();
    this.ofertas.push(await this.prepararOferta(nueva, null));
  }

  async publicarCombo(combo: NuevoCombo): Promise<void> {
    this.exigirLugarLibre();
    // Todo se valida antes de guardar: o se publica entero o nada.
    const preparadas: OfertaGuardada[] = [];
    for (const r of combo.renglones) {
      preparadas.push(await this.prepararOferta({ ...r, horas: combo.horas, nota: combo.nota }, combo.nombre));
    }
    for (const o of preparadas) this.ofertas.push({ ...o, id: this.siguiente++ });
  }

  private exigirLugarLibre(): void {
    const yo = this.sesion();
    const ahora = this.ahora();
    const activas = this.ofertas.filter((o) => o.idVendedor === yo && o.estado === "activa" && o.hasta > ahora);
    if (ofertasQueCuentan(activas.map((o) => ({ id: o.id, combo: o.combo ?? null }))) >= MAXIMO_OFERTAS_ACTIVAS) {
      throw new Error(
        "Ya tiene 3 ofertas activas (un combo cuenta como una): retire una o espere a que venza. Si todo está en oferta, nada lo está.",
      );
    }
  }

  private async prepararOferta(nueva: NuevaOferta, combo: string | null): Promise<OfertaGuardada> {
    const yo = this.sesion();
    const ahora = this.ahora();
    const producto = (await this.catalogo.productos()).find((p) => p.codigo === nueva.codigoProducto);
    const presentacion = producto?.presentaciones.find((p) => p.codigo === nueva.presentacion);
    if (!producto || !presentacion) throw new Error("Ese producto no se vende en esa presentación");
    const mercado = MERCADO_DE_LA_DEMO;
    const sistema = await this.precioDelSistema(producto.codigo, mercado);
    if (sistema === null) {
      throw new Error(`Todavía no hay un precio de ${producto.nombre} en su mercado contra el cual comparar: publíquelo como precio normal.`);
    }
    const porUnidad = nueva.monto / presentacion.factor;
    if (porUnidad >= sistema) {
      throw new Error(
        `Bs ${porUnidad.toFixed(2)} por ${producto.unidadBase} no es más barato que el precio de ${producto.nombre} ` +
          `en su mercado (Bs ${sistema.toFixed(2)} por ${producto.unidadBase}). Publíquelo como precio normal.`,
      );
    }
    const suyo = this.registro.find((p) => p.idVendedor === yo);
    return {
      combo,
      id: combo ? 0 : this.siguiente++,
      idVendedor: yo,
      codigoMercado: mercado,
      numeroPuesto: suyo?.numero ?? null,
      codigoProducto: producto.codigo,
      monto: nueva.monto,
      presentacion: presentacion.codigo,
      factor: presentacion.factor,
      desde: ahora,
      hasta: ahora + nueva.horas * HORA,
      nota: nueva.nota.trim(),
      estado: "activa",
    };
  }

  async retirarOferta(id: number): Promise<void> {
    const yo = this.sesion();
    const oferta = this.ofertas.find((o) => o.id === id && o.idVendedor === yo);
    if (!oferta) throw new Error(`No existe la oferta ${id}`);
    oferta.estado = "retirada";
  }

  // --- administrador -------------------------------------------------------------

  async ofertasEnRevision(): Promise<OfertaEnRevision[]> {
    this.sesion();
    const productos = await this.catalogo.productos();
    const mercados = await this.catalogo.mercados();
    return this.ofertas
      .filter((o) => o.estado === "en_revision")
      .map((o) => ({
        id: o.id,
        nombreProducto: productos.find((p) => p.codigo === o.codigoProducto)?.nombre ?? o.codigoProducto,
        nombreMercado: mercados.find((m) => m.codigo === o.codigoMercado)?.nombre ?? o.codigoMercado,
        numeroPuesto: o.numeroPuesto,
        monto: o.monto,
        presentacion: o.presentacion,
        hasta: new Date(o.hasta).toISOString(),
        nota: o.nota,
        ...this.cuenta(o.id),
      }));
  }

  async reactivarOferta(id: number): Promise<void> {
    this.enRevision(id).estado = "activa";
  }

  /** C146: el administrador da de baja una oferta pausada o activa. Nada se borra: queda «retirada». */
  async retirarOfertaRevisada(id: number): Promise<void> {
    const oferta = this.ofertas.find((o) => o.id === id && (o.estado === "en_revision" || o.estado === "activa"));
    if (!oferta) throw new Error(`No existe la oferta ${id}`);
    oferta.estado = "retirada";
  }

  // --- auxiliares ------------------------------------------------------------------

  private sesion(): number {
    const id = idDeSesion(this.almacen);
    if (id === null) throw new Error("Sesión inválida o vencida. Vuelva a ingresar.");
    return id;
  }

  private enRevision(id: number): OfertaGuardada {
    const oferta = this.ofertas.find((o) => o.id === id && o.estado === "en_revision");
    if (!oferta) throw new Error(`No existe la oferta ${id}`);
    return oferta;
  }

  private cuenta(idOferta: number): { confirmaron: number; desmintieron: number } {
    let confirmaron = 0;
    let desmintieron = 0;
    for (const [clave, laVioAsi] of this.confirmaciones) {
      if (!clave.startsWith(`${idOferta}:`)) continue;
      if (laVioAsi) confirmaron++;
      else desmintieron++;
    }
    return { confirmaron, desmintieron };
  }

  private async precioDelSistema(codigoProducto: string, codigoMercado: string): Promise<number | null> {
    try {
      return (await this.precios.precioEnMercado(codigoProducto, codigoMercado)).rango.centro;
    } catch {
      return null;
    }
  }

  private async vista(o: OfertaGuardada): Promise<Oferta | null> {
    const sistema = await this.precioDelSistema(o.codigoProducto, o.codigoMercado);
    const porUnidad = o.monto / o.factor;
    if (sistema === null || porUnidad >= sistema) return null;
    const producto = (await this.catalogo.productos()).find((p) => p.codigo === o.codigoProducto);
    const mercado = (await this.catalogo.mercados()).find((m) => m.codigo === o.codigoMercado);
    if (!producto || !mercado) return null;
    const precio = await this.precios.precioEnMercado(o.codigoProducto, o.codigoMercado);
    const puesto = this.registro.find((p) => p.codigoMercado === o.codigoMercado && p.numero === o.numeroPuesto);
    return {
      id: o.id,
      codigoProducto: o.codigoProducto,
      nombreProducto: producto.nombre,
      unidadBase: producto.unidadBase,
      codigoMercado: o.codigoMercado,
      nombreMercado: mercado.nombre,
      numeroPuesto: o.numeroPuesto,
      nombrePuesto: puesto?.nombre ?? null,
      monto: o.monto,
      presentacion: o.presentacion,
      precioPorUnidadBase: Math.round(porUnidad * 10_000) / 10_000,
      desde: new Date(o.desde).toISOString(),
      hasta: new Date(o.hasta).toISOString(),
      nota: o.nota,
      combo: o.combo ?? null,
      precioSistema: sistema,
      procedenciaSistema: precio.procedencia,
      ahorroPorUnidad: Math.round((sistema - porUnidad) * 100) / 100,
      ahorroRelativo: Math.round(((sistema - porUnidad) / sistema) * 10_000) / 10_000,
      ...this.cuenta(o.id),
    };
  }
}
