import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    proxy: {
      "/voice": {
        target: "http://127.0.0.1:8020",
        changeOrigin: true,
        ws: true,
      },
      "/chat": { target: "http://127.0.0.1:8020", changeOrigin: true },
      "/eligibility": { target: "http://127.0.0.1:8020", changeOrigin: true },
      "/approval": { target: "http://127.0.0.1:8020", changeOrigin: true },
      "/execution": { target: "http://127.0.0.1:8020", changeOrigin: true },
      "/confirmation": { target: "http://127.0.0.1:8020", changeOrigin: true },
      "/internal": { target: "http://127.0.0.1:8020", changeOrigin: true },
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: './index.html',
        internal: './internal.html',
      },
    },
  },
})
