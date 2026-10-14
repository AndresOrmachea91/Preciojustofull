import { useEffect, useState } from "react";

import { autorDelUltimoCambio, type AccionAuditada, type RegistroAuditado } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";
import { MensajeError, textoDeError } from "@/ui/componentes/Mensajes";
import { fechaCorta } from "@/ui/formato";

const ACCION: Record<AccionAuditada, string> = { creado: "Creado", modificado: "Modificado", eliminado: "Eliminado" };

/** Cómo se llama cada tabla para una persona. */
const NOMBRE_TABLA: Record<string, string> = {
  usuario: "Cuentas",
  vendedor: "Vendedores",
  rol: "Roles",
  permiso: "Permisos",
  rol_permiso: "Permisos por rol",
  fuente: "Fuentes de precios",
  producto: "Productos",
  mercado: "Mercados y tiendas",
  observacion_precio: "Precios",
  reporte_precio: "Reportes de usuarios",
  lista_compras: "Listas de compras",
  item_lista_compras: "Productos de las listas",
  corrida_fuente: "Recolecciones",
  intento_fuente: "Consultas al SIIP",
};

/**
 * Quién creó, cambió o eliminó cada registro y cuándo. No hay una tabla de
 * logs: son los 5 campos que cada fila de cada tabla lleva consigo.
 */
export function Auditoria({ contenedor }: { contenedor: Contenedor }) {
  const [tablas, setTablas] = useState<string[]>([]);
  const [tabla, setTabla] = useState("");
  const [registros, setRegistros] = useState<RegistroAuditado[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void contenedor.verAuditoria.tablas().then(setTablas, (e) => setError(textoDeError(e)));
  }, [contenedor]);

  useEffect(() => {
    setRegistros(null);
    contenedor.verAuditoria.recientes(tabla, 100).then(setRegistros, (e) => setError(textoDeError(e)));
  }, [contenedor, tabla]);

  return (
    <>
      <p className="tenue">
        Cada fila de cada tabla guarda quién la creó, quién la modificó, cuándo, y si fue eliminada. Nada se borra
        de verdad: lo eliminado queda marcado.
      </p>
      <label className="campo campo--angosto">
        <span>Tabla</span>
        <select value={tabla} onChange={(e) => setTabla(e.target.value)}>
          <option value="">Todas</option>
          {tablas.map((t) => (
            <option key={t} value={t}>
              {NOMBRE_TABLA[t] ?? t}
            </option>
          ))}
        </select>
      </label>

      <MensajeError texto={error} />
      {!registros && !error && <p className="estado">Cargando la auditoría…</p>}
      {registros && registros.length === 0 && <p className="estado">No hay registros en esta tabla.</p>}
      {registros && registros.length > 0 && (
        <div className="tabla-envoltura">
          <table className="tabla" aria-label="Últimos cambios">
            <thead>
              <tr>
                <th>Cuándo</th>
                <th>Tabla</th>
                <th>Registro</th>
                <th>Qué pasó</th>
                <th>Quién</th>
              </tr>
            </thead>
            <tbody>
              {registros.map((r) => (
                <tr key={`${r.tabla}-${r.clave}`}>
                  <td className="tabla__numero">{fechaCorta(r.ultimoCambio)}</td>
                  <td>{NOMBRE_TABLA[r.tabla] ?? r.tabla}</td>
                  <td>
                    <span className="auditoria-celda">
                      <span>{r.descripcion || r.clave}</span>
                      {r.descripcion && <span className="tenue">{r.clave}</span>}
                    </span>
                  </td>
                  <td>
                    <span className={`accion accion--${r.accion}`}>{ACCION[r.accion]}</span>
                  </td>
                  <td>{autorDelUltimoCambio(r.auditoria)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
