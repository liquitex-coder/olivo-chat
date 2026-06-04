/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_DEMO_TOKEN?: string;
  readonly VITE_DEMO_CONVERSATION_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
