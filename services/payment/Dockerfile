# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. Application files and dependencies given explicit ownership by the unprivileged runtime user.
# Change: runtime base moved from nodejs22-debian12 to nodejs22-debian13. Measured, not
# preferred: the debian12 base ships libssl3 3.0.18-1~deb12u2, which carries one CRITICAL and
# five HIGH with fixes published, and the newest published debian12 tag still does. Distroless
# has no package manager, so the pinned-package remedy the quote image uses cannot apply here
# and the base itself is the only place the finding can be cleared. The node runtime moves
# v22.22.0 to v22.23.2, a patch within the same major, and shipping already runs a debian13
# distroless base, so this follows an existing choice rather than introducing one.

FROM docker.io/library/node:22-slim AS builder

WORKDIR /usr/src/app/

COPY ./services/payment/package.json package.json
COPY ./services/payment/package-lock.json package-lock.json

RUN npm ci --omit=dev

# -----------------------------------------------------------------------------

FROM gcr.io/distroless/nodejs22-debian13:nonroot

WORKDIR /usr/src/app/

COPY --chown=65532:65532 --from=builder /usr/src/app/node_modules/ node_modules/

COPY --chown=65532:65532 ./pb/demo.proto demo.proto

COPY ./services/payment/charge.js charge.js
COPY ./services/payment/index.js index.js
COPY ./services/payment/logger.js logger.js
COPY ./services/payment/opentelemetry.js opentelemetry.js

EXPOSE ${PAYMENT_PORT}

CMD ["--require=./opentelemetry.js", "index.js"]
