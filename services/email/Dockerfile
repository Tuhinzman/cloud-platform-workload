# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. Runtime base packages upgraded to pick up security fixes.

FROM docker.io/library/ruby:3.4.7-alpine3.22 AS builder

COPY ./services/email/Gemfile Gemfile
COPY ./services/email/Gemfile.lock Gemfile.lock

RUN apk update && \
    apk add make gcc musl-dev gcompat && \
    bundle install

FROM docker.io/library/ruby:3.4.7-alpine3.22

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
