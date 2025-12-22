// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000", // backend FastAPI của bạn
        changeOrigin: true,
      },
    },
  },
  build: {
    // Tắt sourcemap để ẩn source code gốc
    sourcemap: false,

    // Minify code để khó đọc hơn
    minify: 'terser',

    terserOptions: {
      compress: {
        // Xóa console.log trong production
        drop_console: true,
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info', 'console.debug']
      },
      mangle: {
        // Đổi tên biến thành tên ngắn khó hiểu (a, b, c...)
        toplevel: true
      },
      format: {
        // Xóa comments
        comments: false
      }
    } as any,

    // Tách code thành nhiều chunk nhỏ để khó theo dõi
    rollupOptions: {
      output: {
        manualChunks: undefined,
        // Đổi tên file output
        chunkFileNames: 'assets/[hash].js',
        entryFileNames: 'assets/[hash].js',
        assetFileNames: 'assets/[hash].[ext]'
      }
    }
  }
});
