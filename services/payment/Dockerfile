# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: runtime base moved from nodejs22-debian12 to nodejs22-debian13 to clear fixable libssl3 findings.
# Change: builder and runtime bases pinned by digest.
# Change: files from the build context copied with mode 644 rather than the checkout's mode.
# Change: the application directory is created as root and the runtime user is set numerically.
# Change: EXPOSE names port 8080; ${PAYMENT_PORT} is undefined when the image builds.

FROM docker.io/library/node:22.23.3-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392 AS builder

WORKDIR /usr/src/app/

COPY ./services/payment/package.json package.json
COPY ./services/payment/package-lock.json package-lock.json

RUN npm ci --omit=dev

# -----------------------------------------------------------------------------

FROM gcr.io/distroless/nodejs22-debian13:nonroot@sha256:ec2313763dd43931543bd03830466e0c409ce73a487e8d46f10db72d3b816c1c

USER 0:0

WORKDIR /usr/src/app/

COPY --from=builder /usr/src/app/node_modules/ node_modules/

COPY --chmod=644 ./pb/demo.proto demo.proto

COPY --chmod=644 ./services/payment/charge.js charge.js
COPY --chmod=644 ./services/payment/index.js index.js
COPY --chmod=644 ./services/payment/logger.js logger.js
COPY --chmod=644 ./services/payment/opentelemetry.js opentelemetry.js

USER 65532:65532

EXPOSE 8080

CMD ["--require=./opentelemetry.js", "index.js"]

# The runtime stage runs as root until its last USER because BuildKit creates WORKDIR as the active
# user and the base sets 65532; the runtime user can read, not rename or replace, /usr/src/app.
