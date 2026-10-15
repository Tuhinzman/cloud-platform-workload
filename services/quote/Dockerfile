# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout.
# Change: runtime base moved from php:8.4-cli-alpine3.22 to php:8.4-cli-alpine3.23, pinned by digest.
# Change: extension installer raised from 2.9.11 to 2.9.22, the first release supporting Alpine 3.23.
# Change: composer.lock copied into the vendor stage, so the build installs the locked set.
# Change: Composer image pinned by digest, and the protobuf and opentelemetry extensions by version.
# Change: files from the build context copied with fixed modes rather than the checkout's modes.
# Change: the runtime user is set numerically.
# Change: EXPOSE names port 8080; ${QUOTE_PORT} is undefined when the image builds.

FROM ghcr.io/mlocati/php-extension-installer:2.9.22@sha256:16c97587853d6254db940e5a83d2dc3287c50d407e1fd88a4be88b5a8aa0b6b5 AS installer

FROM docker.io/library/composer:2.8.12@sha256:5248900ab8b5f7f880c2d62180e40960cd87f60149ec9a1abfd62ac72a02577c AS vendor

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

RUN install-php-extensions opcache pcntl protobuf-5.36.2 opentelemetry-1.4.2

WORKDIR /var/www

USER 82:82

COPY --from=vendor /tmp/vendor/ vendor/

COPY --chmod=u=rwX,go=rX ./services/quote/app/ app/
COPY --chmod=u=rwX,go=rX ./services/quote/public/ public/
COPY --chmod=u=rwX,go=rX ./services/quote/src/ src/

EXPOSE 8080

CMD ["php", "public/index.php"]

# --ignore-platform-reqs stays because the Composer image lacks ext-pcntl and ext-opentelemetry, which
# the runtime stage installs. A lock change that adds a platform requirement is checked with
# `composer check-platform-reqs` against the runtime image, since this build does not check it.
