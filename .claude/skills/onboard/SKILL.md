---
name: onboard
description: Establish confirmed AI-OS or project operating context when starting or refreshing an installation, workspace, or project.
---

# Onboard

Input: the scope to initialize or refresh, plus whatever facts the user already supplied. Inspect existing context and configuration before asking for missing essentials. Ask only for facts needed to identify the scope, purpose, important sources, and current priorities. Keep global context separate from project context. Never solicit or store credentials.

Present a compact proposed record, distinguish confirmed facts from assumptions, and ask for confirmation before durable writes. Save only confirmed facts through the application-owned context store; merge without erasing unrelated fields. If a valid record already exists, report it and ask only about gaps or changes. Provider setup is a separate operation unless explicitly requested.

Output: the confirmed context location, changed fields, unresolved questions, and next useful action. Stop when the user pauses. If a source conflicts or persistence fails, report the conflict or failure and do not claim completion. See [context storage](references/context-storage.md) only when saving or migrating durable context.
