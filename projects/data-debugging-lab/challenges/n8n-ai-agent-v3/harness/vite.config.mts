import { defineConfig } from 'vitest/config';
import upstream from '../source/n8n/packages/@n8n/nodes-langchain/vite.config';

export default defineConfig({
  ...upstream,
  root: '/lab',
  test: {
    ...upstream.test,
    include: ['harness/business.test.ts'],
    setupFiles: ['/lab/source/n8n/packages/@n8n/nodes-langchain/test/setup.ts'],
    maxWorkers: 1,
    testTimeout: 60000,
    outputFile: { junit: process.env.LAB_ARTIFACT_DIR + '/junit.xml' },
  },
});
