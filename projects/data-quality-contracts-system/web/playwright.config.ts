import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, timeout: 30000,
  reporter: [['list'], ['json', {outputFile: '../docs/test-results/browser.json'}]],
  use: {baseURL: 'http://127.0.0.1:8083', trace: 'retain-on-failure'},
  projects: [{name: 'chromium', use: {...devices['Desktop Chrome'],viewport:{width:1440,height:1000}}}],
  webServer: {command: '../.venv/bin/python ../scripts/run.py --port 8083', url: 'http://127.0.0.1:8083/api/health', reuseExistingServer: false, timeout: 30000},
});
