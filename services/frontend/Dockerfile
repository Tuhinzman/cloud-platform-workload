# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: runtime base debian12 -> debian13. debian12 ships libssl3 with fixed HIGH/CRITICAL
# CVEs and distroless has no package manager, so the base is the only place to clear them.

FROM docker.io/library/node:22-slim AS builder

WORKDIR /app

COPY ./services/frontend/package.json package.json
COPY ./services/frontend/package-lock.json package-lock.json

RUN npm ci

COPY ./services/frontend/components/ components/
COPY ./services/frontend/gateways/ gateways/
COPY ./services/frontend/pages/ pages/
COPY ./services/frontend/protos/ protos/
COPY ./services/frontend/providers/ providers/
COPY ./services/frontend/services/ services/
COPY ./services/frontend/styles/ styles/
COPY ./services/frontend/types/ types/

COPY ./services/frontend/utils/enums/ utils/enums/
COPY ./services/frontend/utils/telemetry/ utils/telemetry/
COPY ./services/frontend/utils/imageLoader.js utils/imageLoader.js
COPY ./services/frontend/utils/Request.ts utils/Request.ts

COPY ./services/frontend/next.config.js next.config.js
COPY ./services/frontend/tsconfig.json tsconfig.json

RUN npm run build

# -----------------------------------------------------------------------------

FROM docker.io/library/node:22-slim AS deps

WORKDIR /app

COPY ./services/frontend/package.json package.json
COPY ./services/frontend/package-lock.json package-lock.json

RUN npm ci --omit=dev

# -----------------------------------------------------------------------------

FROM gcr.io/distroless/nodejs22-debian13:nonroot

WORKDIR /app

COPY --from=builder /app/.next/standalone/ ./
COPY --from=builder /app/.next/static/ .next/static/

COPY --from=deps /app/node_modules/ node_modules/

COPY ./services/frontend/public/ public/

COPY ./services/frontend/utils/telemetry/Instrumentation.js Instrumentation.js

EXPOSE ${FRONTEND_PORT}

CMD ["--require=./Instrumentation.js", "server.js"]
