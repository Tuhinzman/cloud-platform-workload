# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: SDK builder and ASP.NET runtime pinned by digest, the images the floating 10.0 tags resolved to.
# Change: the runtime OpenSSL upgrade removed; the pinned base already carries the revision it installed.
# Change: /app is created by root and its files are copied owned by root with fixed modes, read-only to
# the runtime user; instrument.sh is no longer handed to that user. The auto-instrumentation log
# directory stays writable by it.
# Change: the runtime user set numerically to the base's app account.

FROM --platform=${BUILDPLATFORM} mcr.microsoft.com/dotnet/sdk:10.0.402@sha256:0d99ebf1ccad15037b5c98c9fe8979d6b8dbac23812feae2277a0b277b5c5ffa AS builder
ARG TARGETARCH
ARG BUILD_CONFIGURATION=Release
WORKDIR /src
COPY ["/services/accounting/", "Accounting/"]
COPY ["/pb/demo.proto", "Accounting/src/protos/demo.proto"]
RUN dotnet restore "./Accounting/Accounting.csproj" -r linux-$TARGETARCH
WORKDIR "/src/Accounting"

RUN dotnet build "./Accounting.csproj" -r linux-$TARGETARCH -c $BUILD_CONFIGURATION -o /app/build

# -----------------------------------------------------------------------------

FROM builder AS publish
ARG TARGETARCH
ARG BUILD_CONFIGURATION=Release
RUN dotnet publish "./Accounting.csproj" -r linux-$TARGETARCH -c $BUILD_CONFIGURATION -o /app/publish /p:UseAppHost=false

# -----------------------------------------------------------------------------

FROM mcr.microsoft.com/dotnet/aspnet:10.0.13@sha256:d5633778c754e89a386882eddf8dbee6942447a8a4b8267c19cf1e1158d0b0ac
WORKDIR /app
COPY --from=publish --chmod=u=rwX,go=rX /app/publish .

RUN mkdir -p /var/log/opentelemetry/dotnet && chown 1654:1654 /var/log/opentelemetry/dotnet
USER 1654:1654
ENV OTEL_DOTNET_AUTO_TRACES_ADDITIONAL_SOURCES=Accounting.Consumer

ENTRYPOINT ["./instrument.sh", "dotnet", "Accounting.dll"]

# instrument.sh ships as 0744, so only its owner could run it; the copy's X makes it executable by all while
# root keeps it. The base sets APP_UID 1654; chart 0.40.10 sets no security context for accounting.
