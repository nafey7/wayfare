/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_GOOGLE_CLIENT_ID: string;
  readonly VITE_GOOGLE_MAPS_API_KEY?: string;
  /** Google Maps Map ID — required for AdvancedMarker (custom HTML pins). Set up in Cloud Console. */
  readonly VITE_GOOGLE_MAPS_MAP_ID?: string;
  readonly VITE_ENV: 'development' | 'staging' | 'production';
  readonly VITE_STRAPI_URL?: string;
  readonly VITE_STRAPI_API_TOKEN?: string;
  readonly VITE_REDDIT_PIXEL_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
