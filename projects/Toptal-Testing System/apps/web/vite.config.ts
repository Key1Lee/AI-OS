import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import {fileURLToPath} from 'node:url';
const observabilityUi=fileURLToPath(new URL('../../../Data Observability System/web/src/index.ts',import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve:{alias:{'@data-observability/ui':observabilityUi,'@data-observability/styles':fileURLToPath(new URL('../../../Data Observability System/web/src/foundation.css',import.meta.url))},dedupe:['react','react-dom']},
  server: { fs:{allow:['../..','../../../Data Observability System']}, proxy: { '/api': 'http://127.0.0.1:8001' } },
  build: { target: 'es2022' },
});
