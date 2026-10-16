# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

# Find eligible builder and runner images on Docker Hub. We use Ubuntu/Debian
# instead of Alpine to avoid DNS resolution issues in production.
#
# https://hub.docker.com/r/hexpm/elixir/tags?name=ubuntu
# https://hub.docker.com/_/ubuntu/tags
#
# This file is based on these images:
#
#   - https://hub.docker.com/r/hexpm/elixir/tags - for the build image
#   - https://hub.docker.com/_/debian/tags?name=bookworm-20250610-slim - for the release image
#   - https://pkgs.org/ - resource for finding needed packages
#   - Ex: docker.io/hexpm/elixir:1.18.4-erlang-27.3.4-debian-bookworm-20250610-slim
#

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. Runtime base moved to Debian bookworm with a newer OTP, packages upgraded, and ncurses moved to the supported major version.
# Change: the builder and runner images pinned by digest, the images their tags resolved to.
# Change: the release is copied owned by root with fixed modes, read-only to the runtime user, and /app is no
# longer handed to that user; the runtime user is set numerically to 65534:65534, the base's nobody account.
# Change: EXPOSE names port 4000; ${FLAGD_UI_PORT} is undefined when the image builds.

ARG ELIXIR_VERSION=1.19.3
ARG OTP_VERSION=28.1.1
ARG DEBIAN_VERSION=bookworm-20251117-slim

ARG BUILDER_IMAGE="docker.io/hexpm/elixir:${ELIXIR_VERSION}-erlang-${OTP_VERSION}-debian-${DEBIAN_VERSION}@sha256:bf38d0b96f66fdcc16c4365b558d63e1c6b281a3a8db8ea53429f9138b04f45f"
ARG RUNNER_IMAGE="docker.io/debian:${DEBIAN_VERSION}@sha256:b4aa902587c2e61ce789849cb54c332b0400fe27b1ee33af4669e1f7e7c3e22f"

FROM ${BUILDER_IMAGE} AS builder

# install build dependencies
RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential git \
  && rm -rf /var/lib/apt/lists/*

# prepare build dir
WORKDIR /app

# install hex + rebar
RUN mix local.hex --force \
  && mix local.rebar --force

# set build ENV
ENV MIX_ENV="prod"

# install mix dependencies
COPY ./services/flagd-ui/mix.exs ./services/flagd-ui/mix.lock ./
RUN mix deps.get --only $MIX_ENV
RUN mkdir config

# copy compile-time config files before we compile dependencies
# to ensure any relevant config change will trigger the dependencies
# to be re-compiled.
COPY ./services/flagd-ui/config/config.exs ./services/flagd-ui/config/${MIX_ENV}.exs ./services/flagd-ui/config/runtime.exs config/
RUN mix deps.compile

RUN mix assets.setup

COPY ./services/flagd-ui/priv priv

COPY ./services/flagd-ui/lib lib

COPY ./services/flagd-ui/assets assets

# compile assets
RUN mix assets.deploy

# Compile the release
RUN mix compile

COPY ./services/flagd-ui/rel rel
RUN mix release

# start a new build stage so that the final image will only contain
# the compiled release and other runtime necessities
FROM ${RUNNER_IMAGE} AS final

RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install -y --no-install-recommends libstdc++6 openssl libncurses6 locales ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Set the locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
  && locale-gen

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

WORKDIR "/app"

# set runner ENV
ENV MIX_ENV="prod"

# Only copy the final release from the build stage
COPY --from=builder --chmod=u=rwX,go=rX /app/_build/${MIX_ENV}/rel/flagd_ui ./

USER 65534:65534

EXPOSE 4000

# If using an environment that doesn't automatically reap zombie processes, it is
# advised to add an init process such as tini via `apt-get install`
# above and adding an entrypoint. See https://github.com/krallin/tini for details
# ENTRYPOINT ["/tini", "--"]

CMD ["/app/bin/server"]

# apt-get upgrade stays: even the newest bookworm-slim digest carries fixable CRITICAL findings that only the upgrade
# clears. It and both apt-get installs read the moving Debian index, so rebuilds can differ in those packages.
