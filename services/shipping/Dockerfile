# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: libssl3t64 3.5.7-1~deb13u3, Debian's fix for DSA-6531-1, is installed over the distroless
# base, which still ships deb13u2, and the base is pinned by digest.

FROM --platform=${BUILDPLATFORM} docker.io/library/rust:1.91 AS builder
ARG TARGETARCH
ARG TARGETPLATFORM
ARG BUILDPLATFORM

RUN echo Building on ${BUILDPLATFORM} for ${TARGETPLATFORM}

# Install dependencies - cross-compilation setup for ARM64, native otherwise
RUN apt-get update && \
    if [ "${TARGETPLATFORM}" = "linux/arm64" ] && [ "${BUILDPLATFORM}" != "linux/arm64" ] ; then \
        apt-get install --no-install-recommends -y g++-aarch64-linux-gnu libc6-dev-arm64-cross libprotobuf-dev protobuf-compiler ca-certificates && \
        rustup target add aarch64-unknown-linux-gnu; \
    else \
        apt-get install --no-install-recommends -y g++ libc6-dev libprotobuf-dev protobuf-compiler ca-certificates; \
    fi

WORKDIR /app/

COPY /services/shipping/ /app/

# Build - cross-compile for ARM64 or native build
RUN if [ "${TARGETPLATFORM}" = "linux/arm64" ] && [ "${BUILDPLATFORM}" != "linux/arm64" ] ; then \
        env CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc \
            CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc \
            CXX_aarch64_unknown_linux_gnu=aarch64-linux-gnu-g++ \
        cargo build -r --target aarch64-unknown-linux-gnu && \
        cp /app/target/aarch64-unknown-linux-gnu/release/shipping /app/target/release/shipping; \
    else \
        cargo build -r; \
    fi


# libssl3t64 3.5.7-1~deb13u3 fixes DSA-6531-1, which no distroless build carries yet. It is installed
# the way the base installs every package: the .deb's files, plus its control and md5sums as the
# status.d entries the scanner reads. The build fails once the base itself reaches this version.
FROM docker.io/library/debian:trixie-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a AS libssl3t64
ARG TARGETARCH
ADD https://snapshot.debian.org/archive/debian-security/20260930T060347Z/pool/updates/main/o/openssl/libssl3t64_3.5.7-1~deb13u3_amd64.deb /debs/amd64.deb
ADD https://snapshot.debian.org/archive/debian-security/20260930T060347Z/pool/updates/main/o/openssl/libssl3t64_3.5.7-1~deb13u3_arm64.deb /debs/arm64.deb
COPY --from=gcr.io/distroless/cc-debian13:nonroot@sha256:54df941ed0d06a1bd95ef5e0ce391fd8d9f94b64782dc9a60062727849ee3f97 /var/lib/dpkg/status.d/libssl3t64 /base-status
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

FROM gcr.io/distroless/cc-debian13:nonroot@sha256:54df941ed0d06a1bd95ef5e0ce391fd8d9f94b64782dc9a60062727849ee3f97

COPY --from=libssl3t64 /pkg/ /

WORKDIR /app

COPY --from=builder /app/target/release/shipping shipping

EXPOSE ${SHIPPING_PORT}

CMD ["./shipping"]
