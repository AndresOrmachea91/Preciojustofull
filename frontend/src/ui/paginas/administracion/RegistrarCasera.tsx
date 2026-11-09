import { useEffect, useState, type FormEvent } from "react";

import { CATEGORIAS, type CaseraRegistrada, type Mercado } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { hrefPuesto } from "@/ui/hooks/useRuta";

const VACIA = { nombre: "", celular: "", codigoMercado: "", numero: "", nombrePuesto: "", referencia: "" };

/**
 * Registrar a una casera con puesto fijo, desde el mercado (C144). Muchas no
 * se van a registrar solas: el administrador lo hace en su puesto, con su
 * celular, y le anota la clave temporal en un papel.
 */
export function RegistrarCasera({ contenedor }: { contenedor: Contenedor }) {
  const [mercados, setMercados] = useState<Mercado[]>([]);
  const [datos, setDatos] = useState(VACIA);
  const [rubros, setRubros] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [registrada, setRegistrada] = useState<CaseraRegistrada | null>(null);

  useEffect(() => {
    contenedor.catalogo.mercados().then(
      (lista) =>
        setMercados(
          lista.filter((m) => m.tipo === "mercado" && !m.codigoPadre).sort((a, b) => a.nombre.localeCompare(b.nombre)),
        ),
      (e) => setError(textoDeError(e)),
    );
  }, [contenedor]);

  const cambiar = (campo: keyof typeof VACIA) => (e: { target: { value: string } }) =>
    setDatos({ ...datos, [campo]: e.target.value });

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      setRegistrada(await contenedor.administrar.registrarCasera({ ...datos, rubros }));
      setDatos({ ...VACIA, codigoMercado: datos.codigoMercado });
      setRubros([]);
    } catch (err) {
      setError(textoDeError(err));
    } finally {
      setEnviando(false);
    }
  }

  const mercado = (codigo: string) => mercados.find((m) => m.codigo === codigo)?.nombre ?? codigo;

  return (
    <section aria-labelledby="titulo-casera">
      <h3 id="titulo-casera" className="subseccion">
        Registrar a una casera en su puesto
      </h3>
      <p className="tenue">
        Para las caseras con puesto fijo que no se registran solas. Entra con su <strong>celular</strong> (no necesita
        correo) y una clave temporal que se le anota; su puesto aparece en el mapa y en el plan de compra de los
        compradores desde ese momento.
      </p>

      {registrada && (
        <div className="casera-lista" role="status">
          <p>
            <strong>{registrada.nombre}</strong> quedó registrada en {mercado(registrada.codigoMercado)}, puesto{" "}
            {registrada.numero}.
          </p>
          <p className="casera-lista__datos">
            Entra con el celular <strong>{registrada.celular}</strong> y la clave{" "}
            <strong className="casera-lista__clave">{registrada.claveTemporal}</strong>
          </p>
          <p className="tenue">
            Anótesela en un papel ahora: no se vuelve a mostrar. Si la pierde, se la restablece en Usuarios.
          </p>
          <a href={hrefPuesto(registrada.codigoMercado, registrada.numero)}>Ver su puesto (y su QR para imprimir)</a>
        </div>
      )}

      <form className="formulario formulario--recuadro" onSubmit={(e) => void enviar(e)}>
        <div className="formulario__fila">
          <label className="campo">
            <span>Nombre de la casera</span>
            <input value={datos.nombre} onChange={cambiar("nombre")} required autoComplete="off" />
          </label>
          <label className="campo">
            <span>Celular</span>
            <input
              value={datos.celular}
              onChange={cambiar("celular")}
              required
              inputMode="tel"
              placeholder="71234567"
              autoComplete="off"
            />
          </label>
        </div>
        <div className="formulario__fila">
          <label className="campo">
            <span>Mercado</span>
            <select value={datos.codigoMercado} onChange={cambiar("codigoMercado")} required>
              <option value="">Elija el mercado…</option>
              {mercados.map((m) => (
                <option key={m.codigo} value={m.codigo}>
                  {m.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="campo">
            <span>Número de puesto</span>
            <input value={datos.numero} onChange={cambiar("numero")} required placeholder="14 o B-12" autoComplete="off" />
          </label>
        </div>
        <label className="campo">
          <span>Nombre del puesto (opcional)</span>
          <input value={datos.nombrePuesto} onChange={cambiar("nombrePuesto")} placeholder="Verduras Doña Rosa" />
        </label>
        <fieldset className="campo">
          <legend>Qué vende</legend>
          <div className="zonas">
            {CATEGORIAS.map((c) => (
              <button
                key={c.codigo}
                type="button"
                className="filtro"
                aria-pressed={rubros.includes(c.codigo)}
                onClick={() =>
                  setRubros(rubros.includes(c.codigo) ? rubros.filter((r) => r !== c.codigo) : [...rubros, c.codigo])
                }
              >
                {c.nombre}
              </button>
            ))}
          </div>
        </fieldset>
        <label className="campo">
          <span>Cómo encontrarlo (opcional)</span>
          <input value={datos.referencia} onChange={cambiar("referencia")} placeholder="Pasillo de verduras, frente a la puerta 2" />
        </label>
        <MensajeError texto={error} />
        <button type="submit" className="boton" disabled={enviando}>
          {enviando ? "Registrando…" : "Registrar casera"}
        </button>
      </form>
    </section>
  );
}
