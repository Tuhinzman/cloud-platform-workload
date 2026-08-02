# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. Base packages upgraded during a temporary privileged stage, served content given explicit ownership and read permissions, and the container returned to the unprivileged nginx user.

FROM nginxinc/nginx-unprivileged:1.29.0-alpine3.22-otel

USER 0
RUN apk upgrade --no-cache

COPY --chown=101:101 services/image-provider/static/ /static/
COPY --chown=101:101 services/image-provider/nginx.conf.template /nginx.conf.template
RUN chmod -R a+rX /static /nginx.conf.template

USER 101

EXPOSE ${IMAGE_PROVIDER_PORT}

STOPSIGNAL SIGQUIT

# Start nginx
CMD ["/bin/sh" , "-c" , "envsubst '$OTEL_COLLECTOR_HOST $IMAGE_PROVIDER_PORT $OTEL_COLLECTOR_PORT_GRPC $OTEL_SERVICE_NAME' < /nginx.conf.template > /etc/nginx/nginx.conf && cat  /etc/nginx/nginx.conf && exec nginx -g 'daemon off;'"]
