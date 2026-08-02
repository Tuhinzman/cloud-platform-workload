# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. Application files and dependencies given explicit ownership by the unprivileged runtime user.

FROM docker.io/library/node:22-slim AS builder

WORKDIR /usr/src/app/

COPY ./services/payment/package.json package.json
COPY ./services/payment/package-lock.json package-lock.json

RUN npm ci --omit=dev

# -----------------------------------------------------------------------------

FROM gcr.io/distroless/nodejs22-debian12:nonroot

WORKDIR /usr/src/app/

COPY --chown=65532:65532 --from=builder /usr/src/app/node_modules/ node_modules/

COPY --chown=65532:65532 ./pb/demo.proto demo.proto

COPY ./services/payment/charge.js charge.js
COPY ./services/payment/index.js index.js
COPY ./services/payment/logger.js logger.js
COPY ./services/payment/opentelemetry.js opentelemetry.js

EXPOSE ${PAYMENT_PORT}

CMD ["--require=./opentelemetry.js", "index.js"]
