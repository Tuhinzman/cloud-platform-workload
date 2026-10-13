# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: project-maintained container definition. COPY paths retargeted from src/ to services/.
# Change: builder and runtime bases pinned by digest; the builder runs on the build platform and
# cross-compiles for the target platform; the build is trimmed of local paths.
# Change: the runtime user is set numerically so the non-root identity is verifiable.
# Change: EXPOSE names port 8080; ${CHECKOUT_PORT} is undefined when the image builds.

FROM --platform=$BUILDPLATFORM golang:1.26.9-bookworm@sha256:d9c68c2c51161e12fd77e4c6320687c9cd86e1af1e3ad6e6cd63ff970641453c AS builder

WORKDIR /usr/src/app/

COPY ./services/checkout/go.mod go.mod
COPY ./services/checkout/go.sum go.sum

RUN go mod download

COPY ./services/checkout/genproto/oteldemo/ genproto/oteldemo/
COPY ./services/checkout/kafka/ kafka/
COPY ./services/checkout/money/ money/
COPY ./services/checkout/main.go main.go

ARG TARGETOS
ARG TARGETARCH
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -trimpath -ldflags "-s -w" -o checkout main.go

FROM gcr.io/distroless/static-debian12:nonroot@sha256:afa5c872c891853ca7fcf1f12c3edb23f7eeef36189728842dd51042ff57f7ab

WORKDIR /usr/src/app/

COPY --from=builder /usr/src/app/checkout ./

USER 65532:65532
EXPOSE 8080
ENTRYPOINT [ "./checkout" ]
