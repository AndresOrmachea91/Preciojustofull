import { enlaceLlamar, enlaceWhatsapp, nombreDelPuesto, type Puesto } from "@/dominio/modelo";

/**
 * Cómo contactar al proveedor (C146): llamar o escribir por WhatsApp. Solo
 * aparece si el puesto tiene teléfono (hoy, las distribuidoras).
 */
export function ContactoPuesto({ puesto }: { puesto: Puesto }) {
  if (!puesto.celular) return null;
  const whatsapp = enlaceWhatsapp(
    puesto.celular,
    `Hola, vi ${nombreDelPuesto(puesto)} en PrecioJusto y quería consultar un precio.`,
  );
  return (
    <span className="contacto">
      <a className="contacto__enlace" href={enlaceLlamar(puesto.celular)}>
        Llamar {puesto.celular}
      </a>
      {whatsapp && (
        <a className="contacto__enlace contacto__enlace--whatsapp" href={whatsapp} target="_blank" rel="noreferrer">
          WhatsApp
        </a>
      )}
    </span>
  );
}
