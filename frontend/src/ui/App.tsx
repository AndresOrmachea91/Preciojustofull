import { useMemo, type ReactNode } from "react";

import { puede, type Usuario } from "@/dominio/modelo";
import { crearContenedor } from "@/infraestructura/contenedor";
import { BarraLateral, esAdministrador } from "@/ui/componentes/BarraLateral";
import { useRuta, type Ruta } from "@/ui/hooks/useRuta";
import { useSesion } from "@/ui/hooks/useSesion";
// Pantallas agrupadas por quién las usa: publico/, cuentas/, usuario/, vendedor/, administracion/.
import { PaginaAdmin } from "@/ui/paginas/administracion/PaginaAdmin";
import { PaginaIngreso } from "@/ui/paginas/cuentas/PaginaIngreso";
import { PaginaRecuperar } from "@/ui/paginas/cuentas/PaginaRecuperar";
import { PaginaPrecios } from "@/ui/paginas/publico/PaginaPrecios";
import { PaginaConfiabilidad } from "@/ui/paginas/publico/PaginaConfiabilidad";
import { PaginaMercado } from "@/ui/paginas/publico/PaginaMercado";
import { PaginaMercados } from "@/ui/paginas/publico/PaginaMercados";
import { PaginaOfertas } from "@/ui/paginas/publico/PaginaOfertas";
import { PaginaReferencias } from "@/ui/paginas/publico/PaginaReferencias";
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
  // #/ingresar y #/registrarse son la misma pantalla en dos modos.
  const cuenta = ruta === "ingresar" || ruta === "registrarse" ? ruta : null;

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
          <a
            href="#/ingresar"
            className="boton"
            onClick={(e) => {
              e.preventDefault();
              ir("ingresar");
            }}
          >
            Ingresar
          </a>
        )}
      </div>
    );
  }

  return (
    <div className="app">
      <BarraLateral usuario={usuario} verificando={verificando} ruta={ruta} ir={ir} salir={sesion.salir} />

      <main className="app__contenido">
        {cuenta && !usuario && (
          <PaginaIngreso
            sesion={sesion}
            modo={cuenta}
            cambiarModo={ir}
            alOlvidar={() => ir("recuperar")}
            alIngresar={(u) => ir(inicioDe(u))}
          />
        )}

        {(ruta === "recuperar" || ruta === "restablecer") && (
          <PaginaRecuperar contenedor={contenedor} modo={ruta} alTerminar={() => ir("ingresar")} />
        )}

        {ruta === "mi-cuenta" &&
          protegida(puede(usuario, "gestionar_listas"), "usuario", () => <PaginaUsuario contenedor={contenedor} />)}

        {ruta === "mi-puesto" &&
          protegida(puede(usuario, "publicar_precio_propio"), "vendedor", (u) => (
            <PaginaVendedor contenedor={contenedor} vendedor={u} />
          ))}

        {ruta === "admin" &&
          protegida(esAdministrador(usuario), "administrador", (u) => (
            <PaginaAdmin contenedor={contenedor} usuario={u} />
          ))}

        {ruta === "confiabilidad" && <PaginaConfiabilidad contenedor={contenedor} />}

        {ruta === "mercados" && <PaginaMercados contenedor={contenedor} />}

        {ruta === "mercado" && <PaginaMercado contenedor={contenedor} usuario={usuario} />}

        {ruta === "ofertas" && <PaginaOfertas contenedor={contenedor} usuario={usuario} />}

        {ruta === "referencias" && <PaginaReferencias contenedor={contenedor} />}

        {(ruta === "precios" || (cuenta && usuario)) && <PaginaPrecios contenedor={contenedor} usuario={usuario} />}
      </main>
    </div>
  );
}
