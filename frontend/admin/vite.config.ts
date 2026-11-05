import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    // 线上挂在 /admin/；开发也可直接打开 http://localhost:5174/admin/
    base: env.VITE_BASE || '/admin/',
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
  }
})
