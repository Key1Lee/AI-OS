---
name: audit
description: Audit AI-OS architecture, Skills, instructions, workflow boundaries, routing, and runtime controls for evidence-backed drift or unnecessary complexity.
---

# Audit

Input: an AI-OS architecture scope or suspected drift. Audit the system that governs changes; Review evaluates a particular completed change. Start with `AGENTS.md`, `architecture/skills.md`, the relevant architecture contract, and the canonical Skill catalog. Inspect only the affected sources and generated copies. Compare intended with actual behavior before treating a difference as a problem. Run the [deterministic checks](references/checks.md) when tools are available; otherwise state which checks could not run. If only checker JSON is available, report a **bounded conformance check**, not an AI-OS architecture verdict or a clean bill of health. A model-only summary cannot establish repository-wide conformance.

Select relevant dimensions: Skill inventory and trigger overlap; instruction conflicts, stale workarounds, and context cost; Plan/Implement/Test/Debug/Verify/Review ownership; routing eval coverage; canonical/generated agreement; configuration, provider, permission, and completion boundaries; and access to needed tests, traces, or state. Use models for architectural judgment and existing deterministic checks for mechanical facts. Preserve intentional differences and avoid broad redesign without evidence.

Classify each architectural candidate as **confirmed problem** (demonstrated contract violation), **likely risk** (material but not conclusive), **optimization** (supported optional simplification), or **speculative concern** (insufficient evidence). A suspicion without comparative evidence stays speculative; accurate repetition without demonstrated harm is at most an optimization. Preserve the checker's own classifications: a verification gap is not a defect, and an intentional difference is not automatically a finding. For material findings give component, source or check evidence, relevant contract, consequence, required or optional status, and correction direction. A bounded clean result is valid; do not infer that unchecked project workflows or cloud providers passed. Copy checker IDs exactly, preserve its coverage limits, and do not relabel a passed check as a finding.

Report scope, evidence inspected, checks and skips, material findings, coverage limits, and bounded handoffs. Route architectural decisions to Plan, straightforward authorized corrections to Implementation, unexplained behavior to Debug, corrections needing proof to Verify, and completed-change risk to Review. Audit reports by default; it does not silently repair code, change permissions, invoke paid providers, or save a dated report without a request or applicable policy.
