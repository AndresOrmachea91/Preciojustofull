import type { PrecioEnMercado } from "@/dominio/modelo";
import { etiquetaTipo, explicacionProcedencia, publicaRango } from "@/dominio/modelo";
import { Confianza } from "@/ui/componentes/Confianza";
import { Procedencia } from "@/ui/componentes/Procedencia";

interface Props {
  readonly item: PrecioEnMercado;
  readonly destacado?: boolean;
}

export function TarjetaMercado({ item, destacado = false }: Props) {
  const { mercado, precio } = item;
  const rango = publicaRango(mercado.tipo);

  return (
    <article
      className={`tarjeta tarjeta--${precio.procedencia}${destacado ? " tarjeta--destacada" : ""}`}
      data-procedencia={precio.procedencia}
    >
      <header className="tarjeta__cabecera">
        <div>
          <h3 className="tarjeta__nombre">{mercado.nombre}</h3>
          <p className="tarjeta__zona">
            {etiquetaTipo(mercado.tipo)} · {mercado.macrodistrito || mercado.zona}
          </p>
        </div>
        <div className="tarjeta__insignias">
          <Procedencia valor={precio.procedencia} />
          {destacado && <span className="insignia">Más conveniente</span>}
        </div>
      </header>

      <p className="tarjeta__precio">
        {rango ? (
          <>
            Bs {precio.rango.minimo.toFixed(2)} <span className="tenue">a</span>{" "}
            {precio.rango.maximo.toFixed(2)}
          </>
        ) : (
          <>Bs {precio.rango.centro.toFixed(2)}</>
        )}
        <span className="tarjeta__unidad"> por {precio.unidad}</span>
      </p>

      <footer className="tarjeta__pie">
        <Confianza nivel={precio.confianza} />
        <span className="tenue">
          {precio.observacionesUsadas}{" "}
          {precio.observacionesUsadas === 1 ? "observación" : "observaciones"}
        </span>
      </footer>

      {precio.procedencia === "estimado" && (
        <p className="tarjeta__nota tarjeta__nota--estimado">{explicacionProcedencia(precio, mercado)}</p>
      )}

      {rango && (
        <p className="tarjeta__nota">
          En mercados grandes el precio varía entre puestos, por eso se publica un rango.
        </p>
      )}
    </article>
  );
}

