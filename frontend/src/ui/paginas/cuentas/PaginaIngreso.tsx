import { useState, type FormEvent } from "react";

import type { Usuario } from "@/dominio/modelo";
import { Icono } from "@/ui/componentes/Iconos";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import type { EstadoSesion } from "@/ui/hooks/useSesion";

export type Modo = "ingresar" | "registrarse";

/** Ingresar o crear una cuenta. El modo lo da la ruta (#/ingresar, #/registrarse). */
export function PaginaIngreso({
  sesion,
  modo,
  cambiarModo,
  alOlvidar,
  alIngresar,
}: {
  sesion: EstadoSesion;
  modo: Modo;
  cambiarModo: (modo: Modo) => void;
  alOlvidar: () => void;
  alIngresar: (usuario: Usuario) => void;
}) {
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [quiereVender, setQuiereVender] = useState(false);
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
          : await sesion.registrarse({ correo, nombre, contrasena, quiereVender });
      alIngresar(usuario);
    } catch (e) {
      setError(textoDeError(e));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="formulario-cuenta" aria-labelledby="titulo-cuenta">
      <div className="formulario-cuenta__cabeza">
        <span className="formulario-cuenta__icono" aria-hidden="true">
          <Icono nombre={modo} tamano={22} />
        </span>
        <div>
          <h2 id="titulo-cuenta">{modo === "ingresar" ? "Ingresar" : "Crear una cuenta"}</h2>
          <p className="tenue">
            {modo === "ingresar"
              ? "Para sus listas, sus reportes y su puesto."
              : "Gratis. Arme listas de compras y reporte precios."}
          </p>
        </div>
      </div>
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

        {modo === "registrarse" && (
          <label className="casilla casilla--destacada">
            <input type="checkbox" checked={quiereVender} onChange={(e) => setQuiereVender(e.target.checked)} />
            <span>
              <strong>Quiero vender</strong>
              <small className="tenue">Tengo un puesto en un mercado o una distribuidora y quiero aparecer en el mapa.</small>
            </span>
          </label>
        )}

        <MensajeError texto={error} />

        <button type="submit" className="boton" disabled={enviando}>
          {enviando ? "Enviando…" : modo === "ingresar" ? "Ingresar" : "Crear cuenta"}
        </button>
      </form>

      {modo === "ingresar" && (
        <p className="tenue">
          <button type="button" className="enlace" onClick={alOlvidar}>
            ¿Olvidó su contraseña?
          </button>
        </p>
      )}

      <p className="tenue">
        {modo === "ingresar" ? "¿No tiene cuenta? " : "¿Ya tiene cuenta? "}
        <button
          type="button"
          className="enlace"
          onClick={() => {
            cambiarModo(modo === "ingresar" ? "registrarse" : "ingresar");
            setError(null);
          }}
        >
          {modo === "ingresar" ? "Crear una" : "Ingresar"}
        </button>
      </p>
    </section>
  );
}
