/**
 * Adaptador HTTP de sesión y administración. Traduce los DTO en
 * snake_case de la API al modelo del dominio; nada fuera de este archivo
 * conoce la forma de esas respuestas.
 */
import type {
  AdministracionRepositorio,
  NuevaCuenta,
  SesionRepositorio,
} from "@/aplicacion/puertos";
import type { EstadoReporte, Permiso, ReporteEnRevision, Rol, Usuario } from "@/dominio/modelo";
import type { ClienteHttp } from "@/infraestructura/http/clienteHttp";

interface UsuarioDto {
  id: number;
  correo: string;
  nombre: string;
  rol: Rol;
  activo: boolean;
  creado_en: string;
  permisos: Permiso[];
  codigo_punto_venta?: string | null;
}

export interface ReporteDto {
  id: number;
  codigo_producto: string;
  codigo_mercado: string;
  monto: number;
  unidad: string;
  id_autor: number;
  creado_en: string;
  estado: EstadoReporte;
  motivo_rechazo: string | null;
}

function aUsuario(d: UsuarioDto): Usuario {
  return {
    id: d.id,
    correo: d.correo,
    nombre: d.nombre,
    rol: d.rol,
    activo: d.activo,
    creadoEn: d.creado_en,
    permisos: d.permisos,
    codigoPuntoVenta: d.codigo_punto_venta ?? null,
  };
}

export function aReporte(d: ReporteDto): ReporteEnRevision {
  return {
    id: d.id,
    codigoProducto: d.codigo_producto,
    codigoMercado: d.codigo_mercado,
    monto: d.monto,
    unidad: d.unidad,
    idAutor: d.id_autor,
    creadoEn: d.creado_en,
    estado: d.estado,
    motivoRechazo: d.motivo_rechazo ?? null,
  };
}

export class CuentasApi implements SesionRepositorio, AdministracionRepositorio {
  constructor(private readonly http: ClienteHttp) {}

  async ingresar(correo: string, contrasena: string): Promise<{ token: string; usuario: Usuario }> {
    const d = await this.http.post<{ token: string; usuario: UsuarioDto }>("/auth/ingresar", {
      correo,
      contrasena,
    });
    return { token: d.token, usuario: aUsuario(d.usuario) };
  }

  async registrarse(cuenta: NuevaCuenta): Promise<Usuario> {
    return aUsuario(await this.http.post<UsuarioDto>("/auth/registro", cuenta));
  }

  async yo(): Promise<Usuario> {
    return aUsuario(await this.http.get<UsuarioDto>("/auth/yo"));
  }

  async usuarios(): Promise<Usuario[]> {
    return (await this.http.get<UsuarioDto[]>("/admin/usuarios")).map(aUsuario);
  }

  async crearUsuario(cuenta: NuevaCuenta & { rol: Rol }): Promise<Usuario> {
    return aUsuario(await this.http.post<UsuarioDto>("/admin/usuarios", cuenta));
  }

  async actualizarUsuario(
    id: number,
    cambios: { rol?: Rol; activo?: boolean; codigoPuntoVenta?: string | null },
  ): Promise<Usuario> {
    const { codigoPuntoVenta, ...resto } = cambios;
    // El puesto viaja solo si se quiere cambiar: null lo quita, ausente lo deja.
    const cuerpo = codigoPuntoVenta === undefined ? resto : { ...resto, codigo_punto_venta: codigoPuntoVenta };
    return aUsuario(await this.http.patch<UsuarioDto>(`/admin/usuarios/${id}`, cuerpo));
  }

  async restablecerContrasena(id: number, contrasena: string): Promise<Usuario> {
    return aUsuario(await this.http.put<UsuarioDto>(`/admin/usuarios/${id}/contrasena`, { contrasena }));
  }

  async reportes(estado: EstadoReporte | "todos"): Promise<ReporteEnRevision[]> {
    return (await this.http.get<ReporteDto[]>("/admin/reportes", { estado })).map(aReporte);
  }

  async aprobarReporte(id: number): Promise<ReporteEnRevision> {
    return aReporte(await this.http.post<ReporteDto>(`/admin/reportes/${id}/aprobar`));
  }

  async rechazarReporte(id: number, motivo: string): Promise<ReporteEnRevision> {
    return aReporte(await this.http.post<ReporteDto>(`/admin/reportes/${id}/rechazar`, { motivo }));
  }
}
