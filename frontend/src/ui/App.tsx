import { useMemo, useState } from "react";

import { crearContenedor } from "@/infraestructura/contenedor";
import { TarjetaMercado } from "@/ui/componentes/TarjetaMercado";
import { useComparativa } from "@/ui/hooks/useComparativa";

const PRODUCTOS = [
  { codigo: "tomate", nombre: "Tomate" },
  { codigo: "papa", nombre: "Papa holandesa" },
  { codigo: "arroz", nombre: "Arroz de primera" },
];

export default function App() {
  const contenedor = useMemo(() => crearContenedor(), []);
  const [producto, setProducto] = useState("tomate");
  const { datos, cargando, error, reintentar } = useComparativa(contenedor, producto);

  return (
    <div className="app">
      <header className="app__cabecera">
        <h1>PrecioJusto</h1>
        <p>¿Dónde conviene comprar hoy en La Paz?</p>
      </header>

      <nav className="selector" aria-label="Elegir producto">
        {PRODUCTOS.map((p) => (
          <button
            key={p.codigo}
            type="button"
            className={`selector__opcion${producto === p.codigo ? " selector__opcion--activa" : ""}`}
            aria-pressed={producto === p.codigo}
            onClick={() => setProducto(p.codigo)}
          >
            {p.nombre}
          </button>
        ))}
      </nav>

      {cargando && <p className="estado">Consultando precios…</p>}

      {error && (
        <div className="estado estado--error" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => void reintentar()}>
            Reintentar
          </button>
        </div>
      )}

      {datos && !cargando && (
        <>
          {datos.ahorro > 0 && (
            <p className="ahorro">
              Entre el más barato y el más caro hay <strong>Bs {datos.ahorro.toFixed(2)}</strong> de
              diferencia por kilo.
            </p>
          )}
          <div className="lista">
            {datos.opciones.map((item, i) => (
              <TarjetaMercado key={item.mercado.codigo} item={item} destacado={i === 0} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

