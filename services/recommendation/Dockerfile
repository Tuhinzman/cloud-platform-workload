# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. TLS libraries upgraded and application directories given explicit read permissions.
# Change: libuuid upgraded beside the TLS libraries. The base ships 2.41-r9, against which the
# image scan reports six fixable HIGH util-linux findings; nothing else in the base is upgraded.
# Change: requirements.lock copied into the venv stage and set as pip's constraint, so the
# requirements install and opentelemetry-bootstrap both take the versions the source gate scans.
# Upstream pins direct dependencies only; every other package resolves at build time to the
# newest release its declared range allows.

FROM docker.io/library/python:3.12-alpine3.22 AS build-venv

RUN apk update && \
    apk add gcc g++ linux-headers

COPY ./services/recommendation/requirements.txt requirements.txt
COPY ./services/recommendation/requirements.lock requirements.lock

ENV PIP_CONSTRAINT=/requirements.lock

RUN python -m venv venv && \
    venv/bin/pip install --no-cache-dir -r requirements.txt

RUN venv/bin/opentelemetry-bootstrap -a install

FROM docker.io/library/python:3.12-alpine3.22

RUN apk upgrade --no-cache libcrypto3 libssl3 libuuid

COPY --from=build-venv /venv/ /venv/

WORKDIR /app

COPY ./services/recommendation/demo_pb2_grpc.py demo_pb2_grpc.py
COPY ./services/recommendation/demo_pb2.py demo_pb2.py
COPY ./services/recommendation/logger.py logger.py
COPY ./services/recommendation/metrics.py metrics.py
COPY ./services/recommendation/recommendation_server.py recommendation_server.py

EXPOSE ${RECOMMENDATION_PORT}
RUN chmod -R a+rX /app /venv

ENTRYPOINT [ "/venv/bin/opentelemetry-instrument", "/venv/bin/python", "recommendation_server.py" ]
