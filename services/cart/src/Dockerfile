# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: SDK and runtime bases pinned by digest; the runtime moved from alpine3.22, last published at 10.0.3, to 10.0.13-alpine3.24.
# Change: the build-time apk upgrade removed; the pinned runtime base carries its packages as published.
# Change: application files owned by root and read-only to the runtime user, which is set numerically.
# Change: EXPOSE names port 8080; ${CART_PORT} is undefined when the image builds.

FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:10.0.402@sha256:0d99ebf1ccad15037b5c98c9fe8979d6b8dbac23812feae2277a0b277b5c5ffa AS builder
ARG TARGETARCH

WORKDIR /usr/src/app/

COPY ./services/cart/ ./
COPY ./pb/ ./pb/

RUN dotnet restore ./src/cart.csproj -r linux-musl-$TARGETARCH

RUN dotnet publish ./src/cart.csproj -r linux-musl-$TARGETARCH --no-restore -o /cart

FROM mcr.microsoft.com/dotnet/runtime-deps:10.0.13-alpine3.24@sha256:1a5dbee0a1d2bb1d038e212e8ccdbc12783b5cfbed866fe75d126ee80178a52a

WORKDIR /usr/src/app/
COPY --from=builder --chmod=u=rwX,go=rX /cart/ ./

USER 1654:1654

ENV DOTNET_HOSTBUILDER__RELOADCONFIGONCHANGE=false

EXPOSE 8080
ENTRYPOINT [ "./cart" ]

# The musl restore is not in locked mode: packages.lock.json records only net10.0 and linux-x64, so --locked-mode
# fails NU1004 here, and adding the musl section is a lock change for review. The binary bundles the 10.0.13
# runtime packs of the pinned SDK, which neither Trivy pass reads, so a .NET servicing release needs a new SDK pin.
