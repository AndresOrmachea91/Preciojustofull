import { porcentaje, type PlanDeVerificacion } from "@/dominio/modelo";

/**
 * Cuánto se mueve cada precio de un mes a otro en la ciudad (A5020). Una
 * barra por producto, en la misma escala: lo que más se mueve es lo que
 * más se equivoca cuando se estima, y lo que primero hay que ir a medir.
 */
export function VariacionPorProducto({ plan, cuantos = 12 }: { plan: PlanDeVerificacion; cuantos?: number }) {
  const lista = plan.variaciones.slice(0, cuantos);
  if (lista.length === 0) return null;
  const maximo = Math.max(...lista.map((v) => v.cambioMensual), 0.0001);
  return (
    <section aria-labelledby="titulo-variacion">
      <h3 id="titulo-variacion" className="subseccion">
        Cuánto se mueve cada precio
      </h3>
      <p className="tenue confiabilidad__texto">
        Cambio típico del precio de la ciudad de un mes al siguiente, en el último año. Un producto que se mueve
        mucho envejece rápido: su estimado se equivoca más.
      </p>
      <ol className="barras" aria-label="Productos de más a menos variables">
        {lista.map((v) => (
          <li key={v.producto.codigo} className="barras__fila">
            <span className="barras__nombre">{v.producto.nombre}</span>
            <span className="barras__pista" aria-hidden="true">
              <span className="barras__barra" style={{ width: `${(v.cambioMensual / maximo) * 100}%` }} />
            </span>
            <span className="barras__valor">
              {porcentaje(v.cambioMensual)}
              <span className="tenue"> al mes</span>
            </span>
          </li>
        ))}
      </ol>
      {plan.variaciones.length > cuantos && (
        <p className="tenue">
          Y {plan.variaciones.length - cuantos} productos más, que se mueven menos.
        </p>
      )}
    </section>
  );
}

/**
 * Qué falta medir primero (A4230): lo que nadie midió, lo vencido y lo que
 * más se mueve. Es la lista con que sale la próxima ronda de campo, y es
 * pública: dice dónde el sistema todavía estima.
 */
export function QueFaltaMedir({ plan, cuantos = 6 }: { plan: PlanDeVerificacion; cuantos?: number }) {
  const pendientes = plan.productos.filter((p) => p.puntaje > 0);
  if (pendientes.length === 0) {
    return (
      <p className="aviso">Todos los productos tienen un precio medido y vigente en cada lugar. No falta nada por medir.</p>
    );
  }
  const lugares = plan.lugares.length;
  return (
    <section aria-labelledby="titulo-falta">
      <h3 id="titulo-falta" className="subseccion">
        Lo que falta medir primero
      </h3>
      <p className="tenue confiabilidad__texto">
        Primero lo que nadie midió, lo que ya venció y lo que más se mueve. Así cada ronda de campo le quita al
        sistema la mayor duda posible, en vez de medir todo por igual.
      </p>
      <ol className="pendientes">
        {pendientes.slice(0, cuantos).map((p) => (
          <li key={p.producto.codigo} className="pendientes__fila">
            <div className="pendientes__cabeza">
              <strong>{p.producto.nombre}</strong>
              <span className="tenue">
                medido en {p.lugaresAlDia} de {lugares} {lugares === 1 ? "lugar" : "lugares"}
              </span>
            </div>
            {p.motivos.length > 0 && <p className="pendientes__motivos">{p.motivos.join(" · ")}</p>}
          </li>
        ))}
      </ol>
      {pendientes.length > cuantos && (
        <p className="tenue">Hay {pendientes.length - cuantos} productos más en la lista.</p>
      )}
    </section>
  );
}
