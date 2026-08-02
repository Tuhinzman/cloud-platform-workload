# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. Base image pinned to an immutable digest, package installation narrowed with no recommended extras, TLS libraries added, and the configuration template given explicit ownership and read-only permissions.

FROM envoyproxy/envoy:v1.34.14@sha256:cfc0678bc03cca19cbb031688acb31d510bff501ff97e163026a375fe0515d69

RUN apt-get update && \
    apt-get install -y --no-install-recommends gettext-base libssl3 openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER envoy

WORKDIR /home/envoy

COPY --chown=envoy:envoy ./services/frontend-proxy/envoy.tmpl.yaml envoy.tmpl.yaml
RUN chmod 0644 envoy.tmpl.yaml

EXPOSE ${ENVOY_PORT}
EXPOSE ${ENVOY_ADMIN_PORT}
ENTRYPOINT ["/bin/sh", "-c", "envsubst < envoy.tmpl.yaml > envoy.yaml && envoy -c envoy.yaml;"]
