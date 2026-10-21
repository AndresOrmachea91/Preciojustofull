/**
 * Mercados por dentro, puestos y ofertas en memoria (C133, C134): el plan B
 * de la demo y el adaptador de las pruebas. Aplica los mismos candados que
 * el backend —vence sola, máximo tres, más barata que el precio del sistema,
 * dos desmentidos la pausan— para que la interfaz se comporte igual sin red.
 */
import type {
  AlmacenSesion,
  CatalogoRepositorio,
  DatosPuesto,
  HistorialRepositorio,
  MercadosRepositorio,
  NuevaOferta,
  OfertasRepositorio,
  OfertasVendedorRepositorio,
  PrecioRepositorio,
  RevisionOfertasRepositorio,
} from "@/aplicacion/puertos";
import {
  MAXIMO_OFERTAS_ACTIVAS,
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
}

const HORA = 3_600_000;
// En la demo la única vendedora (Rosa) es del Rodríguez: es su mercado. En
// la API el mercado sale de la cuenta, que asigna el administrador.
const MERCADO_DE_LA_DEMO = "rodriguez";

// La vendedora de la demo (Rosa, id 2) tiene el 14 del Rodríguez; el 22 lo
// registró el administrador y todavía no tiene dueño.
const PUESTOS: (Puesto & { idVendedor: number | null })[] = [
  { id: 1, codigoMercado: "rodriguez", numero: "14", nombre: "Verduras Doña Rosa", rubros: ["hortaliza", "fruta"], referencia: "Pasillo de verduras, frente a la puerta 2", registrado: true, idVendedor: 2 },
  { id: 2, codigoMercado: "rodriguez", numero: "22", nombre: "Papas del Norte", rubros: ["tuberculo"], referencia: "", registrado: true, idVendedor: null },
  { id: 3, codigoMercado: "lanza", numero: "3", nombre: "Abarrotes Mary", rubros: ["abarrote"], referencia: "Planta baja, entrada por la Figueroa", registrado: true, idVendedor: 98 },
];

// Lo último que se supo en algunos puestos (campo y lo que declaró el casero).
const PRECIOS_DE_PUESTO: (PrecioDelPuesto & { codigoMercado: string; numero: string })[] = [
  { codigoMercado: "rodriguez", numero: "14", codigoProducto: "tomate", nombreProducto: "Tomate", monto: 6.5, unidad: "libra", precioPorUnidadBase: 14.13, unidadBase: "kg", fecha: "2026-09-14", fuente: "campo" },
  { codigoMercado: "rodriguez", numero: "22", codigoProducto: "papa", nombreProducto: "Papa holandesa", monto: 80, unidad: "arroba", precioPorUnidadBase: 6.96, unidadBase: "kg", fecha: "2026-09-14", fuente: "vendedor" },
];

export class MercadosMemoria
  implements MercadosRepositorio, OfertasRepositorio, OfertasVendedorRepositorio, RevisionOfertasRepositorio
{
  private readonly puestos = PUESTOS.map((p) => ({ ...p }));
  private readonly ofertas: OfertaGuardada[];
  private readonly confirmaciones = new Map<string, boolean>();
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
      puestos: this.puestos.filter((p) => p.codigoMercado === m.codigo).length,
      ofertas: vigentes.filter((o) => o.codigoMercado === m.codigo).length,
      sectores: mercados.filter((x) => x.codigoPadre === m.codigo).length,
    }));
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
      puestos: this.puestos
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
    const suyo = this.puestos.find((p) => p.idVendedor === yo);
    if (!suyo) return null;
    const { idVendedor: _, ...puesto } = suyo;
    return puesto;
  }

  async guardarMiPuesto(datos: DatosPuesto): Promise<Puesto> {
    const yo = this.sesion();
    const numero = datos.numero.trim().toUpperCase();
    const mercado = MERCADO_DE_LA_DEMO;
    const ocupado = this.puestos.find((p) => p.codigoMercado === mercado && p.numero === numero);
    if (ocupado && ocupado.idVendedor !== null && ocupado.idVendedor !== yo) {
      throw new Error(`Ya existe un puesto en este mercado con el código ${numero}`);
    }
    const suyo = this.puestos.find((p) => p.idVendedor === yo) ?? ocupado;
    const nuevo = { id: suyo?.id ?? this.puestos.length + 1, codigoMercado: mercado, numero, nombre: datos.nombre, rubros: datos.rubros, referencia: datos.referencia, registrado: true, idVendedor: yo };
    if (suyo) Object.assign(suyo, nuevo);
    else this.puestos.push(nuevo);
    const { idVendedor: _, ...puesto } = nuevo;
    return puesto;
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
          estado: o.estado === "activa" && o.hasta <= ahora ? "vencida" : o.estado,
          confirmaron,
          desmintieron,
        };
      });
  }

  async publicarOferta(nueva: NuevaOferta): Promise<void> {
    const yo = this.sesion();
    const ahora = this.ahora();
    const activas = this.ofertas.filter((o) => o.idVendedor === yo && o.estado === "activa" && o.hasta > ahora);
    if (activas.length >= MAXIMO_OFERTAS_ACTIVAS) {
      throw new Error("Ya tiene 3 ofertas activas: retire una o espere a que venza. Si todo está en oferta, nada lo está.");
    }
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
    const suyo = this.puestos.find((p) => p.idVendedor === yo);
    this.ofertas.push({
      id: this.siguiente++,
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
    });
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

  async retirarOfertaRevisada(id: number): Promise<void> {
    this.enRevision(id).estado = "retirada";
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
    const puesto = this.puestos.find((p) => p.codigoMercado === o.codigoMercado && p.numero === o.numeroPuesto);
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
      precioSistema: sistema,
      procedenciaSistema: precio.procedencia,
      ahorroPorUnidad: Math.round((sistema - porUnidad) * 100) / 100,
      ahorroRelativo: Math.round(((sistema - porUnidad) / sistema) * 10_000) / 10_000,
      ...this.cuenta(o.id),
    };
  }
}
