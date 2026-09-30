# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: the agent version carries a default. Upstream supplies it from a .env file this
# repository does not carry, so without one the download URL loses its version and 404s.
# 2.26.1 is the first release that fixes CVE-2026-33701, a CRITICAL the image scan reported
# against 2.23.0.
# Change: gradle.lockfile is copied with the build files, because the build locks its
# dependencies strictly and downloadRepos resolves them before the rest of the source arrives.
# Change: build/outputLocation, the jar copy downloadRepos makes, is deleted before the runtime
# stage copies the application directory; the start script loads only the installed lib/.
# Change: the OpenSSL packages are pinned to the fixed revision 3.5.5-1ubuntu3.6, which the
# newest eclipse-temurin:21-jre digest does not yet carry.

FROM --platform=${BUILDPLATFORM} eclipse-temurin:21-jdk AS builder
ARG _JAVA_OPTIONS
WORKDIR /usr/src/app/

COPY ./services/ad/gradlew* ./services/ad/settings.gradle* ./services/ad/build.gradle ./services/ad/gradle.lockfile ./
COPY ./services/ad/gradle ./gradle

RUN chmod +x ./gradlew
RUN ./gradlew
RUN ./gradlew downloadRepos

COPY ./services/ad/ ./
COPY ./pb/ ./proto
RUN chmod +x ./gradlew
RUN ./gradlew installDist -PprotoSourceDir=./proto
RUN rm -rf build/outputLocation

# -----------------------------------------------------------------------------

FROM eclipse-temurin:21-jre

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libssl3t64=3.5.5-1ubuntu3.6 \
        openssl=3.5.5-1ubuntu3.6 \
        openssl-provider-legacy=3.5.5-1ubuntu3.6 \
    && rm -rf /var/lib/apt/lists/*

ARG OTEL_JAVA_AGENT_VERSION=2.26.1
ARG _JAVA_OPTIONS

WORKDIR /usr/src/app/

COPY --from=builder /usr/src/app/ ./
ADD --chmod=644 https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v$OTEL_JAVA_AGENT_VERSION/opentelemetry-javaagent.jar /usr/src/app/opentelemetry-javaagent.jar
ENV JAVA_TOOL_OPTIONS=-javaagent:/usr/src/app/opentelemetry-javaagent.jar

EXPOSE ${AD_PORT}
ENTRYPOINT [ "./build/install/opentelemetry-demo-ad/bin/Ad" ]
