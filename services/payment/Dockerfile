# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. Application files and dependencies given explicit ownership by the unprivileged runtime user.
# Change: runtime base moved from nodejs22-debian12 to nodejs22-debian13. Measured, not
# preferred: the debian12 base ships libssl3 3.0.18-1~deb12u2, which carries one CRITICAL and
# five HIGH with fixes published, and the newest published debian12 tag still does. Distroless
# has no package manager, so the pinned-package remedy the quote image uses cannot apply here
# and the base was moved. The node runtime moves
# v22.22.0 to v22.23.2, a patch within the same major, and shipping already runs a debian13
# distroless base, so this follows an existing choice rather than introducing one.
# Change: libssl3t64 3.5.7-1~deb13u3, Debian's fix for DSA-6531-1, is installed over the distroless
# base, which still ships deb13u2, and the base is pinned by digest.

FROM docker.io/library/node:22-slim AS builder

WORKDIR /usr/src/app/

COPY ./services/payment/package.json package.json
COPY ./services/payment/package-lock.json package-lock.json

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

WORKDIR /usr/src/app/

COPY --chown=65532:65532 --from=builder /usr/src/app/node_modules/ node_modules/

COPY --chown=65532:65532 ./pb/demo.proto demo.proto

COPY ./services/payment/charge.js charge.js
COPY ./services/payment/index.js index.js
COPY ./services/payment/logger.js logger.js
COPY ./services/payment/opentelemetry.js opentelemetry.js

EXPOSE ${PAYMENT_PORT}

CMD ["--require=./opentelemetry.js", "index.js"]
