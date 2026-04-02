import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        // Use IPv4 so dev proxy hits this app's FastAPI when Docker also binds :8000 via IPv6.
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
