import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
/**
 * The SPA build that ships to Cloudflare Pages.
 *
 * `public/_redirects` carries the `/* /index.html 200` fallback, because this is
 * a client-routed app: a deep link like `/intelligence` has no file behind it on
 * the CDN and would 404 without it.
 */
export default defineConfig({
    plugins: [react(), tailwindcss()],
    server: {
        port: 5173,
        strictPort: true,
    },
    build: {
        // Charts and the React runtime change at different rates from the product
        // code, so they are split out and cached independently of it. The warning
        // threshold is left at its default; this only stops one 1 MB file.
        rollupOptions: {
            output: {
                manualChunks: {
                    react: ['react', 'react-dom', 'react-router-dom'],
                    charts: ['recharts'],
                    icons: ['lucide-react'],
                },
            },
        },
    },
});
