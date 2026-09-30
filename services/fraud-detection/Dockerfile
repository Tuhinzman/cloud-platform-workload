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

FROM --platform=${BUILDPLATFORM} gradle:8-jdk17 AS builder

WORKDIR /usr/src/app/

COPY ./services/fraud-detection/ ./
COPY ./pb/ ./src/main/proto/

RUN gradle shadowJar

# -----------------------------------------------------------------------------

FROM gcr.io/distroless/java17-debian13:nonroot

ARG OTEL_JAVA_AGENT_VERSION=2.26.1
WORKDIR /usr/src/app/

ADD --chmod=644 https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v$OTEL_JAVA_AGENT_VERSION/opentelemetry-javaagent.jar /usr/src/app/opentelemetry-javaagent.jar
ENV JAVA_TOOL_OPTIONS=-javaagent:/usr/src/app/opentelemetry-javaagent.jar

COPY --from=builder /usr/src/app/build/libs/fraud-detection-1.0-all.jar fraud-detection-1.0-all.jar

ENTRYPOINT [ "java", "-jar", "fraud-detection-1.0-all.jar" ]
