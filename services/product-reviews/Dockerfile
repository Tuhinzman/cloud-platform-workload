# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. Runtime base packages upgraded to pick up security fixes.

FROM docker.io/library/python:3.12-alpine3.22 AS build-venv

RUN apk update && \
    apk add gcc g++ linux-headers

COPY ./services/product-reviews/requirements.txt requirements.txt

RUN python -m venv venv && \
    venv/bin/pip install --no-cache-dir -r requirements.txt

RUN venv/bin/opentelemetry-bootstrap -a install

FROM docker.io/library/python:3.12-alpine3.22

RUN apk update && apk upgrade --no-cache

COPY --from=build-venv /venv/ /venv/

WORKDIR /app

COPY ./services/product-reviews/demo_pb2_grpc.py demo_pb2_grpc.py
COPY ./services/product-reviews/demo_pb2.py demo_pb2.py
COPY ./services/product-reviews/product_reviews_server.py product_reviews_server.py
COPY ./services/product-reviews/database.py database.py
COPY ./services/product-reviews/metrics.py metrics.py


EXPOSE ${PRODUCT_REVIEWS_PORT}
ENTRYPOINT [ "/venv/bin/opentelemetry-instrument", "/venv/bin/python", "product_reviews_server.py" ]
