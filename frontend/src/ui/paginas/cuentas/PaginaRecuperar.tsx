import { useState, type FormEvent } from "react";

import type { Contenedor } from "@/infraestructura/contenedor";
import { Icono } from "@/ui/componentes/Iconos";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { parametroDeRuta } from "@/ui/hooks/useRuta";

/**
 * Olvidé mi contraseña. Dos momentos: pedir el enlace (#/recuperar) y, desde
 * el correo, elegir la nueva (#/restablecer?token=...).
 */
export function PaginaRecuperar({
  contenedor,
  modo,
  alTerminar,
}: {
  contenedor: Contenedor;
  modo: "recuperar" | "restablecer";
  alTerminar: () => void;
}) {
  return (
    <section className="formulario-cuenta" aria-labelledby="titulo-recuperar">
      <div className="formulario-cuenta__cabeza">
        <span className="formulario-cuenta__icono" aria-hidden="true">
          <Icono nombre="ingresar" tamano={22} />
        </span>
        <div>
          <h2 id="titulo-recuperar">{modo === "recuperar" ? "Recuperar la contraseña" : "Elegir una contraseña nueva"}</h2>
          <p className="tenue">
            {modo === "recuperar"
              ? "Le mandamos un enlace al correo de su cuenta."
              : "El enlace del correo sirve una sola vez."}
          </p>
        </div>
      </div>
      {modo === "recuperar" ? (
        <PedirEnlace contenedor={contenedor} />
      ) : (
        <ElegirNueva contenedor={contenedor} alTerminar={alTerminar} />
      )}
    </section>
  );
}

function PedirEnlace({ contenedor }: { contenedor: Contenedor }) {
  const [correo, setCorreo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [listo, setListo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await contenedor.recuperar.pedirEnlace(correo);
      setListo(true);
    } catch (e) {
      setError(textoDeError(e));
    } finally {
      setEnviando(false);
    }
  }

  // El mismo mensaje exista o no la cuenta: no se revela qué correos hay.
  if (listo) {
    return (
      <MensajeAviso texto="Si el correo está registrado, le llegará un enlace para elegir una contraseña nueva. Revise también el correo no deseado." />
    );
  }
  return (
    <form className="formulario" onSubmit={(e) => void enviar(e)}>
      <label className="campo">
        <span>Correo</span>
        <input type="email" required value={correo} onChange={(e) => setCorreo(e.target.value)} autoComplete="email" />
      </label>
      <MensajeError texto={error} />
      <button type="submit" className="boton" disabled={enviando}>
        {enviando ? "Enviando…" : "Mandar el enlace"}
      </button>
    </form>
  );
}

function ElegirNueva({ contenedor, alTerminar }: { contenedor: Contenedor; alTerminar: () => void }) {
  const [contrasena, setContrasena] = useState("");
  const [repetida, setRepetida] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [listo, setListo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await contenedor.recuperar.restablecer(parametroDeRuta("token"), contrasena, repetida);
      setListo(true);
    } catch (e) {
      setError(textoDeError(e));
    } finally {
      setEnviando(false);
    }
  }

  if (listo) {
    return (
      <>
        <MensajeAviso texto="Listo: su contraseña cambió. Ya puede ingresar con la nueva." />
        <button type="button" className="boton" onClick={alTerminar}>
          Ingresar
        </button>
      </>
    );
  }
  return (
    <form className="formulario" onSubmit={(e) => void enviar(e)}>
      <div className="campo">
        <label htmlFor="contrasena-nueva">Contraseña nueva</label>
        <input
          id="contrasena-nueva"
          type="password"
          required
          minLength={8}
          aria-describedby="contrasena-nueva-ayuda"
          value={contrasena}
          onChange={(e) => setContrasena(e.target.value)}
          autoComplete="new-password"
        />
        <small id="contrasena-nueva-ayuda" className="tenue">
          Al menos 8 caracteres, con letras y números.
        </small>
      </div>
      <label className="campo">
        <span>Repita la contraseña</span>
        <input
          type="password"
          required
          value={repetida}
          onChange={(e) => setRepetida(e.target.value)}
          autoComplete="new-password"
        />
      </label>
      <MensajeError texto={error} />
      <button type="submit" className="boton" disabled={enviando}>
        {enviando ? "Guardando…" : "Guardar la contraseña nueva"}
      </button>
    </form>
  );
}
