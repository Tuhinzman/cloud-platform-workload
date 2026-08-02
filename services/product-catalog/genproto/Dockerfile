# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.

FROM golang:1.24-alpine

WORKDIR /build

RUN apk add --no-cache protobuf-dev

COPY ./services/product-catalog/go.mod go.mod
COPY ./services/product-catalog/go.sum go.sum

RUN go install tool
