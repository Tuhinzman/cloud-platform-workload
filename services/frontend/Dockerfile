# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: runtime base debian12 -> debian13. debian12 ships libssl3 with fixed HIGH/CRITICAL
# CVEs and distroless has no package manager, so the base was moved.
# Change: libssl3t64 3.5.7-1~deb13u3, Debian's fix for DSA-6531-1, is installed over the distroless
# base, which still ships deb13u2, and the base is pinned by digest.

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

# libssl3t64 3.5.7-1~deb13u3 fixes DSA-6531-1, which no distroless build carries yet. It is installed
# the way the base installs every package: the .deb's files, plus its control and md5sums as the
# status.d entries the scanner reads. The build fails once the base itself reaches this version.
FROM docker.io/library/debian:trixie-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a AS libssl3t64
ARG TARGETARCH
ADD https://snapshot.debian.org/archive/debian-security/20260930T060347Z/pool/updates/main/o/openssl/libssl3t64_3.5.7-1~deb13u3_amd64.deb /debs/amd64.deb
ADD https://snapshot.debian.org/archive/debian-security/20260930T060347Z/pool/updates/main/o/openssl/libssl3t64_3.5.7-1~deb13u3_arm64.deb /debs/arm64.deb
COPY --from=gcr.io/distroless/nodejs22-debian13:nonroot@sha256:5ef534d3db0ac0c43bee379af4ae49cfbfc0ef38a46c94c52d87c68f32f34d8a /var/lib/dpkg/status.d/libssl3t64 /base-status
RUN printf '%s  %s\n' \
        ff16bc048bcd7d1b256094450b79c77947d8e76fe2a24bd99b91021d591fa074 /debs/amd64.deb \
        d0681293a160392186c6ef85a165e40603d1628a099936137d24d391bd591f97 /debs/arm64.deb \
        > /debs/SHA256SUMS && \
    sha256sum -c /debs/SHA256SUMS && \
    base="$(sed -n 's/^Version: //p' /base-status)" && \
    if dpkg --compare-versions "$base" ge 3.5.7-1~deb13u3; then echo "base has libssl3t64 $base: remove this stage"; exit 1; fi && \
    dpkg-deb -x "/debs/$TARGETARCH.deb" /pkg && \
    dpkg-deb -e "/debs/$TARGETARCH.deb" /ctrl && \
    mkdir -p /pkg/var/lib/dpkg/status.d && \
    cp /ctrl/control /pkg/var/lib/dpkg/status.d/libssl3t64 && \
    cp /ctrl/md5sums /pkg/var/lib/dpkg/status.d/libssl3t64.md5sums

FROM gcr.io/distroless/nodejs22-debian13:nonroot@sha256:5ef534d3db0ac0c43bee379af4ae49cfbfc0ef38a46c94c52d87c68f32f34d8a

COPY --from=libssl3t64 /pkg/ /

WORKDIR /app

COPY --from=builder /app/.next/standalone/ ./
COPY --from=builder /app/.next/static/ .next/static/

COPY --from=deps /app/node_modules/ node_modules/

COPY ./services/frontend/public/ public/

COPY ./services/frontend/utils/telemetry/Instrumentation.js Instrumentation.js

EXPOSE ${FRONTEND_PORT}

CMD ["--require=./Instrumentation.js", "server.js"]
