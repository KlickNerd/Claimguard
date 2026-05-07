# syntax=docker/dockerfile:1.6
#
# ClaimGuard Web container.
#
# Multi-stage build:
#   1. ``builder`` runs pnpm install + next build to produce a
#      ``.next/standalone`` self-contained server.
#   2. ``runner`` is a slim node-alpine image that only carries the
#      built artefacts - no dev deps, no source maps.
#
# NEXT_PUBLIC_API_URL is baked at build time because Next ships those
# values into the client bundle. We pass it via --build-arg from
# docker-compose.

FROM node:22-alpine AS builder

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /repo

# Workspace metadata first so npm cache layers properly.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/web/package.json apps/web/

RUN pnpm install --frozen-lockfile --filter @claimguard/web...

# Copy the rest of the web app and build it.
COPY apps/web ./apps/web

ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /repo/apps/web
RUN pnpm exec next build


FROM node:22-alpine AS runner

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

# Standalone output already contains a minimal node_modules.
COPY --from=builder /repo/apps/web/.next/standalone/apps/web ./
COPY --from=builder /repo/apps/web/.next/standalone/node_modules ./node_modules
COPY --from=builder /repo/apps/web/.next/static ./.next/static
COPY --from=builder /repo/apps/web/public ./public

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:3000/app || exit 1

CMD ["node", "server.js"]
