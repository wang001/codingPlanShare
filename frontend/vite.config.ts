import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
        secure: false
      }
      // /api/admin 已被上面的 /api 代理覆盖，无需单独配置
      // 前端路由 /admin/* 不再与后端冲突
    }
  }
})
