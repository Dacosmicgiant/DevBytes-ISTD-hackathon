import { defineConfig } from 'vite';
import react from '@vitro/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/socket.io': {
        target: 'http://localhost:5000',
        ws: true
      },
      '/api': {
        target: 'http://localhost:5000'
      }
    }
  }
});