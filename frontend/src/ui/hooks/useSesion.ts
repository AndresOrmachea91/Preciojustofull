import { useCallback, useEffect, useState } from "react";

import type { NuevaCuenta } from "@/aplicacion/puertos";
import type { Usuario } from "@/dominio/modelo";
import type { Contenedor } from "@/infraestructura/contenedor";

export interface EstadoSesion {
  readonly usuario: Usuario | null;
  /** true mientras se verifica la sesión guardada al abrir la página. */
  readonly verificando: boolean;
  ingresar(correo: string, contrasena: string): Promise<Usuario>;
  registrarse(cuenta: NuevaCuenta): Promise<Usuario>;
  salir(): void;
}

export function useSesion(contenedor: Contenedor): EstadoSesion {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [verificando, setVerificando] = useState(true);

  useEffect(() => {
    let vigente = true;
    void contenedor.sesion.restaurar().then((u) => {
      if (!vigente) return;
      setUsuario(u);
      setVerificando(false);
    });
    return () => {
      vigente = false;
    };
  }, [contenedor]);

  const ingresar = useCallback(
    async (correo: string, contrasena: string) => {
      const u = await contenedor.sesion.ingresar(correo, contrasena);
      setUsuario(u);
      return u;
    },
    [contenedor],
  );

  const registrarse = useCallback(
    async (cuenta: NuevaCuenta) => {
      const u = await contenedor.sesion.registrarse(cuenta);
      setUsuario(u);
      return u;
    },
    [contenedor],
  );

  const salir = useCallback(() => {
    contenedor.sesion.salir();
    setUsuario(null);
  }, [contenedor]);

  return { usuario, verificando, ingresar, registrarse, salir };
}
