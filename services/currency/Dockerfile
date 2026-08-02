# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0
# Copyright 2023 The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: COPY source paths retargeted from src/ to services/ for this repository layout. A default pinned OpenTelemetry C++ version added, a dedicated unprivileged user created and used, and the entrypoint corrected to an absolute path.

FROM docker.io/library/alpine:3.21 AS base

RUN apk update && \
    apk add grpc-dev protobuf-dev

FROM base AS builder

RUN apk add git cmake make g++ linux-headers

ARG OPENTELEMETRY_CPP_VERSION=1.24.0

RUN git clone --depth 1 --branch v${OPENTELEMETRY_CPP_VERSION} https://github.com/open-telemetry/opentelemetry-cpp \
    && cd opentelemetry-cpp/ \
    && mkdir build \
    && cd build \
    && cmake .. -DCMAKE_CXX_STANDARD=17 -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
          -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
          -DWITH_EXAMPLES=OFF -DWITH_OTLP_GRPC=ON -DWITH_ABSEIL=ON \
    && make -j$(nproc || sysctl -n hw.ncpu || echo 1) install && cd ../..

WORKDIR /currency

COPY ./services/currency/build/ build/
COPY ./services/currency/proto/ proto/
COPY ./services/currency/src/ src/

COPY ./services/currency/genproto/CMakeLists.txt genproto/CMakeLists.txt
COPY ./services/currency/CMakeLists.txt CMakeLists.txt

COPY ./pb/demo.proto proto/demo.proto

RUN mkdir -p build && cd build \
    && cmake .. \
    && make -j$(nproc || sysctl -n hw.ncpu || echo 1) install

FROM base AS release

COPY --from=builder /usr/local /usr/local

EXPOSE ${CURRENCY_PORT}

RUN addgroup -S app && adduser -S -G app -u 10001 app
USER app

ENTRYPOINT ["sh", "-c", "/usr/local/bin/currency ${CURRENCY_PORT}"]
