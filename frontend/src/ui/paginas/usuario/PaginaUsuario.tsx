import { useState } from "react";

import type { Contenedor } from "@/infraestructura/contenedor";
import { Pestanas } from "@/ui/componentes/Pestanas";
import { MisListas } from "@/ui/paginas/usuario/MisListas";
import { MisReportes } from "@/ui/paginas/usuario/MisReportes";
import { ReportarPrecio } from "@/ui/paginas/usuario/ReportarPrecio";

type Seccion = "listas" | "reportar" | "reportes";

/** Lo que hace el usuario con su cuenta: sus listas, reportar lo que ve y seguir sus reportes. */
export function PaginaUsuario({ contenedor }: { contenedor: Contenedor }) {
  const [seccion, setSeccion] = useState<Seccion>("listas");

  return (
    <section aria-labelledby="titulo-usuario">
      <h2 id="titulo-usuario" className="seccion">
        Mi cuenta
      </h2>
      <Pestanas
        pestanas={[
          { id: "listas", texto: "Mis listas" },
          { id: "reportar", texto: "Reportar un precio" },
          { id: "reportes", texto: "Mis reportes" },
        ]}
        activa={seccion}
        onCambiar={setSeccion}
      />
      {seccion === "listas" && <MisListas contenedor={contenedor} />}
      {seccion === "reportar" && <ReportarPrecio contenedor={contenedor} alEnviar={() => setSeccion("reportes")} />}
      {seccion === "reportes" && <MisReportes contenedor={contenedor} />}
    </section>
  );
}
