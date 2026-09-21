import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    // Las pruebas de dominio y aplicación no tocan el navegador y corren en
    // node. Las de interfaz declaran jsdom con un docblock en su cabecera.
    environment: "node",
    include: ["tests/**/*.test.{ts,tsx}"],
    // Las pruebas corren SIEMPRE con el adaptador en memoria, aunque
    // .env.local diga "http": una prueba no debe depender de que haya un
    // backend levantado ni de lo que cada máquina tenga configurado.
    env: { VITE_ORIGEN_DATOS: "memoria" },
  },
});

