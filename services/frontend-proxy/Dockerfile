# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: base moved from envoyproxy/envoy v1.34.14, past its end of life, to v1.37.9, pinned by digest.
# Change: only gettext-base is installed, at an exact version; the base carries the fixed OpenSSL itself.
# Change: the configuration template copied to /etc/envoy, owned by root and read-only to the envoy user.
# Change: the runtime user is set numerically.
# Change: EXPOSE names port 8080; ${ENVOY_PORT} and ${ENVOY_ADMIN_PORT} are undefined when the image builds.
# Change: the entrypoint execs envoy, so the process that receives the stop signal is envoy rather than the shell.

FROM envoyproxy/envoy:v1.37.9@sha256:a384f50976a8ce7511316776383f907bb5d0edffabac393ada1fdd703a5c1318

RUN apt-get update && \
    apt-get install -y --no-install-recommends gettext-base=0.21-4ubuntu4 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --chmod=644 ./services/frontend-proxy/envoy.tmpl.yaml /etc/envoy/envoy.tmpl.yaml

USER 101:101

WORKDIR /home/envoy

EXPOSE 8080
ENTRYPOINT ["/bin/sh", "-c", "envsubst < /etc/envoy/envoy.tmpl.yaml > envoy.yaml && exec envoy -c envoy.yaml"]

# gettext-base 0.21-4ubuntu4 is the only version the jammy archive carries, in its release pocket. The entrypoint
# renders envoy.yaml into /home/envoy, the base's envoy-owned home, so the image does not start on a read-only root
# filesystem. EXPOSE 10000 is inherited from the base; chart 0.40.10 sets the admin port to 10000.
