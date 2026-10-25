import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react()],
    server: {
      port: Number(env.FRONTEND_PORT || 5173),
      strictPort: true,
      proxy: { '/api': { target: env.BACKEND_PROXY_URL || 'http://127.0.0.1:3000', changeOrigin: false } },
    },
  };
});
