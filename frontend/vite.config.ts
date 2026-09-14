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
  },
});

