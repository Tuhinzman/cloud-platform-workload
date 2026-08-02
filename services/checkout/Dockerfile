# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.

FROM golang:1.24-bookworm AS builder

WORKDIR /usr/src/app/

COPY ./services/checkout/go.mod go.mod
COPY ./services/checkout/go.sum go.sum

RUN go mod download

COPY ./services/checkout/genproto/oteldemo/ genproto/oteldemo/
COPY ./services/checkout/kafka/ kafka/
COPY ./services/checkout/money/ money/
COPY ./services/checkout/main.go main.go

RUN CGO_ENABLED=0 GOOS=linux go build -ldflags "-s -w" -o checkout main.go

FROM gcr.io/distroless/static-debian12:nonroot

WORKDIR /usr/src/app/

COPY --from=builder /usr/src/app/checkout/ ./

EXPOSE ${CHECKOUT_PORT}
ENTRYPOINT [ "./checkout" ]
