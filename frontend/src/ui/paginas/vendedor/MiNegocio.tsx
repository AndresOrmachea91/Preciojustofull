import { useEffect, useState, type FormEvent } from "react";

import { CATEGORIAS, nombreDelPuesto, type Mercado, type Puesto } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { achicarFoto } from "@/ui/foto";
import { Icono } from "@/ui/componentes/Iconos";
import { MapaSelectorUbicacion } from "@/ui/componentes/MapaSelectorUbicacion";
import { MensajeAviso, MensajeError, textoDeError } from "@/ui/componentes/Mensajes";

type Clase = "puesto" | "distribuidora";

interface Props {
  readonly contenedor: Contenedor;
  readonly mercados: readonly Mercado[];
  /** Avisa a la página que el negocio quedó registrado (y en qué punto del mapa). */
  readonly alGuardar: (puesto: Puesto) => void;
}

/**
 * El negocio del casero (C137): su puesto en un mercado —él elige el
 * mercado y el número— o su distribuidora, con su foto. Pensado para el
 * celular: un campo por renglón y la cámara a un toque.
 */
export function MiNegocio({ contenedor, mercados, alGuardar }: Props) {
  const [puesto, setPuesto] = useState<Puesto | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    contenedor.miPuesto.puesto().then(setPuesto, (e) => setError(textoDeError(e)));
  }, [contenedor]);

  if (puesto === undefined && !error) return <p className="estado">Cargando su puesto…</p>;
  return (
    <div className="negocio">
      <MensajeError texto={error} />
      {puesto && <FotoDelPuesto contenedor={contenedor} puesto={puesto} alCambiar={setPuesto} />}
      <FormularioNegocio
        contenedor={contenedor}
        mercados={mercados}
        puesto={puesto ?? null}
        alGuardar={(p) => {
          setPuesto(p);
          alGuardar(p);
        }}
      />
    </div>
  );
}

function FormularioNegocio({
  contenedor,
  mercados,
  puesto,
  alGuardar,
}: {
  contenedor: Contenedor;
  mercados: readonly Mercado[];
  puesto: Puesto | null;
  alGuardar: (p: Puesto) => void;
}) {
  const distribuidoraActual = puesto?.esLocal ? mercados.find((m) => m.codigo === puesto.codigoMercado) : undefined;
  const [clase, setClase] = useState<Clase>(puesto?.esLocal ? "distribuidora" : "puesto");
  const [codigoMercado, setCodigoMercado] = useState(puesto && !puesto.esLocal ? puesto.codigoMercado : "");
  const [numero, setNumero] = useState(puesto && !puesto.esLocal ? puesto.numero : "");
  const [nombre, setNombre] = useState(puesto?.nombre ?? "");
  const [referencia, setReferencia] = useState(puesto?.referencia ?? "");
  const [rubros, setRubros] = useState<string[]>([...(puesto?.rubros ?? [])]);
  const [zona, setZona] = useState(distribuidoraActual?.zona ?? "");
  const [ubicacion, setUbicacion] = useState<{ latitud: number; longitud: number } | null>(
    distribuidoraActual?.latitud !== undefined && distribuidoraActual.longitud !== undefined
      ? { latitud: distribuidoraActual.latitud, longitud: distribuidoraActual.longitud }
      : null,
  );
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  // Solo mercados (y sus sectores, con el nombre del mercado): un puesto no va en una distribuidora.
  const opciones = mercados
    .filter((m) => m.tipo === "mercado")
    .map((m) => ({ codigo: m.codigo, nombre: m.nombre }))
    .sort((a, b) => a.nombre.localeCompare(b.nombre));

  async function guardar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setAviso(null);
    setEnviando(true);
    try {
      const guardado =
        clase === "puesto"
          ? await contenedor.miPuesto.guardarPuesto({ numero, nombre, rubros, referencia, codigoMercado })
          : await contenedor.miPuesto.registrarDistribuidora({
              nombre,
              zona,
              macrodistrito: "",
              latitud: ubicacion?.latitud ?? Number.NaN,
              longitud: ubicacion?.longitud ?? Number.NaN,
              rubros,
              referencia,
            });
      alGuardar(guardado);
      setAviso(`Guardado: ${nombreDelPuesto(guardado)}. Ya aparece en el mapa y en la ficha del mercado.`);
    } catch (e) {
      setError(textoDeError(e));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="formulario formulario--recuadro negocio__formulario" onSubmit={(e) => void guardar(e)} aria-label="Mi negocio">
      <div className="campo">
        <span id="clase-negocio">¿Dónde vende?</span>
        <div className="segmentado segmentado--ancho" role="group" aria-labelledby="clase-negocio">
          <button type="button" className="segmentado__opcion" aria-pressed={clase === "puesto"} onClick={() => setClase("puesto")}>
            Puesto en un mercado
          </button>
          <button
            type="button"
            className="segmentado__opcion"
            aria-pressed={clase === "distribuidora"}
            onClick={() => setClase("distribuidora")}
          >
            Distribuidora
          </button>
        </div>
      </div>

      {clase === "puesto" ? (
        <>
          <label className="campo">
            <span>Mercado</span>
            <select required value={codigoMercado} onChange={(e) => setCodigoMercado(e.target.value)}>
              <option value="">Elija su mercado…</option>
              {opciones.map((m) => (
                <option key={m.codigo} value={m.codigo}>
                  {m.nombre}
                </option>
              ))}
            </select>
          </label>
          <div className="formulario__fila">
            <label className="campo">
              <span>Número del puesto</span>
              <input required maxLength={16} value={numero} onChange={(e) => setNumero(e.target.value)} placeholder="14, B-3…" />
            </label>
            <label className="campo">
              <span>Nombre (opcional)</span>
              <input maxLength={80} value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Verduras Doña Rosa" />
            </label>
          </div>
        </>
      ) : (
        <>
          <div className="formulario__fila">
            <label className="campo">
              <span>Nombre de la distribuidora</span>
              <input required maxLength={80} value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Distribuidora El Sol" />
            </label>
            <label className="campo">
              <span>Zona</span>
              <input maxLength={128} value={zona} onChange={(e) => setZona(e.target.value)} placeholder="Villa Fátima" />
            </label>
          </div>
          <div className="campo">
            <span>Toque el mapa donde está la distribuidora</span>
            <MapaSelectorUbicacion
              latitud={ubicacion?.latitud ?? null}
              longitud={ubicacion?.longitud ?? null}
              onCambiar={(latitud, longitud) => setUbicacion({ latitud, longitud })}
            />
            <span className="tenue">{ubicacion ? "Ubicación marcada. Puede moverla con otro toque." : "Todavía sin marcar."}</span>
          </div>
        </>
      )}

      <label className="campo">
        <span>Cómo encontrarlo (opcional)</span>
        <input
          maxLength={160}
          value={referencia}
          onChange={(e) => setReferencia(e.target.value)}
          placeholder={clase === "puesto" ? "Pasillo de verduras, frente a la puerta 2" : "Al lado del surtidor, portón verde"}
        />
      </label>
      <fieldset className="campo--grupo">
        <legend>Qué vende</legend>
        {CATEGORIAS.map((c) => (
          <label key={c.codigo} className="casilla">
            <input
              type="checkbox"
              checked={rubros.includes(c.codigo)}
              onChange={(e) => setRubros(e.target.checked ? [...rubros, c.codigo] : rubros.filter((r) => r !== c.codigo))}
            />
            {c.nombre}
          </label>
        ))}
      </fieldset>
      <MensajeError texto={error} />
      <MensajeAviso texto={aviso} />
      <div className="formulario__botones">
        <button type="submit" className="boton" disabled={enviando}>
          {enviando ? "Guardando…" : puesto ? "Guardar cambios" : clase === "puesto" ? "Registrar mi puesto" : "Registrar mi distribuidora"}
        </button>
      </div>
    </form>
  );
}

