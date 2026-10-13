/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly DEV: boolean
  readonly PROD: boolean
  readonly MODE: string
  readonly VITE_MAPBOX_ACCESS_TOKEN: string
  readonly VITE_LAUNCH_SERVICES?: string
  readonly VITE_LAUNCH_API_PORTAL?: string
  readonly VITE_LAUNCH_REPORT_CATALOG?: string
  readonly VITE_LAUNCH_WORKHUB?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
