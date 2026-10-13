/** Acciones de interfaz que repiten varias pruebas, hechas como las haría una persona. */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";

/** Busca un producto en la caja de búsqueda y lo elige de la lista. */
export async function elegirProducto(nombre: string, etiqueta = "Producto", dentro: HTMLElement = document.body) {
  const caja = within(dentro).getByRole("combobox", { name: etiqueta });
  fireEvent.focus(caja);
  fireEvent.change(caja, { target: { value: nombre } });
  const opcion = await waitFor(() => screen.getByRole("option", { name: nombre }));
  fireEvent.mouseDown(opcion);
}
