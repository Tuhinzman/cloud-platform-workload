# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: base moved from nginx-unprivileged 1.29.0-alpine3.22-otel to 1.30.6-alpine3.24-otel, pinned by digest.
# Change: the build-time apk upgrade narrowed to libexpat; the pinned base carries the other package fixes itself.
# Change: static assets and the configuration template owned by root with fixed modes, not by the nginx user.
# Change: EXPOSE names port 8081; ${IMAGE_PROVIDER_PORT} is undefined when the image builds.

FROM nginxinc/nginx-unprivileged:1.30.6-alpine3.24-otel@sha256:faa095d05e8cc390398e61ae84bf65f0c5fa7481e32d0ec2aec87c9c6708bd1d

USER 0:0
RUN apk add --no-cache 'libexpat>=2.9.0-r0'

COPY --chmod=u=rwX,go=rX services/image-provider/static/ /static/
COPY --chmod=u=rwX,go=rX services/image-provider/nginx.conf.template /nginx.conf.template

USER 101

EXPOSE 8081

STOPSIGNAL SIGQUIT

# Start nginx
CMD ["/bin/sh" , "-c" , "envsubst '$OTEL_COLLECTOR_HOST $IMAGE_PROVIDER_PORT $OTEL_COLLECTOR_PORT_GRPC $OTEL_SERVICE_NAME' < /nginx.conf.template > /etc/nginx/nginx.conf && cat  /etc/nginx/nginx.conf && exec nginx -g 'daemon off;'"]

# The CMD renders /etc/nginx/nginx.conf at startup, which the base leaves writable by the nginx user, so
# the image does not start on a read-only root filesystem. EXPOSE 8080 is inherited from the base; the
# rendered configuration listens only on IMAGE_PROVIDER_PORT. The pinned base still ships libexpat 2.8.5-r0
# (CVE-2026-77214); apk add reads the moving Alpine 3.24 index, so a rebuild can take a later libexpat revision.
# Drop that step once a base digest carries the fix.
