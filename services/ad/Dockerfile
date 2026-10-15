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
# Change: builder and runtime bases pinned by digest. The runtime moved from eclipse-temurin:21-jre,
# now built on Ubuntu 26.04, to the Ubuntu 24.04 (noble) build of the same JRE 21.0.12.1+1: the
# 26.04 image carries fixable HIGH findings in curl and in its pebble binary, and noble none.
# Change: the OpenSSL package pin removed; its revision no longer resolves, and the noble base
# needs no package upgrade.
# Change: the agent download is verified against the release's sha256.
# Change: application files copied owned by root with fixed modes, read-only to the runtime user.
# Change: the runtime user set numerically to the base's nobody account.
# Change: EXPOSE names port 8080; ${AD_PORT} is undefined when the image builds.

FROM --platform=${BUILDPLATFORM} eclipse-temurin:21.0.12.1_1-jdk-resolute@sha256:b6a11792e73e0a2d0d96f1d5cb186da289a2741f8148ed174f6654a0335745cd AS builder
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

FROM eclipse-temurin:21.0.12.1_1-jre-noble@sha256:000fd431958bc81a24abe1e8e5f0f0fd3ae365a594bd50aadb20696805f9408c

ARG OTEL_JAVA_AGENT_VERSION=2.26.1
ARG _JAVA_OPTIONS

WORKDIR /usr/src/app/

COPY --from=builder --chmod=u=rwX,go=rX /usr/src/app/ ./
ADD --checksum=sha256:cc4af5966ab72109cacc962ba3b9f99b3e88caf064c3144a451bcfe0f4950f19 --chmod=644 https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v$OTEL_JAVA_AGENT_VERSION/opentelemetry-javaagent.jar /usr/src/app/opentelemetry-javaagent.jar
ENV JAVA_TOOL_OPTIONS=-javaagent:/usr/src/app/opentelemetry-javaagent.jar

USER 65534:65534

EXPOSE 8080
ENTRYPOINT [ "./build/install/opentelemetry-demo-ad/bin/Ad" ]

# The checksum is the 2.26.1 agent's; another OTEL_JAVA_AGENT_VERSION fails the build until the checksum changes with it.
# The base defines no service account, so the runtime uses its nobody account; chart 0.40.10 sets no security context.
