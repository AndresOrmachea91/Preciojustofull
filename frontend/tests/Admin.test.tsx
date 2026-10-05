/**
 * @vitest-environment jsdom
 *
 * El recorrido completo del administrador sobre la interfaz, con los
 * adaptadores en memoria: ingresar, ver las cuentas, cambiar un rol y
 * aprobar un reporte. Y el lado opuesto: sin sesión, la página de
 * administración no muestra nada.
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { ADMIN_DEMO } from "@/infraestructura/memoria/CuentasMemoria";
import App from "@/ui/App";

beforeEach(() => {
  window.location.hash = "";
});
afterEach(cleanup);

async function ingresar(correo: string, contrasena: string) {
  fireEvent.click(await screen.findByRole("button", { name: "Ingresar" }));
  fireEvent.change(screen.getByLabelText("Correo"), { target: { value: correo } });
  fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: contrasena } });
  fireEvent.submit(screen.getByRole("button", { name: "Ingresar" }).closest("form")!);
}

describe("administración", () => {
  it("sin sesión, la página de administración pide ingresar", async () => {
    window.location.hash = "#/admin";
    render(<App />);
    expect(await screen.findByText(/Ingrese con una cuenta de administrador/)).toBeDefined();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("una contraseña equivocada muestra el error y no inicia sesión", async () => {
    render(<App />);
    await ingresar(ADMIN_DEMO.correo, "equivocada");
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Correo o contraseña incorrectos");
    expect(screen.queryByRole("button", { name: "Salir" })).toBeNull();
  });

  it("el administrador ingresa, cambia un rol y aprueba un reporte", async () => {
    render(<App />);
    await ingresar(ADMIN_DEMO.correo, ADMIN_DEMO.contrasena);

    const tabla = await screen.findByRole("table");
    expect(within(tabla).getByText("recolector@preciojusto.bo")).toBeDefined();

    fireEvent.change(within(tabla).getByLabelText("Rol de vecino@correo.bo"), { target: { value: "recolector" } });
    expect(await screen.findByRole("status")).toHaveProperty(
      "textContent",
      "vecino@correo.bo ahora es recolector.",
    );

    fireEvent.click(screen.getByRole("tab", { name: "Reportes por revisar" }));
    const aprobar = await screen.findAllByRole("button", { name: "Aprobar" });
    expect(aprobar).toHaveLength(2);
    fireEvent.click(aprobar[0]);
    await waitFor(() => expect(screen.getAllByRole("button", { name: "Aprobar" })).toHaveLength(1));
  });

  it("un usuario común no ve el acceso a administración", async () => {
    render(<App />);
    await ingresar("vecino@correo.bo", "vecino1234");
    expect(await screen.findByRole("button", { name: "Salir" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Administración" })).toBeNull();
  });
});
