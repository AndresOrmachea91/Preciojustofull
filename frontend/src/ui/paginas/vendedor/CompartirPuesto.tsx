import { useEffect, useState } from "react";
import QRCode from "qrcode";

import { nombreDelPuesto, type Puesto } from "@/dominio/modelo";
import { Icono } from "@/ui/componentes/Iconos";
import { hrefPuesto } from "@/ui/hooks/useRuta";

/**
 * La vitrina del casero (C140): un enlace y un código QR que llevan directo
 * a su puesto, con su foto y sus precios. Lo pega en el puesto o lo manda
 * por WhatsApp a sus caseras de siempre: así el sistema le trae clientes y
 * no es una tarea más.
 */
export function CompartirPuesto({ puesto }: { puesto: Puesto }) {
  const enlace = `${globalThis.location?.origin ?? ""}/${hrefPuesto(puesto.codigoMercado, puesto.numero)}`;
  const nombre = nombreDelPuesto(puesto);
  const [qr, setQr] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    let vigente = true;
    QRCode.toDataURL(enlace, { margin: 1, width: 480, color: { dark: "#0e3b32", light: "#ffffff" } }).then(
      (url) => vigente && setQr(url),
      () => vigente && setQr(null),
    );
    return () => {
      vigente = false;
    };
  }, [enlace]);

  const mensaje = `Vea mis precios de hoy en PrecioJusto: ${nombre}. ${enlace}`;

  async function copiar() {
    try {
      await navigator.clipboard.writeText(enlace);
      setCopiado(true);
    } catch {
      setCopiado(false);
    }
  }

  return (
    <section className="compartir" aria-labelledby="titulo-compartir">
      {qr && <img className="compartir__qr" src={qr} alt={`Código QR que lleva a ${nombre}`} />}
      <div className="compartir__texto">
        <h3 id="titulo-compartir" className="subseccion">
          Comparta su puesto
        </h3>
        <p className="tenue">
          Imprima el código y péguelo en su puesto, o mándelo por WhatsApp: quien lo abre ve su foto y sus precios de hoy.
        </p>
        <div className="compartir__botones">
          <a
            className="boton boton--icono"
            href={`https://wa.me/?text=${encodeURIComponent(mensaje)}`}
            target="_blank"
            rel="noreferrer"
          >
            <Icono nombre="flecha" tamano={16} />
            Mandar por WhatsApp
          </a>
          <button type="button" className="boton boton--suave" onClick={() => void copiar()}>
            {copiado ? "Enlace copiado" : "Copiar enlace"}
          </button>
          {qr && (
            <a className="boton boton--suave" href={qr} download={`qr-${puesto.codigoMercado}-${puesto.numero}.png`}>
              Descargar el QR
            </a>
          )}
        </div>
      </div>
    </section>
  );
}
