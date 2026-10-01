# AI OS

## Responsibilities

- **n8n** is the executable workflow/process layer for orchestration, automation, integrations, triggers, and multi-step workflows.
- **Codex** is the implementation and coding layer.
- **GitHub** is source control for code, documentation, and exported workflow JSON.
- **Applications, services, and APIs** remain independent components. Normal application logic stays in application code, not n8n.

```text
User / App
  -> AI OS
    -> n8n
      -> APIs / Database / Payments / Email / AI services / GPU-LTX services
```

## Local operations

Run from this directory in PowerShell:

```powershell
.\scripts\n8n.ps1 start
.\scripts\n8n.ps1 stop
.\scripts\n8n.ps1 status
.\scripts\n8n.ps1 smoke
.\scripts\n8n.ps1 backup
.\scripts\n8n.ps1 restore -Path .\backups\n8n-YYYYMMDD-HHMMSS.zip
.\scripts\n8n.ps1 update
```

Open http://127.0.0.1:5678 and create the local owner account on first launch. Import tracked exports from `n8n/workflows/`. Before updating, review n8n release notes and breaking changes, then change the pinned image tag in `compose.yaml`; `update` backs up data and pulls that approved tag.

Runtime state and `.env` are local and ignored by Git. Workflow exports are tracked; export a workflow after every accepted UI change.

Upstream: https://github.com/n8n-io/n8n
