---
name: 3d-brain
description: Build or refresh an optional local 3D view of approved AI-OS knowledge sources when the user asks to explore saved knowledge visually.
---

# 3D brain

Input: approved source routes, optional project scope, and a destination for the local view. Read the source registry and the [viewer guide](references/viewer.md) only when building or updating a view. Ask which sources may be displayed if approval is unclear. Generate a graph of route relationships, not a copy of source bodies.

Output: a local visualization artifact with clickable source routes, the included and skipped sources, and the generation time. Keep it optional and outside Core runtime decisions. Never treat the visualization as authoritative knowledge, expose private content by default, or connect to external services without authorization. If no approved sources resolve, explain the gap rather than inventing nodes.
