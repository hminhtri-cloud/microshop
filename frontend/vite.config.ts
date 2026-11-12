import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const proxy = {
  '/api/internal': {
    target: 'http://127.0.0.1:8001',
    bypass: (): false => false,
  },
  '/api/admin/orders': {
    target: process.env.ORDER_API_TARGET || 'http://127.0.0.1:8004',
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
  '/api/seller/orders': {
    target: process.env.ORDER_API_TARGET || 'http://127.0.0.1:8004',
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
  '/api/orders': {
    target: process.env.ORDER_API_TARGET || 'http://127.0.0.1:8004',
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
  '/api/admin/products': {
    target: process.env.PRODUCT_API_TARGET || 'http://127.0.0.1:8002',
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
  '/api/seller/products': {
    target: process.env.PRODUCT_API_TARGET || 'http://127.0.0.1:8002',
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
  '/api/products': {
    target: process.env.PRODUCT_API_TARGET || 'http://127.0.0.1:8002',
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
  '/api': {
    target: process.env.AUTH_API_TARGET || 'http://127.0.0.1:8001',
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
};

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, proxy },
  preview: { port: 4173, strictPort: true, proxy },
});
