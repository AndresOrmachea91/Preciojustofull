/**
 * @vitest-environment jsdom
 *
 * Olvidé mi contraseña: la regla de la contraseña (dominio), el flujo con el
 * adaptador en memoria y la pantalla.
 */
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { RecuperarContrasena } from "@/aplicacion/casosUso/cuentas/recuperarContrasena";
import { problemaConContrasena } from "@/dominio/modelo";
import { AlmacenSesionMemoria } from "@/infraestructura/almacen/almacenSesion";
import { CuentasMemoria } from "@/infraestructura/memoria/CuentasMemoria";
import App from "@/ui/App";

beforeEach(() => {
  window.location.hash = "";
});
afterEach(cleanup);

describe("contraseña (dominio)", () => {
  it("pide 8 caracteres con letras y números, como el backend", () => {
    expect(problemaConContrasena("corta1")).toMatch(/8 caracteres/);
    expect(problemaConContrasena("12345678")).toMatch(/letras y números/);
    expect(problemaConContrasena("soloLetras")).toMatch(/letras y números/);
    expect(problemaConContrasena("nueva1234")).toBeNull();
  });
});

describe("recuperar (caso de uso + memoria)", () => {
  it("el enlace cambia la contraseña y no sirve dos veces", async () => {
    const cuentas = new CuentasMemoria(new AlmacenSesionMemoria());
    const caso = new RecuperarContrasena(cuentas);

    await caso.pedirEnlace("vecino@correo.bo");
    await caso.pedirEnlace("nadie@correo.bo"); // no falla ni manda nada
    expect(cuentas.enlacesEnviados.map((e) => e.correo)).toEqual(["vecino@correo.bo"]);

    const [{ token }] = cuentas.enlacesEnviados;
    await expect(caso.restablecer(token, "nueva1234", "otra12345")).rejects.toThrow(/no coinciden/);
    await caso.restablecer(token, "nueva1234", "nueva1234");
    expect((await cuentas.ingresar("vecino@correo.bo", "nueva1234")).usuario.correo).toBe("vecino@correo.bo");
    await expect(caso.restablecer(token, "otra12345", "otra12345")).rejects.toThrow(/no es válido/);
  });
});

describe("recuperar (pantalla)", () => {
  it("desde el ingreso se pide el enlace y la respuesta no delata si el correo existe", async () => {
    render(<App />);
    fireEvent.click(await screen.findByRole("link", { name: "Ingresar" }));
    fireEvent.click(screen.getByRole("button", { name: "¿Olvidó su contraseña?" }));
    expect(screen.getByRole("heading", { name: "Recuperar la contraseña" })).toBeDefined();

    fireEvent.change(screen.getByLabelText("Correo"), { target: { value: "nadie@correo.bo" } });
    fireEvent.submit(screen.getByRole("button", { name: "Mandar el enlace" }).closest("form")!);
    expect((await screen.findByRole("status")).textContent).toMatch(/Si el correo está registrado/);
  });

  it("con un enlace que no sirve lo dice", async () => {
    window.location.hash = "#/restablecer?token=enlace:99:nada";
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Contraseña nueva"), { target: { value: "nueva1234" } });
    fireEvent.change(screen.getByLabelText("Repita la contraseña"), { target: { value: "nueva1234" } });
    fireEvent.submit(screen.getByRole("button", { name: "Guardar la contraseña nueva" }).closest("form")!);
    expect((await screen.findByRole("alert")).textContent).toMatch(/no es válido o ya venció/);
  });
});
