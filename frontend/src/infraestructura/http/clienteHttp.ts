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

/** De dónde sale el token de sesión en cada petición; null si no hay sesión. */
export type ProveedorToken = () => string | null;

/**
 * FastAPI responde los errores como {"detail": "..."} o, en los de
 * validación, {"detail": [{"msg": "..."}]}. Se muestra el texto, no el JSON.
 */
function mensajeDeError(cuerpo: string, estado: number): string {
  try {
    const { detail } = JSON.parse(cuerpo) as { detail?: unknown };
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => (d as { msg?: string }).msg ?? String(d)).join("; ");
    }
  } catch {
    // No era JSON: se usa el texto tal cual.
  }
  return cuerpo || `La consulta falló con estado ${estado}`;
}

export class ClienteHttp {
  // GET idénticos en vuelo se comparten: dos hooks que piden lo mismo (y
  // StrictMode, que en desarrollo ejecuta los efectos dos veces) producen
  // UNA petición al servidor, no cuatro. Contra una base remota cada
  // /comparar cuesta segundos; no se paga dos veces.
  private readonly enVuelo = new Map<string, Promise<unknown>>();

  constructor(
    private readonly baseUrl: string,
    private readonly token: ProveedorToken = () => null,
  ) {}

  async get<T>(ruta: string, params?: Record<string, string | undefined>): Promise<T> {
    // baseUrl puede ser absoluta ("http://localhost:8000/api/v1", en
    // desarrollo con Vite) o relativa ("/api/v1", cuando el backend sirve
    // la interfaz y todo vive en el mismo origen).
    const url = new URL(this.baseUrl + ruta, globalThis.location?.origin);
    for (const [clave, valor] of Object.entries(params ?? {})) {
      if (valor !== undefined) url.searchParams.set(clave, valor);
    }
    // El token entra en la clave: dos sesiones distintas no comparten respuesta.
    const clave = `${this.token() ?? ""} ${url.toString()}`;
    const pendiente = this.enVuelo.get(clave);
    if (pendiente) return pendiente as Promise<T>;
    const peticion = this.enviar<T>(url.toString(), { method: "GET" }).finally(() =>
      this.enVuelo.delete(clave),
    );
    this.enVuelo.set(clave, peticion);
    return peticion;
  }

  post<T>(ruta: string, cuerpo?: unknown): Promise<T> {
    return this.conCuerpo<T>("POST", ruta, cuerpo);
  }

  patch<T>(ruta: string, cuerpo: unknown): Promise<T> {
    return this.conCuerpo<T>("PATCH", ruta, cuerpo);
  }

  put<T>(ruta: string, cuerpo: unknown): Promise<T> {
    return this.conCuerpo<T>("PUT", ruta, cuerpo);
  }

  async delete(ruta: string): Promise<void> {
    await this.enviar<void>(this.baseUrl + ruta, { method: "DELETE" });
  }

  private conCuerpo<T>(method: string, ruta: string, cuerpo: unknown): Promise<T> {
    return this.enviar<T>(this.baseUrl + ruta, {
      method,
      headers: { "Content-Type": "application/json" },
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    });
  }

  private async enviar<T>(url: string, init: RequestInit): Promise<T> {
    const token = this.token();
    const headers = new Headers(init.headers);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const respuesta = await fetch(url, { ...init, headers });
    if (!respuesta.ok) {
      const detalle = await respuesta.text().catch(() => "");
      throw new ErrorApi(mensajeDeError(detalle, respuesta.status), respuesta.status);
    }
    // 204: la operación salió bien y no hay nada que devolver (un DELETE).
    if (respuesta.status === 204) return undefined as T;
    return (await respuesta.json()) as T;
  }
}
