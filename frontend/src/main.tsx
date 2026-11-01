import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "@/ui/App";
import "@/ui/estilos.css";

const contenedor = document.getElementById("root");
if (!contenedor) throw new Error("Falta el elemento #root en index.html");

createRoot(contenedor).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Se puede instalar en el celular como una app (C137). Solo en la versión
// construida: en desarrollo un service worker guardaría archivos viejos.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    void navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  });
}
