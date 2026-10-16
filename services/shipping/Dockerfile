# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: the builder pinned by digest to rust:1.91.1, the image the 1.91 tag resolved to. The runtime pinned to the
# newest distroless cc-debian13 digest, which carries libssl3t64 3.5.7-1~deb13u3 itself, so the stage that installed
# it over the older base is removed.
# Change: an amd64 target built on an arm64 host is cross-compiled, as an arm64 target on an amd64 host already was;
# before, that build put an arm64 binary into the amd64 image.
# Change: every cargo build passes --locked, so a stale Cargo.lock fails the build instead of being re-resolved.
# Change: /app is created by root; the runtime user is set numerically to 65532:65532 and cannot replace the binary.
# Change: EXPOSE names port 8080; ${SHIPPING_PORT} is undefined when the image builds.

FROM --platform=${BUILDPLATFORM} docker.io/library/rust:1.91.1@sha256:867f1d1162913c401378a8504fb17fe2032c760dc316448766f150a130204aad AS builder
ARG TARGETARCH
ARG TARGETPLATFORM
ARG BUILDPLATFORM

RUN echo Building on ${BUILDPLATFORM} for ${TARGETPLATFORM}

# Install dependencies - cross-compilation setup when the target differs from the build host, native otherwise
RUN apt-get update && \
    if [ "${TARGETPLATFORM}" = "linux/arm64" ] && [ "${BUILDPLATFORM}" != "linux/arm64" ] ; then \
        apt-get install --no-install-recommends -y g++-aarch64-linux-gnu libc6-dev-arm64-cross libprotobuf-dev protobuf-compiler ca-certificates && \
        rustup target add aarch64-unknown-linux-gnu; \
    elif [ "${TARGETPLATFORM}" = "linux/amd64" ] && [ "${BUILDPLATFORM}" != "linux/amd64" ] ; then \
        apt-get install --no-install-recommends -y g++-x86-64-linux-gnu libc6-dev-amd64-cross libprotobuf-dev protobuf-compiler ca-certificates && \
        rustup target add x86_64-unknown-linux-gnu; \
    else \
        apt-get install --no-install-recommends -y g++ libc6-dev libprotobuf-dev protobuf-compiler ca-certificates; \
    fi

WORKDIR /app/

COPY /services/shipping/ /app/

# Build - cross-compile when the target differs from the build host, native otherwise
RUN if [ "${TARGETPLATFORM}" = "linux/arm64" ] && [ "${BUILDPLATFORM}" != "linux/arm64" ] ; then \
        env CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc \
            CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc \
            CXX_aarch64_unknown_linux_gnu=aarch64-linux-gnu-g++ \
        cargo build -r --locked --target aarch64-unknown-linux-gnu && \
        cp /app/target/aarch64-unknown-linux-gnu/release/shipping /app/target/release/shipping; \
    elif [ "${TARGETPLATFORM}" = "linux/amd64" ] && [ "${BUILDPLATFORM}" != "linux/amd64" ] ; then \
        env CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER=x86_64-linux-gnu-gcc \
            CC_x86_64_unknown_linux_gnu=x86_64-linux-gnu-gcc \
            CXX_x86_64_unknown_linux_gnu=x86_64-linux-gnu-g++ \
        cargo build -r --locked --target x86_64-unknown-linux-gnu && \
        cp /app/target/x86_64-unknown-linux-gnu/release/shipping /app/target/release/shipping; \
    else \
        cargo build -r --locked; \
    fi

FROM gcr.io/distroless/cc-debian13:nonroot@sha256:e792ab3d241a468a4fd7519ddbbebe66b49b5f365771716ea688ad40b6c6f1c2

USER 0:0
WORKDIR /app

COPY --from=builder /app/target/release/shipping shipping

USER 65532:65532

EXPOSE 8080

CMD ["./shipping"]

# WORKDIR creates its directory as the current user, and the nonroot base sets 65532, so root creates it here.
