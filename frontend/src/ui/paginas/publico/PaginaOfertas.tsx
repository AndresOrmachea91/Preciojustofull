import { useCallback, useEffect, useMemo, useState } from "react";

import { sinTildes, type Oferta, type Usuario } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { TarjetaOferta } from "@/ui/componentes/TarjetaOferta";

/**
 * Ofertas de hoy (C133): las que los caseros declararon y que de verdad son
 * más baratas que el precio del sistema. El orden es la recomendación, y se
 * explica en la página: mayor ahorro real primero. Nadie paga por aparecer.
 */
export function PaginaOfertas({ contenedor, usuario }: { contenedor: Contenedor; usuario: Usuario | null }) {
  const [ofertas, setOfertas] = useState<Oferta[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [texto, setTexto] = useState("");

  const cargar = useCallback(() => {
    contenedor.ofertas.vigentes().then(setOfertas, (e) => setError(textoDeError(e)));
  }, [contenedor]);
  useEffect(cargar, [cargar]);

  const visibles = useMemo(() => {
    const buscado = sinTildes(texto.trim());
    return (ofertas ?? []).filter(
      (o) => !buscado || sinTildes(`${o.nombreProducto} ${o.nombreMercado} ${o.nombrePuesto ?? ""}`).includes(buscado),
    );
  }, [ofertas, texto]);

  return (
    <section aria-labelledby="titulo-ofertas">
      <h2 id="titulo-ofertas" className="seccion">
        Ofertas de hoy
      </h2>
      <p className="app__lema">Lo que los caseros rebajaron, comparado con el precio de todos.</p>

      <div className="candado" aria-label="Cómo se ordenan y qué se exige">
        <p>
          <strong>Cómo se ordenan:</strong> primero la que más ahorra frente al precio del sistema en ese mercado. Ese
          precio se calcula <strong>sin</strong> lo que dice el propio casero, así nadie elige su "precio de antes".
          Nadie paga por aparecer arriba.
        </p>
        <p className="tenue">
          Cada oferta vence sola (24 a 72 horas), un casero tiene como mucho tres a la vez y, si dos compradores dicen
          que no estaba así, se pausa hasta que la revisen.
        </p>
      </div>

      {ofertas && ofertas.length > 0 && (
        <input
          className="barra__buscar barra__buscar--suelta"
          type="search"
          placeholder="Buscar por producto o mercado"
          aria-label="Buscar ofertas"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
      )}

      <MensajeError texto={error} />
      {!ofertas && !error && <p className="estado">Buscando ofertas…</p>}
      {ofertas && ofertas.length === 0 && (
        <p className="estado">
          Hoy no hay ofertas vigentes. Los caseros las publican desde «Mi puesto», y solo aparecen si son más baratas
          que el precio del sistema.
        </p>
      )}
      {ofertas && ofertas.length > 0 && visibles.length === 0 && <p className="estado">Ninguna oferta coincide.</p>}

      <div className="ofertas">
        {visibles.map((o) => (
          <TarjetaOferta key={o.id} oferta={o} contenedor={contenedor} usuario={usuario} />
        ))}
      </div>
    </section>
  );
}
