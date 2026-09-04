# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: vulnerable Alpine runtime packages are pinned to measured fixed revisions so the
# HIGH-severity OS findings reported by the image scan are removed without a broad upgrade.

FROM ghcr.io/mlocati/php-extension-installer:2.9.11 AS installer

FROM docker.io/library/composer:2.8.12 AS vendor

WORKDIR /tmp/

COPY ./services/quote/composer.json composer.json

RUN composer install \
    --ignore-platform-reqs \
    --no-interaction \
    --no-plugins \
    --no-scripts \
    --no-dev \
    --prefer-dist

FROM docker.io/library/php:8.4-cli-alpine3.22

RUN apk add --no-cache \
        c-ares=1.34.8-r0 \
        libcrypto3=3.5.8-r0 \
        libssl3=3.5.8-r0 \
        openssl=3.5.8-r0

COPY --from=installer /usr/bin/install-php-extensions /usr/local/bin/

RUN install-php-extensions opcache pcntl protobuf opentelemetry

WORKDIR /var/www

USER www-data

COPY --from=vendor /tmp/vendor/ vendor/

COPY ./services/quote/app/ app/
COPY ./services/quote/public/ public/
COPY ./services/quote/src/ src/

EXPOSE ${QUOTE_PORT}

CMD ["php", "public/index.php"]
