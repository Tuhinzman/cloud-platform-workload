# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: runtime base php:8.4-cli-alpine3.22, no longer rebuilt and carrying fixable HIGH findings
# in c-ares and OpenSSL, replaced by php:8.4-cli-alpine3.23 pinned by digest, whose own packages are
# fixed. Exact apk pins are dropped: Alpine removes a revision from the index once it is superseded.
# Change: extension installer raised from 2.9.11 to 2.9.22, the first release supporting Alpine 3.23.
# Change: composer.lock is copied into the vendor stage. Upstream copies only composer.json,
# which makes `composer install` resolve dependencies afresh on every build - measured, it
# logs "No composer.lock file present. Updating dependencies to latest instead". The source
# gate reads composer.lock, so without this the scanned dependency set and the installed one
# were free to differ and the scan would be evidence for an artifact nobody built.

FROM ghcr.io/mlocati/php-extension-installer:2.9.22@sha256:16c97587853d6254db940e5a83d2dc3287c50d407e1fd88a4be88b5a8aa0b6b5 AS installer

FROM docker.io/library/composer:2.8.12 AS vendor

WORKDIR /tmp/

COPY ./services/quote/composer.json composer.json
COPY ./services/quote/composer.lock composer.lock

RUN composer install \
    --ignore-platform-reqs \
    --no-interaction \
    --no-plugins \
    --no-scripts \
    --no-dev \
    --prefer-dist

FROM docker.io/library/php:8.4-cli-alpine3.23@sha256:da7a7a945a493ac9c015f327231afd820bbe57fc6ae22f4f520a79fbd635ba39

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
