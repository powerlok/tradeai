import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8001';
    return {
        plugins: [react()],
        server: {
            host: '0.0.0.0',
            port: 4173,
            proxy: {
                '/api': {
                    target: apiProxyTarget,
                    changeOrigin: true,
                    ws: true,
                },
            },
        },
        preview: {
            host: '0.0.0.0',
            port: 4173,
        },
    };
});
