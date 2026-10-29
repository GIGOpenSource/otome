import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  base: process.env.VITE_BASE || '/',
  build: {
    sourcemap: true,
  },
  server: {
    port: 5174,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8001', changeOrigin: true, secure: false },
      '/media': { target: 'http://127.0.0.1:8001', changeOrigin: true, secure: false },
      '/go': { target: 'http://127.0.0.1:8001', changeOrigin: true, secure: false },
      '/land': { target: 'http://127.0.0.1:8001', changeOrigin: true, secure: false },
    },
  },
  plugins: [vue()],
})