/** La foto del puesto: la reconoce quien llega al mercado. En el celular abre la cámara. */
function FotoDelPuesto({ contenedor, puesto, alCambiar }: { contenedor: Contenedor; puesto: Puesto; alCambiar: (p: Puesto) => void }) {
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function elegir(archivo: File | undefined) {
    if (!archivo) return;
    setError(null);
    setSubiendo(true);
    try {
      alCambiar(await contenedor.miPuesto.ponerFoto(await achicarFoto(archivo)));
    } catch (e) {
      setError(textoDeError(e));
    } finally {
      setSubiendo(false);
    }
  }

  return (
    <section className="foto-puesto" aria-label="Foto del puesto">
      <div className="foto-puesto__marco">
        {puesto.foto ? (
          <img src={puesto.foto} alt={`Foto de ${nombreDelPuesto(puesto)}`} className="foto-puesto__imagen" />
        ) : (
          <span className="foto-puesto__vacia" aria-hidden="true">
            <Icono nombre="mercado" tamano={32} />
          </span>
        )}
      </div>
      <div className="foto-puesto__texto">
        <strong>{nombreDelPuesto(puesto)}</strong>
        <span className="tenue">
          {puesto.foto
            ? "Así lo reconocen los compradores en el mapa."
            : "Una foto del puesto ayuda a que lo encuentren: la lona, el letrero, lo que se vea desde el pasillo."}
        </span>
        <label className="boton boton--suave boton--icono foto-puesto__boton">
          <Icono nombre="camara" tamano={18} />
          {subiendo ? "Subiendo…" : puesto.foto ? "Cambiar foto" : "Tomar o elegir foto"}
          <input
            type="file"
            accept="image/*"
            capture="environment"
            className="visualmente-oculto"
            disabled={subiendo}
            onChange={(e) => void elegir(e.target.files?.[0])}
          />
        </label>
        <MensajeError texto={error} />
      </div>
    </section>
  );
}
