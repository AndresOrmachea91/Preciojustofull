import { useState, type FormEvent } from "react";

import type { Usuario } from "@/dominio/modelo";
import type { EstadoSesion } from "@/ui/hooks/useSesion";

type Modo = "ingresar" | "registrarse";

export function PaginaIngreso({
  sesion,
  alIngresar,
}: {
  sesion: EstadoSesion;
  alIngresar: (usuario: Usuario) => void;
}) {
  const [modo, setModo] = useState<Modo>("ingresar");
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const usuario =
        modo === "ingresar"
          ? await sesion.ingresar(correo, contrasena)
          : await sesion.registrarse({ correo, nombre, contrasena });
      alIngresar(usuario);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo completar la operación");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="formulario-cuenta" aria-labelledby="titulo-cuenta">
      <h2 id="titulo-cuenta" className="seccion">
        {modo === "ingresar" ? "Ingresar" : "Crear una cuenta"}
      </h2>
      <form className="formulario" onSubmit={(e) => void enviar(e)}>
        {modo === "registrarse" && (
          <label className="campo">
            <span>Nombre</span>
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} autoComplete="name" />
          </label>
        )}
        <label className="campo">
          <span>Correo</span>
          <input
            type="email"
            required
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            autoComplete="email"
          />
        </label>
        <label className="campo">
          <span>Contraseña</span>
          <input
            type="password"
            required
            minLength={modo === "registrarse" ? 8 : undefined}
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
            autoComplete={modo === "ingresar" ? "current-password" : "new-password"}
          />
          {modo === "registrarse" && <small className="tenue">Al menos 8 caracteres, con letras y números.</small>}
        </label>

        {error && (
          <p className="estado estado--error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="boton" disabled={enviando}>
          {enviando ? "Enviando…" : modo === "ingresar" ? "Ingresar" : "Crear cuenta"}
        </button>
      </form>

      <p className="tenue">
        {modo === "ingresar" ? "¿No tiene cuenta? " : "¿Ya tiene cuenta? "}
        <button
          type="button"
          className="enlace"
          onClick={() => {
            setModo(modo === "ingresar" ? "registrarse" : "ingresar");
            setError(null);
          }}
        >
          {modo === "ingresar" ? "Crear una" : "Ingresar"}
        </button>
      </p>
    </section>
  );
}
