---
name: link
description: Register a project, local source, or external source for later discovery when the user wants AI-OS to find it without copying its contents.
---

# Link

Input: the target and its intended use. Determine whether the route belongs to global AI-OS or a specific project. Ask only if the target, scope, or intended use cannot be inferred. Inspect existing routes to avoid duplicates and preserve the authoritative source.

For a local path, resolve and verify it. For an external source, record its URL and access mechanism, but mark live access unverified unless a narrow authorized read succeeds. Register the smallest useful route using [the source registry](references/registry.md); do not ingest whole files or copy source content. Record authority, freshness expectation, and last verification separately.

Output: the registry location, route ID, target, verification result, and any access gap. Fail on a missing local target or conflicting route ID. Do not store credentials or broaden tool access.
