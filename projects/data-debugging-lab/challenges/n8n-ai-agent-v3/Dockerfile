FROM node:22.22.0-bookworm-slim@sha256:dd9d21971ec4395903fa6143c2b9267d048ae01ca6d3ea96f16cb30df6187d94
RUN corepack enable && corepack prepare pnpm@10.32.1 --activate
ENV CI=true DO_NOT_TRACK=1 TURBO_TELEMETRY_DISABLED=1 N8N_DIAGNOSTICS_ENABLED=false
WORKDIR /lab/source/n8n
