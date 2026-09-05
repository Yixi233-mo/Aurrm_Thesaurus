import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  base: './',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/query': 'http://127.0.0.1:8002',
      '/history': 'http://127.0.0.1:8002',
      '/stream': 'http://127.0.0.1:8002',
      '/upload': 'http://127.0.0.1:8000',
      '/status': 'http://127.0.0.1:8000',
      '/docs': 'http://127.0.0.1:8002',
      '/openapi.json': 'http://127.0.0.1:8002',
    },
  },
})
