# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: the agent version carries a default. Upstream supplies it from a .env file this
# repository does not carry, so without one the download URL loses its version and 404s.
# 2.26.1 is the first release that fixes CVE-2026-33701, a CRITICAL the image scan reported
# against 2.23.0.
# Change: runtime base moved from java17-debian12 to java17-debian13. Measured, not preferred:
# the newest java17-debian12 digest still ships openjdk-17 17.0.18 and pcre2, expat and lcms2
# revisions with nine fixable HIGH findings, and distroless has no package manager to upgrade
# them in place. The debian13 base carries Temurin 17.0.20 and no fixable HIGH or CRITICAL
# finding; the Java major is unchanged.
# Change: builder and runtime bases pinned by digest.
# Change: the agent download is verified against the release's sha256.
# Change: /usr/src/app created owned by root, so the runtime user cannot replace the jars in it.

FROM --platform=${BUILDPLATFORM} gradle:8.14.6-jdk17@sha256:f03084035115370914672b6964aadf0d516a4a452f7ef236dc80a43db4dd4789 AS builder

WORKDIR /usr/src/app/

COPY ./services/fraud-detection/ ./
COPY ./pb/ ./src/main/proto/

RUN gradle shadowJar

# -----------------------------------------------------------------------------

FROM gcr.io/distroless/java17-debian13:nonroot@sha256:b318d135426b282db46c3e2601edeb41eb7b157d9ab75d2f9499743180cddf0e

ARG OTEL_JAVA_AGENT_VERSION=2.26.1
USER 0:0
WORKDIR /usr/src/app/

ADD --checksum=sha256:cc4af5966ab72109cacc962ba3b9f99b3e88caf064c3144a451bcfe0f4950f19 --chmod=644 https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v$OTEL_JAVA_AGENT_VERSION/opentelemetry-javaagent.jar /usr/src/app/opentelemetry-javaagent.jar
ENV JAVA_TOOL_OPTIONS=-javaagent:/usr/src/app/opentelemetry-javaagent.jar

COPY --from=builder /usr/src/app/build/libs/fraud-detection-1.0-all.jar fraud-detection-1.0-all.jar

USER 65532:65532

ENTRYPOINT [ "java", "-jar", "fraud-detection-1.0-all.jar" ]

# WORKDIR creates its directory as the current user, and the nonroot base sets 65532, so root creates it here.
# The checksum is the 2.26.1 agent's; another OTEL_JAVA_AGENT_VERSION fails the build until the checksum changes with it.
