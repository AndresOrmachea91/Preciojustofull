/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ORIGEN_DATOS?: string;
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

