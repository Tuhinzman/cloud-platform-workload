# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. Runtime base packages upgraded to pick up security fixes.
# Change: Ruby 3.4.7 on Alpine 3.22 moved to 3.4.11 on Alpine 3.23, the first 3.4 release whose
# own erb, resolv, zlib and net-imap carry the security fixes. No 3.4.11 image exists for 3.22.
# Change: builder and runtime pinned by digest, the image the 3.4.11-alpine3.23 tag resolved to.
# Change: gems and application files copied owned by root with fixed modes, read-only to the runtime user;
# the base's world-writable gem directory, also Bundler's configuration directory, is set to 0755.
# Change: the runtime user set numerically to the base's nobody account.
# Change: EXPOSE names port 8080; ${EMAIL_PORT} is undefined when the image builds.

FROM docker.io/library/ruby:3.4.11-alpine3.23@sha256:ed7dfb6ccf31f54d33286eef060f611cfecbe03db3abffa37a999c0c7a9ba7a1 AS builder

COPY ./services/email/Gemfile Gemfile
COPY ./services/email/Gemfile.lock Gemfile.lock

RUN apk update && \
    apk add make gcc musl-dev gcompat && \
    bundle install

FROM docker.io/library/ruby:3.4.11-alpine3.23@sha256:ed7dfb6ccf31f54d33286eef060f611cfecbe03db3abffa37a999c0c7a9ba7a1

RUN apk upgrade --no-cache && \
    chmod 0755 "$GEM_HOME"

COPY --from=builder --chmod=u=rwX,go=rX /usr/local/bundle/ /usr/local/bundle/

WORKDIR /email_server

COPY --chmod=u=rwX,go=rX ./services/email/views/ views/

COPY --chmod=u=rwX,go=rX ./services/email/.ruby-version .ruby-version
COPY --chmod=u=rwX,go=rX ./services/email/Gemfile Gemfile
COPY --chmod=u=rwX,go=rX ./services/email/Gemfile.lock Gemfile.lock
COPY --chmod=u=rwX,go=rX ./services/email/email_server.rb email_server.rb

USER 65534:65534

EXPOSE 8080
ENTRYPOINT ["bundle", "exec", "ruby", "email_server.rb"]

# apk upgrade stays: the pinned base still carries zlib 1.3.2-r0 (CVE-2026-85091), which it moves to r1. It
# and the builder's apk add read the moving Alpine index, so rebuilds can differ in those packages.
# COPY keeps an existing directory's mode, so GEM_HOME's 1777 from the base is changed before the copy.
# The base has no service account, so the runtime uses its nobody account; chart 0.40.10 sets no security context.
