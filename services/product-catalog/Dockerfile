# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: the build output is a file, so the stage copy no longer ends in a slash that
# claims it is a directory. Current BuildKit tolerates the slash; other builders need not.

FROM golang:1.25-bookworm AS builder

WORKDIR /usr/src/app/

COPY ./services/product-catalog/go.mod go.mod
COPY ./services/product-catalog/go.sum go.sum

RUN go mod download

COPY ./services/product-catalog/genproto/oteldemo/ genproto/oteldemo/
COPY ./services/product-catalog/main.go main.go

RUN CGO_ENABLED=0 GOOS=linux GO111MODULE=on go build -ldflags "-s -w" -o product-catalog main.go

FROM gcr.io/distroless/static-debian12:nonroot

WORKDIR /usr/src/app/

COPY --from=builder /usr/src/app/product-catalog ./

EXPOSE ${PRODUCT_CATALOG_PORT}
ENTRYPOINT [ "./product-catalog" ]
