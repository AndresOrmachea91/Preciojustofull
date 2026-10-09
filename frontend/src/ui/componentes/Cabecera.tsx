import { NOMBRE_ROL, puede, type Usuario } from "@/dominio/modelo";
import type { Ruta } from "@/ui/hooks/useRuta";

/** Las secciones que ve cada rol. Mostrar u ocultar es comodidad: quien protege es la API. */
export function seccionesDe(usuario: Usuario | null): { ruta: Ruta; texto: string }[] {
  const secciones: { ruta: Ruta; texto: string }[] = [{ ruta: "precios", texto: "Precios" }];
  if (puede(usuario, "gestionar_listas")) secciones.push({ ruta: "mi-cuenta", texto: "Mis listas y reportes" });
  if (puede(usuario, "publicar_precio_propio") && (usuario?.rol === "vendedor" || usuario?.codigoPuntoVenta)) {
    secciones.push({ ruta: "mi-puesto", texto: "Mi puesto" });
  }
  if (esAdministrador(usuario)) secciones.push({ ruta: "admin", texto: "Administración" });
  return secciones;
}

export function esAdministrador(usuario: Usuario | null): boolean {
  return (
    puede(usuario, "gestionar_usuarios") || puede(usuario, "validar_reportes") || puede(usuario, "gestionar_catalogo")
  );
}

interface Props {
  readonly usuario: Usuario | null;
  readonly verificando: boolean;
  readonly ruta: Ruta;
  readonly ir: (ruta: Ruta) => void;
  readonly salir: () => void;
}

export function Cabecera({ usuario, verificando, ruta, ir, salir }: Props) {
  const secciones = seccionesDe(usuario);

  return (
    <header className="app__cabecera">
      <h1>
        <a href="#/" className="app__marca" onClick={() => ir("precios")}>
          PrecioJusto
        </a>
      </h1>
      <div className="cuenta">
        {usuario ? (
          <>
            {secciones.length > 1 && (
              <nav className="navegacion" aria-label="Secciones">
                {secciones.map((s) => (
                  <button
                    key={s.ruta}
                    type="button"
                    aria-current={ruta === s.ruta ? "page" : undefined}
                    className={`navegacion__enlace${ruta === s.ruta ? " navegacion__enlace--activo" : ""}`}
                    onClick={() => ir(s.ruta)}
                  >
                    {s.texto}
                  </button>
                ))}
              </nav>
            )}
            <span className="cuenta__nombre">
              {usuario.nombre} <span className="cuenta__rol">· {NOMBRE_ROL[usuario.rol]}</span>
            </span>
            <button
              type="button"
              className="boton boton--suave"
              onClick={() => {
                salir();
                ir("precios");
              }}
            >
              Salir
            </button>
          </>
        ) : (
          !verificando &&
          ruta !== "ingresar" && (
            <button type="button" className="boton boton--suave" onClick={() => ir("ingresar")}>
              Ingresar
            </button>
          )
        )}
      </div>
    </header>
  );
}
