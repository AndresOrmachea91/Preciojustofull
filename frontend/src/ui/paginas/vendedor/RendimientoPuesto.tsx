import { useEffect, useState } from "react";

import { DIAS_CORTOS, rendimientoDeEjemplo } from "@/dominio/servicio/rendimientoDeEjemplo";
import type { MiOferta, Puesto } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";

/**
 * Cómo le va a su puesto (C145). Por ahora con DATOS DE EJEMPLO, y la
 * pantalla lo dice: el conteo real llega con el piloto.
 */
export function RendimientoPuesto({ contenedor, ofertas }: { contenedor: Contenedor; ofertas?: readonly MiOferta[] | null }) {
  const [puesto, setPuesto] = useState<Puesto | null>(null);
  const [propias, setPropias] = useState<readonly MiOferta[]>(ofertas ?? []);

  useEffect(() => {
    contenedor.miPuesto.puesto().then(setPuesto, () => setPuesto(null));
  }, [contenedor]);
  useEffect(() => {
    if (ofertas) setPropias(ofertas);
    else contenedor.miPuesto.misOfertas().then(setPropias, () => setPropias([]));
  }, [contenedor, ofertas]);

  if (!puesto) return null;
  const activas = propias.filter((o) => o.estado === "activa");
  const combos = new Set(activas.filter((o) => o.combo).map((o) => o.combo)).size;
  const r = rendimientoDeEjemplo(`${puesto.codigoMercado}/${puesto.numero}`, {
    sueltas: activas.filter((o) => !o.combo).length,
    combos,
  });
  const maximo = Math.max(...r.porDia, 1);

  return (
    <section className="rendimiento" aria-labelledby="titulo-rendimiento">
      <div className="rendimiento__cabeza">
        <h3 id="titulo-rendimiento" className="subseccion">
          Cómo le va a su puesto esta semana
        </h3>
        <span className="insignia insignia--ejemplo">Datos de ejemplo</span>
      </div>
      <div className="rendimiento__cifras">
        <Dato valor={r.visitasSemana} texto="personas vieron su puesto" destacado />
        <Dato valor={r.vieronOfertas} texto="vieron sus ofertas" />
        <Dato valor={r.enPlanes} texto="veces apareció en un plan de compra" />
        <Dato valor={r.abrieronWhatsapp} texto="le escribieron por WhatsApp" />
      </div>
      <div className="rendimiento__semana" aria-label="Visitas por día">
        {r.porDia.map((n, i) => (
          <div key={DIAS_CORTOS[i]} className="rendimiento__dia">
            <span className="rendimiento__barra" style={{ height: `${Math.max(6, (n / maximo) * 100)}%` }} title={`${n} visitas`} />
            <span className="tenue">{DIAS_CORTOS[i]}</span>
          </div>
        ))}
      </div>
      <p className="rendimiento__consejo">
        <strong>Sus ofertas en combo pueden llegar a más gente:</strong> una oferta suelta llega a unas{" "}
        <strong>{r.alcanceOferta}</strong> personas; un combo, a unas <strong>{r.alcanceCombo}</strong>, porque aparece a
        quien busca cualquiera de sus productos.
      </p>
      <p className="tenue rendimiento__nota">
        Estos números son de ejemplo, para mostrar la idea. Las visitas reales se van a contar desde el piloto.
      </p>
    </section>
  );
}

function Dato({ valor, texto, destacado = false }: { valor: number; texto: string; destacado?: boolean }) {
  return (
    <div className={`panorama__cifra${destacado ? " panorama__cifra--destacada" : ""}`}>
      <strong>{valor}</strong>
      <span>{texto}</span>
    </div>
  );
}
