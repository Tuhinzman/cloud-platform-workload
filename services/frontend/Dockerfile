# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: runtime base moved from nodejs22-debian12 to nodejs22-debian13 to clear fixable libssl3 findings.
# Change: builder, dependency and runtime bases pinned by digest.
# Change: files from the build context copied with fixed modes rather than the checkout's modes.
# Change: the application directory is created as root and the runtime user is set numerically.
# Change: EXPOSE names port 8080; ${FRONTEND_PORT} is undefined when the image builds.

FROM docker.io/library/node:22.23.3-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392 AS builder

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

FROM docker.io/library/node:22.23.3-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392 AS deps

WORKDIR /app

COPY ./services/frontend/package.json package.json
COPY ./services/frontend/package-lock.json package-lock.json

RUN npm ci --omit=dev

# -----------------------------------------------------------------------------

FROM gcr.io/distroless/nodejs22-debian13:nonroot@sha256:ec2313763dd43931543bd03830466e0c409ce73a487e8d46f10db72d3b816c1c

USER 0:0

WORKDIR /app

COPY --from=builder /app/.next/standalone/ ./
COPY --from=builder /app/.next/static/ .next/static/

COPY --from=deps /app/node_modules/ node_modules/

COPY --chmod=u=rwX,go=rX ./services/frontend/public/ public/

COPY --chmod=644 ./services/frontend/utils/telemetry/Instrumentation.js Instrumentation.js

USER 65532:65532

EXPOSE 8080

CMD ["--require=./Instrumentation.js", "server.js"]

# The runtime stage runs as root until its last USER because BuildKit creates WORKDIR as the active
# user and the base sets 65532; the runtime user can read, not rename or replace, /app.
