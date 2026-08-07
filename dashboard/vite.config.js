import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/analyze-yahoo': 'http://localhost:5050',
      '/trade-action':  'http://localhost:5050',
      '/analyze':       'http://localhost:5050',
      '/health':        'http://localhost:5050',
    },
  },
})
