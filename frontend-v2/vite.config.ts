import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        // Allow override (BACKEND_PROXY_TARGET=http://backend:80 inside Docker compose,
        // http://localhost:8000 when running Vite directly on the host).
        target: process.env.BACKEND_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
      // Profile photos: backend mints signed `/imgproxy/...` URLs; forward to backend
      // which proxies to the imgproxy container. In prod, CloudFlare/ALB routes this.
      '/imgproxy': {
        target: process.env.BACKEND_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
