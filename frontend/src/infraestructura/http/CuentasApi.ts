/**
 * Adaptador HTTP de sesión y administración. Traduce los DTO en
 * snake_case de la API al modelo del dominio; nada fuera de este archivo
 * conoce la forma de esas respuestas.
 */
import type {
  AdministracionRepositorio,
  AuditoriaRepositorio,
  NuevaCuenta,
  SesionRepositorio,
} from "@/aplicacion/puertos";
import type {
  AccionAuditada,
  Auditoria,
  EstadoReporte,
  NivelConfianza,
  Permiso,
  Referencias,
  RegistroAuditado,
  ReporteEnRevision,
  Rol,
  Usuario,
} from "@/dominio/modelo";
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
  auditoria?: AuditoriaDto | null;
}

interface AuditoriaDto {
  creado_en: string;
  creado_por: string;
  modificado_en: string | null;
  modificado_por: string | null;
  eliminado: boolean;
}

interface RegistroAuditadoDto {
  tabla: string;
  clave: string;
  descripcion: string;
  accion: AccionAuditada;
  ultimo_cambio: string;
  auditoria: AuditoriaDto;
}

interface ReferenciasDto {
  roles: { codigo: Rol; nombre: string; descripcion: string; permisos: { codigo: Permiso; descripcion: string }[] }[];
  fuentes: {
    codigo: string;
    nombre: string;
    descripcion: string;
    confianza_base: NivelConfianza;
    deriva_de: string | null;
    automatica: boolean;
    url: string | null;
  }[];
}

function aAuditoria(d: AuditoriaDto): Auditoria {
  return {
    creadoEn: d.creado_en,
    creadoPor: d.creado_por,
    modificadoEn: d.modificado_en,
    modificadoPor: d.modificado_por,
    eliminado: d.eliminado,
  };
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
    auditoria: d.auditoria ? aAuditoria(d.auditoria) : null,
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

export class CuentasApi implements SesionRepositorio, AdministracionRepositorio, AuditoriaRepositorio {
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

  async usuarios(incluirEliminados = false): Promise<Usuario[]> {
    const consulta = incluirEliminados ? { incluir_eliminados: "true" } : undefined;
    return (await this.http.get<UsuarioDto[]>("/admin/usuarios", consulta)).map(aUsuario);
  }

  eliminarUsuario(id: number): Promise<void> {
    return this.http.delete(`/admin/usuarios/${id}`);
  }

  tablasAuditadas(): Promise<string[]> {
    return this.http.get<string[]>("/admin/auditoria/tablas");
  }

  async auditoria(tabla?: string, limite = 50): Promise<RegistroAuditado[]> {
    const datos = await this.http.get<RegistroAuditadoDto[]>("/admin/auditoria", { tabla, limite: String(limite) });
    return datos.map((d) => ({
      tabla: d.tabla,
      clave: d.clave,
      descripcion: d.descripcion,
      accion: d.accion,
      ultimoCambio: d.ultimo_cambio,
      auditoria: aAuditoria(d.auditoria),
    }));
  }

  async referencias(): Promise<Referencias> {
    const d = await this.http.get<ReferenciasDto>("/admin/referencias");
    return {
      roles: d.roles,
      fuentes: d.fuentes.map((f) => ({
        codigo: f.codigo,
        nombre: f.nombre,
        descripcion: f.descripcion,
        confianzaBase: f.confianza_base,
        derivaDe: f.deriva_de,
        automatica: f.automatica,
        url: f.url,
      })),
    };
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
