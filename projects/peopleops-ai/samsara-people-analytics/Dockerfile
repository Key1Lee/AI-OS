FROM node:24-bookworm-slim AS build
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM node:24-bookworm-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 DEMO_ROOT=/app
WORKDIR /app/web
COPY --from=build /app/web ./
COPY fixtures /app/fixtures
COPY knowledge /app/knowledge
USER node
EXPOSE 3000
CMD ["npm", "start"]
