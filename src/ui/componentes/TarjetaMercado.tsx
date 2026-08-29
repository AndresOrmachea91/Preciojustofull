import type { PrecioEnMercado } from "@/dominio/modelo";
import { publicaRango } from "@/dominio/modelo";
import { Confianza } from "@/ui/componentes/Confianza";

interface Props {
  readonly item: PrecioEnMercado;
  readonly destacado?: boolean;
}

export function TarjetaMercado({ item, destacado = false }: Props) {
  const { mercado, precio } = item;
  const rango = publicaRango(mercado.tipo);

  return (
    <article className={`tarjeta${destacado ? " tarjeta--destacada" : ""}`}>
      <header className="tarjeta__cabecera">
        <div>
          <h3 className="tarjeta__nombre">{mercado.nombre}</h3>
          <p className="tarjeta__zona">{mercado.zona}</p>
        </div>
        {destacado && <span className="insignia">Más conveniente</span>}
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
          {precio.observacionesUsadas === 1 ? "fuente" : "fuentes"}
        </span>
      </footer>

      {rango && (
        <p className="tarjeta__nota">
          En mercados grandes el precio varía entre puestos, por eso se publica un rango.
        </p>
      )}
    </article>
  );
}

