/**
 * Achica una foto del celular antes de mandarla: una foto de 12 MP pesa
 * 4 MB y con datos móviles no sube; a 1280 px de lado y en JPEG queda en
 * unos 200 KB y se sigue reconociendo el puesto. Devuelve una data URL.
 */
const LADO_MAXIMO = 1280;
const CALIDAD = 0.8;

export async function achicarFoto(archivo: File): Promise<string> {
  if (!archivo.type.startsWith("image/")) throw new Error("Elija una foto (JPG, PNG o WEBP)");
  const url = URL.createObjectURL(archivo);
  try {
    const imagen = await cargar(url);
    const escala = Math.min(1, LADO_MAXIMO / Math.max(imagen.naturalWidth, imagen.naturalHeight));
    const lienzo = document.createElement("canvas");
    lienzo.width = Math.max(1, Math.round(imagen.naturalWidth * escala));
    lienzo.height = Math.max(1, Math.round(imagen.naturalHeight * escala));
    const contexto = lienzo.getContext("2d");
    if (!contexto) throw new Error("Este navegador no puede preparar la foto");
    contexto.drawImage(imagen, 0, 0, lienzo.width, lienzo.height);
    return lienzo.toDataURL("image/jpeg", CALIDAD);
  } finally {
    URL.revokeObjectURL(url);
  }
}

function cargar(url: string): Promise<HTMLImageElement> {
  return new Promise((resolver, rechazar) => {
    const imagen = new Image();
    imagen.onload = () => resolver(imagen);
    imagen.onerror = () => rechazar(new Error("No se pudo abrir la foto: pruebe con otra"));
    imagen.src = url;
  });
}
