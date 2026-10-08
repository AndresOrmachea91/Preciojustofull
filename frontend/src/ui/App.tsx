import { useMemo } from "react";

import { NOMBRE_ROL, puede } from "@/dominio/modelo";
import { crearContenedor } from "@/infraestructura/contenedor";
import { useRuta } from "@/ui/hooks/useRuta";
import { useSesion } from "@/ui/hooks/useSesion";
// Pantallas agrupadas por quién las usa: publico/, cuentas/, usuario/, vendedor/, administracion/.
import { PaginaAdmin } from "@/ui/paginas/administracion/PaginaAdmin";
import { PaginaIngreso } from "@/ui/paginas/cuentas/PaginaIngreso";
import { PaginaPrecios } from "@/ui/paginas/publico/PaginaPrecios";

export default function App() {
  const contenedor = useMemo(() => crearContenedor(), []);
  const sesion = useSesion(contenedor);
  const [ruta, ir] = useRuta();
  const { usuario } = sesion;
  const esAdmin = puede(usuario, "gestionar_usuarios") || puede(usuario, "validar_reportes");

  return (
    <div className="app">
      <header className="app__cabecera">
        <h1>
          <a href="#/" className="app__marca" onClick={() => ir("precios")}>
            PrecioJusto
          </a>
        </h1>
        <nav className="cuenta" aria-label="Cuenta">
          {usuario ? (
            <>
              <span className="cuenta__nombre">
                {usuario.nombre} <span className="cuenta__rol">· {NOMBRE_ROL[usuario.rol]}</span>
              </span>
              {esAdmin && ruta !== "admin" && (
                <button type="button" className="boton boton--suave" onClick={() => ir("admin")}>
                  Administración
                </button>
              )}
              {ruta === "admin" && (
                <button type="button" className="boton boton--suave" onClick={() => ir("precios")}>
                  Ver precios
                </button>
              )}
              <button
                type="button"
                className="boton boton--suave"
                onClick={() => {
                  sesion.salir();
                  ir("precios");
                }}
              >
                Salir
              </button>
            </>
          ) : (
            !sesion.verificando &&
            ruta !== "ingresar" && (
              <button type="button" className="boton boton--suave" onClick={() => ir("ingresar")}>
                Ingresar
              </button>
            )
          )}
        </nav>
      </header>

      {ruta === "ingresar" && !usuario && (
        <PaginaIngreso sesion={sesion} alIngresar={(u) => ir(puede(u, "gestionar_usuarios") ? "admin" : "precios")} />
      )}

      {ruta === "admin" &&
        (sesion.verificando ? (
          <p className="estado">Verificando la sesión…</p>
        ) : esAdmin ? (
          <PaginaAdmin contenedor={contenedor} usuario={usuario!} />
        ) : (
          <div className="estado estado--error" role="alert">
            <p>
              {usuario
                ? "Su cuenta no tiene permiso para administrar."
                : "Ingrese con una cuenta de administrador para ver esta página."}
            </p>
            {!usuario && (
              <button type="button" className="boton" onClick={() => ir("ingresar")}>
                Ingresar
              </button>
            )}
          </div>
        ))}

      {(ruta === "precios" || (ruta === "ingresar" && usuario)) && <PaginaPrecios contenedor={contenedor} />}
    </div>
  );
}
