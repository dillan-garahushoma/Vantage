// Temporary, session-only config — NOT part of the project. It exists so this
// session's preview browser (which blocks cross-origin requests) can render the
// real app against the running backend: the dev server answers /api itself and
// forwards it to the API on :8000.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    port: 4173,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
})
