import { useMemo, type ReactNode } from "react";

import { puede, type Usuario } from "@/dominio/modelo";
import { crearContenedor } from "@/infraestructura/contenedor";
import { Cabecera, esAdministrador } from "@/ui/componentes/Cabecera";
import { useRuta, type Ruta } from "@/ui/hooks/useRuta";
import { useSesion } from "@/ui/hooks/useSesion";
// Pantallas agrupadas por quién las usa: publico/, cuentas/, usuario/, vendedor/, administracion/.
import { PaginaAdmin } from "@/ui/paginas/administracion/PaginaAdmin";
import { PaginaIngreso } from "@/ui/paginas/cuentas/PaginaIngreso";
import { PaginaPrecios } from "@/ui/paginas/publico/PaginaPrecios";
import { PaginaUsuario } from "@/ui/paginas/usuario/PaginaUsuario";
import { PaginaVendedor } from "@/ui/paginas/vendedor/PaginaVendedor";

/** Adónde va cada rol después de ingresar. */
function inicioDe(usuario: Usuario): Ruta {
  if (esAdministrador(usuario)) return "admin";
  if (puede(usuario, "publicar_precio_propio")) return "mi-puesto";
  return "precios";
}

export default function App() {
  const contenedor = useMemo(() => crearContenedor(), []);
  const sesion = useSesion(contenedor);
  const [ruta, ir] = useRuta();
  const { usuario, verificando } = sesion;

  /** Una página que exige sesión y un permiso; si no, explica por qué no se ve. */
  function protegida(permitido: boolean, quien: string, pagina: (u: Usuario) => ReactNode) {
    if (verificando) return <p className="estado">Verificando la sesión…</p>;
    if (usuario && permitido) return pagina(usuario);
    return (
      <div className="estado estado--error" role="alert">
        <p>
          {usuario
            ? "Su cuenta no tiene permiso para ver esta página."
            : `Ingrese con una cuenta de ${quien} para ver esta página.`}
        </p>
        {!usuario && (
          <button type="button" className="boton" onClick={() => ir("ingresar")}>
            Ingresar
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="app">
      <Cabecera usuario={usuario} verificando={verificando} ruta={ruta} ir={ir} salir={sesion.salir} />

      {ruta === "ingresar" && !usuario && <PaginaIngreso sesion={sesion} alIngresar={(u) => ir(inicioDe(u))} />}

      {ruta === "mi-cuenta" &&
        protegida(puede(usuario, "gestionar_listas"), "usuario", () => <PaginaUsuario contenedor={contenedor} />)}

      {ruta === "mi-puesto" &&
        protegida(puede(usuario, "publicar_precio_propio"), "vendedor", (u) => (
          <PaginaVendedor contenedor={contenedor} vendedor={u} />
        ))}

      {ruta === "admin" &&
        protegida(esAdministrador(usuario), "administrador", (u) => <PaginaAdmin contenedor={contenedor} usuario={u} />)}

      {(ruta === "precios" || (ruta === "ingresar" && usuario)) && <PaginaPrecios contenedor={contenedor} />}
    </div>
  );
}
