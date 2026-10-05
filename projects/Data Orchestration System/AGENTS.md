# Data Orchestration Lab

This independent project is named `data-orchestration-lab`. The existing
`Data Orchestration System` directory is its root. Follow parent AI-OS guidance.
Read `docs/architecture.md` and `docs/acceptance.md` before changing contracts.

- The pure TypeScript simulator owns execution truth. No AI, real time, randomness,
  sibling imports, SQL transformations, scoring, or monitoring services in the engine.
- Keep partition dates separate from execution timestamps. All virtual times use
  the declared schedule timezone, Asia/Seoul by default.
- Preserve the eight task states, explicit retry eligibility, global worker limits,
  stable topological ordering, and runtime input validation.
- Exactly one independent Orchestration Verification Agent challenges the first slice.
  It may inspect, run checks, and save its own probes/evidence. It must not edit
  implementation, product tests, or approved contracts. Reuse it for reverification.
- Required checks: `npm test`, `npm run build`, `npm run test:e2e` (`npm run check`).
  Install with `npm ci`; browser checks need `npx playwright install chromium`.
- Start the production build with `npm start` (loopback, port 8078). `npm run dev`
  starts the development server on the same port. No external account is required.
