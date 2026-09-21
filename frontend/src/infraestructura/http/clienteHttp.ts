/**
 * Cliente HTTP. Detalle de infraestructura: es el único archivo del
 * frontend que sabe que existe `fetch`.
 */
export class ErrorApi extends Error {
  constructor(
    message: string,
    readonly estado: number,
  ) {
    super(message);
    this.name = "ErrorApi";
  }
}

export class ClienteHttp {
  // GET idénticos en vuelo se comparten: dos hooks que piden lo mismo (y
  // StrictMode, que en desarrollo ejecuta los efectos dos veces) producen
  // UNA petición al servidor, no cuatro. Contra una base remota cada
  // /comparar cuesta segundos; no se paga dos veces.
  private readonly enVuelo = new Map<string, Promise<unknown>>();

  constructor(private readonly baseUrl: string) {}

  async get<T>(ruta: string, params?: Record<string, string | undefined>): Promise<T> {
    const url = new URL(this.baseUrl + ruta);
    for (const [clave, valor] of Object.entries(params ?? {})) {
      if (valor !== undefined) url.searchParams.set(clave, valor);
    }
    const clave = url.toString();
    const pendiente = this.enVuelo.get(clave);
    if (pendiente) return pendiente as Promise<T>;
    const peticion = this.enviar<T>(clave, { method: "GET" }).finally(() => this.enVuelo.delete(clave));
    this.enVuelo.set(clave, peticion);
    return peticion;
  }

  async post<T>(ruta: string, cuerpo: unknown): Promise<T> {
    return this.enviar<T>(this.baseUrl + ruta, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    });
  }

  private async enviar<T>(url: string, init: RequestInit): Promise<T> {
    const respuesta = await fetch(url, init);
    if (!respuesta.ok) {
      const detalle = await respuesta.text().catch(() => "");
      throw new ErrorApi(
        detalle || `La consulta falló con estado ${respuesta.status}`,
        respuesta.status,
      );
    }
    return (await respuesta.json()) as T;
  }
}

