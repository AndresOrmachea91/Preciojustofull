/**
 * C144: el administrador registra a una casera en su puesto; ella entra con
 * su celular (con o sin +591) y la clave temporal.
 */
import { describe, expect, it } from "vitest";

import { Administrar } from "@/aplicacion/casosUso/administracion/administrarCuentas";
import { GestionarSesion } from "@/aplicacion/casosUso/cuentas/gestionarSesion";
import { celularBoliviano, identificadorDeIngreso } from "@/dominio/modelo";
import { AlmacenSesionMemoria } from "@/infraestructura/almacen/almacenSesion";
import { ADMIN_DEMO, CuentasMemoria } from "@/infraestructura/memoria/CuentasMemoria";

describe("celular de Bolivia", () => {
  it("reconoce el celular con prefijo y espacios, y deja pasar el correo", () => {
    expect(celularBoliviano("+591 712-34567")).toBe("71234567");
    expect(celularBoliviano("51234567")).toBeNull();
    expect(identificadorDeIngreso("71234567")).toBe("71234567@caseras.preciojusto.bo");
    expect(identificadorDeIngreso("rosa@correo.bo")).toBe("rosa@correo.bo");
  });
});

describe("Registrar casera", () => {
  const casera = {
    nombre: "Doña Rosa", celular: "712 34 567", codigoMercado: "lanza", numero: "b-12",
    nombrePuesto: "Verduras Rosa", rubros: ["hortaliza"], referencia: "",
  };

  it("el administrador la registra y ella entra con su celular", async () => {
    const almacen = new AlmacenSesionMemoria();
    const cuentas = new CuentasMemoria(almacen);
    const sesion = new GestionarSesion(cuentas, almacen);
    await sesion.ingresar(ADMIN_DEMO.correo, ADMIN_DEMO.contrasena);

    const r = await new Administrar(cuentas).registrarCasera(casera);
    expect(r.celular).toBe("71234567");

    await sesion.salir();
    const u = await sesion.ingresar("+591 71234567", r.claveTemporal);
    expect(u.rol).toBe("vendedor");
  });

  it("avisa antes de mandar un celular que no es de Bolivia", async () => {
    const cuentas = new CuentasMemoria(new AlmacenSesionMemoria());
    await expect(new Administrar(cuentas).registrarCasera({ ...casera, celular: "123" })).rejects.toThrow(/8 dígitos/);
  });
});
