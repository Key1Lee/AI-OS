import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const projectRoot = fileURLToPath(new URL('../..', import.meta.url));
export default defineConfig({
  testDir: './e2e', timeout: 30000, fullyParallel: false, workers: 1,
  reporter: [['list']],
  use: { baseURL:'http://127.0.0.1:8076', viewport:{width:1440,height:1000}, trace:'retain-on-failure', screenshot:'only-on-failure' },
  webServer: { command:'uv run python scripts/run.py --port 8076', cwd:projectRoot, url:'http://127.0.0.1:8076/api/health', reuseExistingServer:false, timeout:30000 },
});
