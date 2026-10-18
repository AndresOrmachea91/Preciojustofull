import { useState } from "react";

import { NOMBRE_ROL, puede, type Usuario } from "@/dominio/modelo";
import { Icono, type NombreIcono } from "@/ui/componentes/Iconos";
import { hrefDe, type Ruta } from "@/ui/hooks/useRuta";

interface Seccion {
  readonly ruta: Ruta;
  readonly texto: string;
  readonly icono: NombreIcono;
}

/** Las secciones que ve cada rol. Mostrar u ocultar es comodidad: quien protege es la API. */
export function seccionesDe(usuario: Usuario | null): Seccion[] {
  return [...seccionesPublicas(), ...seccionesDeCuenta(usuario)];
}

/** Lo que ve cualquiera, con o sin cuenta. */
export function seccionesPublicas(): Seccion[] {
  return [
    { ruta: "precios", texto: "Precios", icono: "precios" },
    // Entrar a un mercado: sus precios, sus puestos y sus ofertas (C134).
    { ruta: "mercados", texto: "Mercados", icono: "mercado" },
    { ruta: "ofertas", texto: "Ofertas de hoy", icono: "oferta" },
    // Pública: cualquiera puede ver cuánto se equivoca el estimado.
    { ruta: "confiabilidad", texto: "¿Qué tan confiable es?", icono: "confiabilidad" },
  ];
}

/** Lo que depende del rol de la cuenta. */
export function seccionesDeCuenta(usuario: Usuario | null): Seccion[] {
  const secciones: Seccion[] = [];
  if (puede(usuario, "gestionar_listas")) {
    secciones.push({ ruta: "mi-cuenta", texto: "Mis listas y reportes", icono: "listas" });
  }
  if (puede(usuario, "publicar_precio_propio") && (usuario?.rol === "vendedor" || usuario?.codigoPuntoVenta)) {
    secciones.push({ ruta: "mi-puesto", texto: "Mi puesto", icono: "puesto" });
  }
  if (esAdministrador(usuario)) secciones.push({ ruta: "admin", texto: "Administración", icono: "admin" });
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

function Enlace({ ruta, actual, texto, icono, alIr }: Seccion & { actual: Ruta; alIr: (ruta: Ruta) => void }) {
  // La ficha de un mercado es parte de "Mercados".
  const activo = ruta === actual || (ruta === "mercados" && actual === "mercado");
  return (
    <a
      href={hrefDe(ruta)}
      className={`lateral__enlace${activo ? " lateral__enlace--activo" : ""}`}
      aria-current={activo ? "page" : undefined}
      onClick={(e) => {
        e.preventDefault();
        alIr(ruta);
      }}
    >
      <Icono nombre={icono} />
      <span>{texto}</span>
    </a>
  );
}

/**
 * La navegación, a la izquierda: arriba las secciones de cada rol, abajo la
 * cuenta (ingresar y crear cuenta, o quién está y salir). En el celular se
 * pliega en una barra con un botón de menú.
 */
export function BarraLateral({ usuario, verificando, ruta, ir, salir }: Props) {
  const [abierta, setAbierta] = useState(false);
  const cerrar = () => setAbierta(false);
  const navegar = (destino: Ruta) => {
    cerrar();
    ir(destino);
  };

  return (
    <aside className={`lateral${abierta ? " lateral--abierta" : ""}`}>
      <div className="lateral__marca">
        <h1 className="lateral__titulo">
          <a
            href={hrefDe("precios")}
            className="lateral__logo"
            onClick={(e) => {
              e.preventDefault();
              navegar("precios");
            }}
          >
            <span className="lateral__sello" aria-hidden="true">
              <Icono nombre="precios" tamano={18} />
            </span>
            PrecioJusto
          </a>
        </h1>
        <button
          type="button"
          className="lateral__menu"
          aria-expanded={abierta}
          aria-controls="lateral-navegacion"
          aria-label={abierta ? "Cerrar el menú" : "Abrir el menú"}
          onClick={() => setAbierta(!abierta)}
        >
          <Icono nombre="menu" />
        </button>
      </div>

      <div id="lateral-navegacion" className="lateral__cuerpo">
        <nav aria-label="Secciones" className="lateral__secciones">
          <p className="lateral__rotulo" aria-hidden="true">
            Explorar
          </p>
          <div className="lateral__grupo">
            {seccionesPublicas().map((s) => (
              <Enlace key={s.ruta} {...s} actual={ruta} alIr={navegar} />
            ))}
          </div>
          {seccionesDeCuenta(usuario).length > 0 && (
            <>
              <p className="lateral__rotulo" aria-hidden="true">
                Mi cuenta
              </p>
              <div className="lateral__grupo">
                {seccionesDeCuenta(usuario).map((s) => (
                  <Enlace key={s.ruta} {...s} actual={ruta} alIr={navegar} />
                ))}
              </div>
            </>
          )}
        </nav>

        <p className="lateral__lema">
          Precios de La Paz con su procedencia: observado si alguien lo midió, estimado si sale del boletín oficial.
          Nadie paga por aparecer.
        </p>

        <div className="lateral__cuenta">
          {usuario ? (
            <>
              <div className="lateral__usuario">
                <span className="lateral__avatar" aria-hidden="true">
                  {usuario.nombre.trim().charAt(0).toUpperCase()}
                </span>
                <span>
                  <strong>{usuario.nombre}</strong>
                  <small>{NOMBRE_ROL[usuario.rol]}</small>
                </span>
              </div>
              <button
                type="button"
                className="lateral__enlace lateral__enlace--boton"
                onClick={() => {
                  cerrar();
                  salir();
                  ir("precios");
                }}
              >
                <Icono nombre="salir" />
                <span>Salir</span>
              </button>
            </>
          ) : (
            !verificando && (
              <nav aria-label="Cuenta" className="lateral__grupo">
                <Enlace ruta="ingresar" actual={ruta} texto="Ingresar" icono="ingresar" alIr={navegar} />
                <Enlace ruta="registrarse" actual={ruta} texto="Crear cuenta" icono="registrarse" alIr={navegar} />
              </nav>
            )
          )}
        </div>
      </div>
    </aside>
  );
}
