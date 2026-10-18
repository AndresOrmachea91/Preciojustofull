import { useEffect, useMemo, useState } from "react";

import {
  etiquetaTipo,
  filtrarDirectorio,
  type EntradaDirectorio,
  type TipoPuntoVenta,
} from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { Icono } from "@/ui/componentes/Iconos";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { hrefMercado } from "@/ui/hooks/useRuta";

const TIPOS: readonly { valor: TipoPuntoVenta | "todos"; texto: string }[] = [
  { valor: "todos", texto: "Todos" },
  { valor: "mercado", texto: "Mercados" },
  { valor: "supermercado", texto: "Supermercados" },
  { valor: "minimarket", texto: "Minimarkets" },
  { valor: "mayorista", texto: "Mayoristas" },
];

/**
 * El directorio de lugares (C134): la puerta para "entrar" a un mercado y
 * ver sus precios, sus puestos y sus ofertas. Primero los que tienen ofertas.
 */
export function PaginaMercados({ contenedor }: { contenedor: Contenedor }) {
  const [entradas, setEntradas] = useState<EntradaDirectorio[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [texto, setTexto] = useState("");
  const [tipo, setTipo] = useState<TipoPuntoVenta | "todos">("todos");

  useEffect(() => {
    contenedor.mercados.directorio().then(setEntradas, (e) => setError(textoDeError(e)));
  }, [contenedor]);

  const visibles = useMemo(() => filtrarDirectorio(entradas ?? [], texto, tipo), [entradas, texto, tipo]);
  const tiposPresentes = TIPOS.filter((t) => t.valor === "todos" || entradas?.some((e) => e.mercado.tipo === t.valor));

  return (
    <section aria-labelledby="titulo-mercados">
      <h2 id="titulo-mercados" className="seccion">
        Mercados
      </h2>
      <p className="app__lema">Entre a un mercado para ver cuánto sale cada producto ahí, sus puestos y sus ofertas.</p>

      <div className="barra barra--directorio">
        <input
          className="barra__buscar"
          type="search"
          placeholder="Buscar por nombre o zona (Rodríguez, Villa Fátima, Sopocachi…)"
          aria-label="Buscar mercados"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
        <div className="segmentado" role="group" aria-label="Tipo de lugar">
          {tiposPresentes.map((t) => (
            <button
              key={t.valor}
              type="button"
              className="segmentado__opcion"
              aria-pressed={tipo === t.valor}
              onClick={() => setTipo(t.valor)}
            >
              {t.texto}
            </button>
          ))}
        </div>
      </div>

      <MensajeError texto={error} />
      {!entradas && !error && <p className="estado">Cargando los mercados…</p>}
      {entradas && visibles.length === 0 && <p className="estado">Ningún lugar coincide.</p>}
      {entradas && visibles.length > 0 && (
        <p className="tenue">
          {visibles.length} {visibles.length === 1 ? "lugar" : "lugares"}
        </p>
      )}

      <ul className="directorio" aria-label="Lugares">
        {visibles.map(({ mercado, puestos, ofertas, sectores }) => (
          <li key={mercado.codigo}>
            <a className="directorio__lugar" href={hrefMercado(mercado.codigo)}>
              <span className={`directorio__icono directorio__icono--${mercado.tipo}`} aria-hidden="true">
                <Icono nombre={mercado.tipo === "mercado" ? "mercado" : "puesto"} tamano={20} />
              </span>
              <span className="directorio__texto">
                <strong>{mercado.nombre}</strong>
                <span className="tenue">
                  {etiquetaTipo(mercado.tipo)} · {mercado.macrodistrito || mercado.zona}
                </span>
                <span className="directorio__cifras">
                  {ofertas > 0 && (
                    <span className="chip chip--oferta">
                      {ofertas} {ofertas === 1 ? "oferta" : "ofertas"}
                    </span>
                  )}
                  {puestos > 0 && (
                    <span className="chip">
                      {puestos} {puestos === 1 ? "puesto" : "puestos"}
                    </span>
                  )}
                  {sectores > 0 && (
                    <span className="chip">
                      {sectores} {sectores === 1 ? "sector" : "sectores"}
                    </span>
                  )}
                </span>
              </span>
              <Icono nombre="flecha" tamano={18} />
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
