# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: builder and runtime moved from python:3.12-alpine3.22, last published at 3.12.13, to 3.12.15-alpine3.24, pinned by digest.
# Change: the runtime apk upgrade removed; the pinned base carries the fixed packages.
# Change: requirements.lock copied into the venv stage and set as pip's constraint, so the
# requirements install and opentelemetry-bootstrap both take the versions the source gate scans.
# Upstream pins direct dependencies only; every other package resolves at build time to the
# newest release its declared range allows.
# Change: application and venv files copied owned by root with fixed modes, read-only to the runtime user.
# Change: the runtime user set numerically to the base's nobody account.
# Change: EXPOSE names port 3551, the port chart 0.40.10 sets; ${PRODUCT_REVIEWS_PORT} is undefined when the image builds.

FROM docker.io/library/python:3.12.15-alpine3.24@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4 AS build-venv

RUN apk update && \
    apk add gcc g++ linux-headers

COPY ./services/product-reviews/requirements.txt requirements.txt
COPY ./services/product-reviews/requirements.lock requirements.lock

ENV PIP_CONSTRAINT=/requirements.lock

RUN python -m venv venv && \
    venv/bin/pip install --no-cache-dir -r requirements.txt

RUN venv/bin/opentelemetry-bootstrap -a install

FROM docker.io/library/python:3.12.15-alpine3.24@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4

COPY --from=build-venv --chmod=u=rwX,go=rX /venv/ /venv/

WORKDIR /app

COPY --chmod=u=rwX,go=rX ./services/product-reviews/demo_pb2_grpc.py demo_pb2_grpc.py
COPY --chmod=u=rwX,go=rX ./services/product-reviews/demo_pb2.py demo_pb2.py
COPY --chmod=u=rwX,go=rX ./services/product-reviews/product_reviews_server.py product_reviews_server.py
COPY --chmod=u=rwX,go=rX ./services/product-reviews/database.py database.py
COPY --chmod=u=rwX,go=rX ./services/product-reviews/metrics.py metrics.py

USER 65534:65534

EXPOSE 3551
ENTRYPOINT [ "/venv/bin/opentelemetry-instrument", "/venv/bin/python", "product_reviews_server.py" ]

# The builder's apk add still reads the moving Alpine index; only the venv it builds reaches the runtime stage.
# The base has no service account, so the runtime uses its nobody account; chart 0.40.10 sets no security context.
