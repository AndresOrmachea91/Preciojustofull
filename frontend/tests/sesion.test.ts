/**
 * Sesión y administración sobre los adaptadores en memoria y el HTTP.
 *
 * Lo que se fija: el token se guarda solo si el ingreso salió bien, viaja
 * en la cabecera Authorization, una sesión vencida se descarta sola, y el
 * mensaje de error que ve la persona es el texto del backend, no su JSON.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { Administrar } from "@/aplicacion/casosUso/administrar";
import { GestionarSesion } from "@/aplicacion/casosUso/gestionarSesion";
import { AlmacenSesionMemoria } from "@/infraestructura/almacen/almacenSesion";
import { ClienteHttp } from "@/infraestructura/http/clienteHttp";
import { CuentasApi } from "@/infraestructura/http/CuentasApi";
import { ADMIN_DEMO, CuentasMemoria } from "@/infraestructura/memoria/CuentasMemoria";

afterEach(() => vi.unstubAllGlobals());

function enMemoria() {
  const almacen = new AlmacenSesionMemoria();
  const cuentas = new CuentasMemoria(almacen);
  return { almacen, sesion: new GestionarSesion(cuentas, almacen), administrar: new Administrar(cuentas) };
}

describe("GestionarSesion", () => {
  it("un ingreso fallido no guarda nada", async () => {
    const { almacen, sesion } = enMemoria();
    await expect(sesion.ingresar(ADMIN_DEMO.correo, "equivocada")).rejects.toThrow("incorrectos");
    expect(almacen.leer()).toBeNull();
  });

  it("ingresar guarda el token y restaurar recupera la cuenta", async () => {
    const { almacen, sesion } = enMemoria();
    const u = await sesion.ingresar(ADMIN_DEMO.correo, ADMIN_DEMO.contrasena);
    expect(u.rol).toBe("administrador");
    expect(almacen.leer()).not.toBeNull();
    expect((await sesion.restaurar())?.id).toBe(u.id);

    sesion.salir();
    expect(await sesion.restaurar()).toBeNull();
  });

  it("registrarse crea un usuario común y deja la sesión iniciada", async () => {
    const { sesion } = enMemoria();
    const u = await sesion.registrarse({ correo: "Ana@Correo.bo", nombre: "Ana", contrasena: "clave1234" });
    expect(u.rol).toBe("usuario");
    expect(u.permisos).toEqual(["gestionar_listas", "reportar_precio"]);
    expect((await sesion.restaurar())?.correo).toBe("ana@correo.bo");
  });

  it("un token que ya no sirve se descarta al restaurar", async () => {
    const { almacen, sesion } = enMemoria();
    almacen.guardar("memoria:999");
    expect(await sesion.restaurar()).toBeNull();
    expect(almacen.leer()).toBeNull();
  });
});

describe("Administrar", () => {
  it("no deja sin administradores y exige motivo para rechazar", async () => {
    const { sesion, administrar } = enMemoria();
    const admin = await sesion.ingresar(ADMIN_DEMO.correo, ADMIN_DEMO.contrasena);

    await expect(administrar.cambiarRol(admin.id, "usuario")).rejects.toThrow("al menos un administrador");
    await expect(administrar.rechazar(1, " ")).rejects.toThrow("motivo");

    const [primero] = await administrar.reportes();
    expect((await administrar.aprobar(primero.id)).estado).toBe("aprobado");
    await expect(administrar.aprobar(primero.id)).rejects.toThrow("ya fue revisado");
  });

  it("un usuario común no ve la lista de cuentas", async () => {
    const { sesion, administrar } = enMemoria();
    await sesion.ingresar("vecino@correo.bo", "vecino1234");
    await expect(administrar.usuarios()).rejects.toThrow("permiso");
  });
});

describe("CuentasApi", () => {
  function servidor(respuestas: Record<string, { estado?: number; cuerpo: unknown }>) {
    const pedidos: { url: string; init: RequestInit }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (entrada: RequestInfo | URL, init: RequestInit = {}) => {
        const url = String(entrada);
        pedidos.push({ url, init });
        const clave = Object.keys(respuestas).find((k) => url.includes(k));
        const r = clave ? respuestas[clave] : { estado: 404, cuerpo: { detail: "no" } };
        return new Response(JSON.stringify(r.cuerpo), { status: r.estado ?? 200 });
      }),
    );
    return pedidos;
  }

  const USUARIO = {
    id: 7, correo: "ana@pj.bo", nombre: "Ana", rol: "vendedor", activo: true,
    creado_en: "2026-10-04T12:00:00Z", permisos: ["publicar_precio_propio", "reportar_precio"], codigo_punto_venta: "rodriguez",
  };

  it("traduce la sesión y manda el token en las peticiones siguientes", async () => {
    const pedidos = servidor({
      "/auth/ingresar": { cuerpo: { token: "abc.def.ghi", tipo: "bearer", usuario: USUARIO } },
      "/auth/yo": { cuerpo: USUARIO },
    });
    const almacen = new AlmacenSesionMemoria();
    const api = new CuentasApi(new ClienteHttp("http://api.test/api/v1", () => almacen.leer()));
    const sesion = new GestionarSesion(api, almacen);

    const u = await sesion.ingresar("ana@pj.bo", "clave1234");

    expect(u).toMatchObject({ id: 7, rol: "vendedor", creadoEn: "2026-10-04T12:00:00Z", codigoPuntoVenta: "rodriguez" });
    expect(new Headers(pedidos[0].init.headers).get("Authorization")).toBeNull();
    await sesion.restaurar();
    expect(new Headers(pedidos[1].init.headers).get("Authorization")).toBe("Bearer abc.def.ghi");
  });

  it("muestra el texto del error del backend, no su JSON", async () => {
    servidor({ "/admin/usuarios/1": { estado: 409, cuerpo: { detail: "Debe quedar al menos un administrador activo" } } });
    const api = new CuentasApi(new ClienteHttp("http://api.test/api/v1"));
    await expect(api.actualizarUsuario(1, { rol: "usuario" })).rejects.toThrow(
      /^Debe quedar al menos un administrador activo$/,
    );
  });

  it("traduce los reportes y manda el motivo del rechazo", async () => {
    const pedidos = servidor({
      "/admin/reportes/3/rechazar": {
        cuerpo: {
          id: 3, codigo_producto: "tomate", codigo_mercado: "rodriguez", monto: 95, unidad: "KILO",
          id_autor: 7, creado_en: "2026-10-04T12:00:00Z", estado: "rechazado", motivo_rechazo: "Fuera de rango",
        },
      },
    });
    const api = new CuentasApi(new ClienteHttp("http://api.test/api/v1"));
    const r = await api.rechazarReporte(3, "Fuera de rango");
    expect(r).toMatchObject({ codigoProducto: "tomate", estado: "rechazado", motivoRechazo: "Fuera de rango" });
    expect(JSON.parse(String(pedidos[0].init.body))).toEqual({ motivo: "Fuera de rango" });
  });
});
