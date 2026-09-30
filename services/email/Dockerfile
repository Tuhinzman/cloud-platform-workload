# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. Runtime base packages upgraded to pick up security fixes.
# Change: Ruby 3.4.7 on Alpine 3.22 moved to 3.4.11 on Alpine 3.23, the first 3.4 release whose
# own erb, resolv, zlib and net-imap carry the security fixes. No 3.4.11 image exists for 3.22.

FROM docker.io/library/ruby:3.4.11-alpine3.23 AS builder

COPY ./services/email/Gemfile Gemfile
COPY ./services/email/Gemfile.lock Gemfile.lock

RUN apk update && \
    apk add make gcc musl-dev gcompat && \
    bundle install

FROM docker.io/library/ruby:3.4.11-alpine3.23

RUN apk upgrade --no-cache

COPY --from=builder /usr/local/bundle/ /usr/local/bundle/

WORKDIR /email_server

COPY ./services/email/views/ views/

COPY ./services/email/.ruby-version .ruby-version
COPY ./services/email/Gemfile Gemfile
COPY ./services/email/Gemfile.lock Gemfile.lock
COPY ./services/email/email_server.rb email_server.rb

EXPOSE ${EMAIL_PORT}
ENTRYPOINT ["bundle", "exec", "ruby", "email_server.rb"]
