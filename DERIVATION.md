# Derivation Record

This repository contains a derived copy of an upstream application. This record states
exactly what was taken, from where, what was changed, and how to reproduce the result. It
exists because the repository does not carry upstream Git history, so provenance has to be
recoverable from documentation instead.

## Upstream Source

| | |
|---|---|
| Project | OpenTelemetry Demo |
| Repository | `https://github.com/open-telemetry/opentelemetry-demo` |
| Pinned release tag | `2.2.0` |
| Pinned commit | `b74a7bc7bbe66099c61951f42b24dab8b6f02d18` |
| Licence | Apache License 2.0 |
| NOTICE file at the pinned tag | Not present, verified with `git ls-tree` |

Every upstream path below is quoted relative to the upstream repository root at that tag.

## Ownership Boundary

Upstream owns the application source, the service architecture, the protobuf contracts, the
existing OpenTelemetry instrumentation, and the upstream project structure. The
instrumentation in particular is upstream work, and its presence is part of why this
workload was selected rather than something this project built.

This project owns the container definitions as modified here, the container hardening, the
build context layout, the delivery pipeline, scanning and exception governance, SBOM
integration, registry publication, the deployment structure, the validation, and the
evidence.

Neither side is overstated. This project did not write this application, and it is not
merely deploying an unchanged one.

## What Was Taken

Seventeen component directories and the protobuf contract. Each component moved from
`src/<name>` upstream to `services/<name>` here. The contract moved from `pb/demo.proto` to
`pb/demo.proto`. The upstream `LICENSE` was copied unchanged.

## What Was Excluded

| Excluded | Upstream path | Reason |
|---|---|---|
| flagd | `src/flagd` | No container definition at the pinned tag, verified. Classified as the justified upstream exception rather than built here; not yet mirrored, scanned or enabled in any environment. |
| kafka | `src/kafka` | Infrastructure dependency. Deployment form is an open implementation decision. |
| postgresql | `src/postgresql` | Infrastructure dependency. Data that outlives its environment belongs in a managed service. |
| load-generator | `src/load-generator` | Not deployed. Runs as root and carries a large volume of unfixed operating-system findings. May be enabled inside a bounded, owner-approved validation window. |
| llm | `src/llm` | Not deployed. |
| react-native-app | `src/react-native-app` | Not deployed. |
| grafana, jaeger, opensearch, otel-collector, prometheus | `src/*` | Observability belongs to the platform. Telemetry reaches the platform gateway only. |
| `kubernetes/` | `kubernetes/` | Desired state belongs in the deployment repository, not here. |
| `internal/` | `internal/` | Upstream repository tooling with no role in this project. |

## Build Context

Every container definition builds from the repository root. Seven components copy the
shared contract from `pb/`, which no per-service context can reach: `accounting`, `ad`,
`cart`, `currency`, `fraud-detection`, `frontend`, and `payment`, across eight container
definitions. A root context is the only layout that serves the whole fleet without
duplicating the contract into each service.

Using the root context requires one change: `COPY` source paths move from `src/<name>/` to
`services/<name>/`. The context choice requires no other build change. Changes that
individual definitions carry beyond this, such as hardening or the project-maintained
checkout and product-catalog definitions, are separate decisions recorded per component below.

The root [.dockerignore](.dockerignore) is derived from the upstream root file with the
same path retargeting. It excludes container definitions from the context on purpose, since
Docker reads the Dockerfile through `-f`, so an edit to one service's definition does not
invalidate cached layers for the rest of the fleet.

Ten per-service `.dockerignore` files were carried from upstream unchanged, under
`accounting`, `cart/src`, `currency`, `email`, `flagd-ui`, `fraud-detection`, `frontend`,
`payment`, `quote`, and `shipping`. Under a root context these are not the effective ignore
file. They are retained as upstream content rather than deleted, and the root file is what
governs.

## Per-Component Derivation

Every container definition retained in this repository appears exactly once. Twenty-four in
total: twenty-two modified and carrying an Apache-2.0 modification notice, two retained
exactly as upstream wrote them.

| Container definition | Component | Status |
|---|---|---|
| `services/checkout/Dockerfile` | checkout | Project-maintained since 2026-10-13: rewritten from upstream's definition, which it still follows in stage layout; the changes are listed under Hardening applied |
| `services/checkout/genproto/Dockerfile` | checkout | Path-only modified |
| `services/currency/genproto/Dockerfile` | currency | Path-only modified |
| **`services/frontend/Dockerfile`** | **frontend** | **Path plus hardening** |
| `services/frontend/genproto/Dockerfile` | frontend | Path-only modified |
| `services/frontend/Dockerfile.cypress` | frontend | Path-only modified |
| `services/product-catalog/Dockerfile` | product-catalog | Project-maintained since 2026-10-13: rewritten from upstream's definition, which it still follows in stage layout; the changes are listed under Hardening applied |
| `services/product-catalog/genproto/Dockerfile` | product-catalog | Path-only modified |
| `services/quote/Dockerfile` | quote | Path plus hardening |
| `services/shipping/Dockerfile` | shipping | Path plus hardening |
| `services/product-reviews/genproto/Dockerfile` | product-reviews | Upstream unchanged |
| `services/recommendation/genproto/Dockerfile` | recommendation | Upstream unchanged |
| `services/accounting/Dockerfile` | accounting | Path plus hardening |
| `services/ad/Dockerfile` | ad | Path plus hardening |
| `services/cart/src/Dockerfile` | cart | Path plus hardening |
| `services/currency/Dockerfile` | currency | Path plus hardening |
| `services/email/Dockerfile` | email | Path plus hardening |
| `services/flagd-ui/Dockerfile` | flagd-ui | Path plus hardening |
| `services/fraud-detection/Dockerfile` | fraud-detection | Path plus hardening |
| `services/payment/Dockerfile` | payment | Path plus hardening |
| `services/product-reviews/Dockerfile` | product-reviews | Path plus hardening |
| `services/recommendation/Dockerfile` | recommendation | Path plus hardening |
| `services/frontend-proxy/Dockerfile` | frontend-proxy | Configured component, path plus hardening |
| `services/image-provider/Dockerfile` | image-provider | Configured component, path plus hardening |
| No container definition upstream | flagd | Upstream exception |

One change to `services/accounting/Dockerfile` was reviewed and rejected. The file itself is
retained and appears once above, as path plus hardening. The rejection is recorded under
rejected modifications below.

`frontend` and `product-catalog` keep the root build context. The prior bare-metal project
had adapted both to a per-service build context, dropping the `./src/<name>/` prefix
entirely. That adaptation is not carried, because it does not work for the seven components
that copy from `pb/`, and using two different context models across one fleet would make
the pipeline harder to share than the problem it solves.

### Modified upstream files that are not container definitions

The table above covers container definitions. Twenty-five upstream-derived files under
`services/checkout/`, `services/product-catalog/`, `services/shipping/`,
`services/quote/`, `services/frontend/`, `services/payment/`, `services/cart/`,
`services/email/`, `services/flagd-ui/`, `services/ad/`, `services/fraud-detection/`, and
`services/accounting/` also differ from the pinned source, and they
are recorded here so the modification inventory is not limited to container definitions. Those applications remain
upstream work. What follows are corrections and dependency movement applied on top of them,
not authorship of the services.

| File | Kind | Change measured against the pinned source |
|---|---|---|
| `services/checkout/main.go` | Application source | Three static-analysis corrections, each already stated in the file's own modification notice: `status.Errorf` replaced with `status.Error` where the message is a non-constant string, which `go vet` rejects as a non-constant format string; the error returned by `openfeature.SetProvider` explicitly discarded rather than silently dropped; and the receive from the Kafka `Successes()` channel no longer assigned to the blank identifier. Applied in `348490c`. |
| `services/checkout/go.mod` | Dependency and toolchain metadata | The `go` directive raised from `1.24.2` to `1.25.0`, direct dependencies advanced, and the indirect set re-resolved as a consequence, in `a384c3d` and `bf07e2e`. Later remediation in `14d12f3` advanced `google.golang.org/grpc` to `1.83.1`, `golang.org/x/crypto` to `0.55.0`, `golang.org/x/mod` to `0.40.0`, and the OpenTelemetry Go modules to `1.44.0`, with the consequential indirect movement that re-resolution produced. On 2026-10-13 the `go` directive was raised from `1.25.0` to `1.26.0`, because `golang.org/x/net` `v0.60.0`, the first release clear of the HIGH finding CVE-2026-78669 that both scans reported against `v0.58.0`, declares `go 1.26.0`. The same change moved `golang.org/x/crypto` to `0.57.0`, `golang.org/x/mod` to `0.41.0`, `golang.org/x/sys` to `0.48.0` and `golang.org/x/text` to `0.42.0`, each required by the new `x/net` or by a module it requires; no direct dependency moved. The directive is a minimum, not a compiler pin: the container builder and the Go tier's CI jobs run Go 1.26.9. |
| `services/checkout/go.sum` | Dependency checksum metadata | Checksum metadata corresponding to the dependency changes recorded above. Applied in `a384c3d`, `bf07e2e`, and `14d12f3`. The earlier `a384c3d` and `bf07e2e` pair touched thirty-five distinct module paths. The 2026-10-13 change touched six: the five modules above and `golang.org/x/sync`, `0.22.0` to `0.23.0`, which `golang.org/x/text` `0.42.0` requires and which only dependencies' tests import, so it appears in `go.sum` and not in `go.mod`. |
| `services/product-catalog/main.go` | Application source | One static-analysis correction, stated in the file's own modification notice: `status.Errorf` replaced with `status.Error` at the two call sites where the message is a non-constant string, which `go vet` rejects as a non-constant format string. The three remaining `status.Errorf` calls in the file pass constant format strings and are unchanged. Recorded in the same change that applies it, so no earlier commit is cited. |
| `services/product-catalog/go.mod` | Dependency and toolchain metadata | `0463437` raised the `go` directive from `1.24.2` to `1.25.0`, which the fixed module versions require; moved `github.com/open-feature/go-sdk-contrib/providers/flagd` from `v0.3.1` to `v0.4.0`, the lowest version that builds against the fixed flagd core; moved `google.golang.org/grpc` from `v1.78.0` to `v1.83.2` and `go.opentelemetry.io/otel` with its `sdk`, `sdk/metric` and `trace` modules from `v1.39.0` to `v1.44.0`; and promoted `go.opentelemetry.io/otel/metric` from an indirect to a direct `v1.44.0` requirement. The indirect set moved as re-resolution required. On 2026-10-13 the `go` directive was raised from `1.25.0` to `1.26.0` for the same `golang.org/x/net` `v0.60.0` remediation recorded for checkout, and `golang.org/x/mod`, `golang.org/x/sys` and `golang.org/x/text` moved to the same versions as there; no direct dependency moved. |
| `services/product-catalog/go.sum` | Dependency checksum metadata | Checksum metadata corresponding to the `go.mod` changes above, applied in `0463437` and on 2026-10-13. The later change touched five module paths: the four above and `golang.org/x/sync`, moved for the same reason as in checkout. |
| `services/shipping/src/shipping_service.rs` | Application source | Byte-identical to the pinned release until `9406cac`, verified against the upstream blob. That change removed an unnecessary `as u32` cast on an item quantity that is already `u32`, and initialised the required `address` and `items` fields of the `ShipOrderRequest` test fixture, which the upstream literal left empty. |
| `services/quote/composer.json` | Dependency metadata | `1b4deb0` moved `guzzlehttp/guzzle` from `7.10.0` to `7.15.2` to clear the HIGH-severity finding the image scan reported against it, and changed nothing else at that time. `8bcc926` later moved `react/http` from `v1.11.0` to `v1.11.1` for CVE-2026-84997, a HIGH the blocking scan gate reported against a subsequent build. Each entry records the scan result of its own moment: the digest published before that second change was built from the earlier source and is not retrospectively remediated by it, and republishing quote and promoting the remediated digest are separate work that has not been done. |
| `services/frontend/pages/api/product-ask-ai-assistant/[productId]/index.ts` | Application source | The unused `AddItemRequest` import specifier removed. `Empty` is still imported from the same module, so the import statement and its side effects are unchanged. Recorded in the same change that applies it, so no earlier commit is cited. |
| `services/frontend/pages/api/product-reviews-avg-score/[productId]/index.ts` | Application source | The unused `ProductReview` import specifier removed, on the same basis: `Empty` is still imported from the same module. Recorded in the same change that applies it. |
| `services/frontend/providers/Ad.provider.tsx` | Application source | The unused `Money` import specifier removed. `Ad` and `Product` are still imported from the same module. Recorded in the same change that applies it. |
| `services/frontend/providers/ProductReview.provider.tsx` | Application source | The unused `useEffect` import specifier removed. The other three React imports are still used, so the import statement remains. Recorded in the same change that applies it. |
| `services/frontend/components/ProductReviews/ProductReviews.tsx` | Application source | `remainder` declared with `const` rather than `let`. It is assigned once and only read afterwards, so the change is behaviour-neutral. Recorded in the same change that applies it. |
| `services/frontend/package.json` | Dependency metadata | `94eeedf` moved six direct pins: `next` from `16.1.1` to `16.3.3`, `sharp` from `0.34.5` to `0.35.4`, `styled-components` from `6.2.0` to `6.4.0`, `@grpc/grpc-js` from `1.12.6` to `1.12.7`, `@opentelemetry/auto-instrumentations-node` from `0.67.3` to `0.78.0` and `@opentelemetry/sdk-node` from `0.208.0` to `0.220.0`. A later change moved `next` to `16.3.6` for GHSA-vcvr-r3jv-pc5j and `@grpc/grpc-js` to `1.13.6` for CVE-2026-101916, and `@openfeature/flagd-provider` from `0.13.3` to `0.13.4`, the first release whose peer range admits a fixed `@grpc/grpc-js`. A third change moved `next` to `16.3.8` for CVE-2026-94483 and `sharp` to `0.35.5` for GHSA-wq5f-xc86-pv6w. |
| `services/frontend/package-lock.json` | Dependency lock metadata | Re-resolved by npm for those pins, in `94eeedf`, and again for the later ones, which move twelve entries and add or remove none. The third re-resolution moves 38 entries and adds or removes none: `next`, `@next/env` and the `@next/swc-*` binaries, `sharp` and its `@img/*` platform packages, and `source-map-js` from `1.2.1` to `1.2.2` for CVE-2026-93749, a version the `^1.2.1` range of `postcss` already admits. |
| `services/payment/package.json` | Dependency metadata | `d2f3481` moved three direct pins: `@grpc/grpc-js` from `1.12.6` to `1.12.7`, `@opentelemetry/auto-instrumentations-node` from `0.67.3` to `0.78.0` and `@opentelemetry/sdk-node` from `0.208.0` to `0.220.0`. A later change moved `@grpc/grpc-js` to `1.13.6` for CVE-2026-101916 and `@openfeature/flagd-provider` from `0.13.3` to `0.13.4`, the first release whose peer range admits it. |
| `services/payment/package-lock.json` | Dependency lock metadata | Re-resolved by npm for those pins, in `d2f3481`, and again for the later ones, which move two entries and add or remove none. |
| `services/cart/src/cart.csproj` | Dependency metadata | `30c556a` moved `OpenTelemetry.Resources.Host` from `1.14.0-beta.1` to `1.16.0-beta.2`, the first published version carrying the fix for GHSA-v8pv-4842-x354, and changed nothing else. |
| `services/email/Gemfile.lock` | Dependency metadata | Four gems moved within the unchanged `Gemfile` constraints to clear the HIGH and CRITICAL findings both scan gates reported: rack 3.1.15 to 3.1.22, rack-session 2.1.1 to 2.1.2, net-imap 0.5.8 to 0.5.15 and puma 7.1.0 to 7.2.1, resolved with `bundle update --conservative` under the locked Bundler 2.6.7. |
| `services/email/.ruby-version` | Toolchain metadata | 3.4.7 to 3.4.11, matching the container definition's move to the first 3.4 release whose bundled gems carry the fixes. |
| `services/flagd-ui/mix.exs` | Dependency metadata | bandit raised from `~> 1.10.0` to `~> 1.12.5` and req from `~> 0.5.16` to `~> 0.6.1`, the smallest constraints that clear the HIGH findings the source gate reported without taking bandit releases that carry newer HIGH advisories. The file carries a modification notice. |
| `services/flagd-ui/mix.lock` | Dependency metadata | Re-resolved for those constraints, and six unused entries unlocked (cowboy, cowboy_telemetry, cowlib, opentelemetry_cowboy, opentelemetry_phoenix_live_view_process_propagator, ranch); fourteen packages moved, among them bandit 1.12.5, mint 1.11.0, phoenix 1.8.15, plug 1.20.3 and req 0.6.3. |
| `services/ad/build.gradle` | Build script and dependency metadata | Every configuration locked in strict mode against the committed `gradle.lockfile`, outside the `-Pspeed` path, which compiles against copied jars rather than a resolved graph; jackson raised from `2.20.1` to `2.21.7` and aligned through its BOM, and netty aligned on `4.2.18.Final` through its BOM. The file carries a modification notice. |
| `services/fraud-detection/build.gradle.kts` | Build script and dependency metadata | Every configuration locked in strict mode against the committed `gradle.lockfile`; `kafka-clients` raised from `4.1.1` to `4.1.2`, and jackson `2.21.7` and netty `4.2.18.Final` aligned through their BOMs. The file carries a modification notice. |
| `services/accounting/Accounting.csproj` | Dependency metadata | `OpenTelemetry.AutoInstrumentation` stays at `1.13.0`; six packages it brings in are referenced directly at fixed versions: `OpenTelemetry.Resources.Host` `1.16.0-beta.2`, `OpenTelemetry.Exporter.Zipkin` `1.15.3`, `OpenTelemetry.Extensions.Propagators` `1.15.3`, `OpenTelemetry.Resources.Azure` `1.15.1-beta.1`, and `OpenTelemetry.Exporter.Console` and `OpenTelemetry.Exporter.OpenTelemetryProtocol` at `1.16.0`, the SDK release Host's fix requires and whose internals both exporters use. The file carries a modification notice. |

Every dependency change above was made to move off modules a scan reported findings against:
the image scan, which is the reason recorded in `a384c3d`, `bf07e2e`, `14d12f3`, and `1b4deb0`;
the source gate, which is the reason recorded in `0463437`, `94eeedf`, `d2f3481`, and
`30c556a`, and for the `services/flagd-ui/` changes; both gates for the later frontend and
payment moves; both scan gates for the `services/email/`, `services/ad/` and
`services/fraud-detection/` changes; and the .NET dependency audit, which stops the Release
build, with the source gate for the `services/accounting/` change. Neither the changes nor this
record claims any review of those dependencies beyond that.

Both `main.go` files, `shipping_service.rs`, the five `services/frontend/` source files, both
`.csproj` files, flagd-ui's `mix.exs` and the two Gradle build scripts above carry an
Apache-2.0 modification notice in the format described below. The `go.mod` and `go.sum` files, `composer.json`, the `package.json`
and `package-lock.json` files, `Gemfile.lock`, `.ruby-version` and `mix.lock` carry none, and
none is added. `Gemfile.lock` and `mix.lock` are rewritten whole by Bundler and Mix, and
`.ruby-version` holds a single version string, so none of them can hold one. `go.sum` is a
line-oriented checksum list with no comment syntax, and `composer.json`, `package.json` and
`package-lock.json` are strict JSON, which rejects comments outright, so none of them can hold
one. `go.mod` does support `//` comments, but neither copy carries an upstream copyright or
licence header for a notice to sit beneath, and both are dependency metadata maintained by the
Go toolchain rather than authored source. This table is the record of their modification.

### Hardening applied, by component

| Component | Change beyond the path retargeting |
|---|---|
| checkout | Container definition project-maintained from 2026-10-13. Builder `golang:1.26.9-bookworm` and runtime `gcr.io/distroless/static-debian12:nonroot` pinned by digest; the builder moved off the 1.25 line to Go 1.26.9, the first 1.26 release clear of the stdlib findings the image scan reported; the builder runs on the build platform and cross-compiles for the target, so `linux/amd64` images build without emulation on other hosts; `-trimpath` added; runtime user set numerically to 65532:65532; `EXPOSE` names port 8080, because the earlier `EXPOSE ${CHECKOUT_PORT}` named a variable undefined at build time and the image declared no port. The process still binds the port `CHECKOUT_PORT` sets at runtime. The multi-stage layout, `CGO_ENABLED=0`, `-ldflags "-s -w"` and entrypoint behaviour are upstream's and unchanged |
| product-catalog | Container definition project-maintained from 2026-10-13, the same changes as checkout; the dead `GO111MODULE=on` setting dropped and the floating `golang:1.25-bookworm` builder replaced by the digest pin |
| accounting | Runtime OpenSSL packages, `libssl3t64` and `openssl`, upgraded to the fixed revision the newest `aspnet:10.0` digest does not yet carry, while the stage is still root |
| ad | OpenTelemetry Java agent defaulted to 2.26.1, the first release clear of a CRITICAL the image scan reported; OpenSSL pinned to the fixed revision the newest `eclipse-temurin:21-jre` digest does not yet carry; `gradle.lockfile` copied with the build files so the strict lock holds in the image build; the duplicate jar copy removed before the runtime stage |
| cart | Runtime base moved from `mcr.microsoft.com/dotnet/runtime-deps:10.0-alpine3.22`, whose last published image is 10.0.3 from 2026-02-10 and whose own packages carry 71 fixable findings in OpenSSL, zlib and musl, two of them CRITICAL and fifteen HIGH, to `10.0.13-alpine3.24` pinned by digest; at the scanner database of 2026-10-15 its packages carry no finding at any severity. The build-time `apk upgrade` that cleared the old base's findings is removed: it upgraded nine packages to whatever the Alpine 3.22 index served on the day of the build. The SDK builder is pinned by digest to `10.0.402`, the image the floating `sdk:10.0` tag resolved to when it was pinned, so the 10.0.13 runtime packs the self-contained binary bundles change only with a new SDK pin. Everything under `/usr/src/app` is owned by root and readable, not writable, by the runtime user; with the old `--chown=app:app` that user could append to, chmod and touch the `cart` binary and `appsettings.json`. The runtime user is set numerically to 1654:1654, the base's `app` account; chart 0.40.10 sets no security context for cart. `EXPOSE` names port 8080 instead of the undefined `${CART_PORT}`; the process still binds the port it is given at runtime, through `ASPNETCORE_URLS` in the chart and `ASPNETCORE_HTTP_PORTS` in CI. Checkouts in three file modes produced identical files, modes and owners, and the published files are byte-identical whether the builder runs on an arm64 or an amd64 host; the layer digest of the copied application differs between builds. Neither scan inventories the .NET runtime packs the binary bundles. The project-added `packages.lock.json` is refreshed under the same SDK, which moved only the implicit `Microsoft.NET.ILLink.Tasks` from 10.0.12 to 10.0.13; before the refresh, the locked restore `cart:lint-dotnet` runs failed NU1004 under SDK 10.0.402. The image's own musl restore stays unlocked, because the lock records only `net10.0` and `linux-x64`. Below the gate, the source pass reports three fixable MEDIUM findings in `OpenTelemetry.Exporter.OpenTelemetryProtocol` 1.14.0, fixed in 1.15.2 and 1.15.3 |
| currency | Default pinned OpenTelemetry C++ version, dedicated unprivileged user, entrypoint corrected to an absolute path |
| email | Base packages upgraded, Ruby moved from 3.4.7 on Alpine 3.22 to 3.4.11 on Alpine 3.23, the first 3.4 release whose bundled gems carry the fixes the scan gates require |
| flagd-ui | Runtime base moved to Debian bookworm, newer OTP, packages upgraded, ncurses moved to the supported major version |
| fraud-detection | OpenTelemetry Java agent defaulted to 2.26.1, the first release clear of a CRITICAL the image scan reported; runtime base moved from distroless `java17-debian12` to `java17-debian13`, because the newest debian12 digest still carries nine fixable HIGH findings and distroless cannot upgrade in place; the Java major is unchanged |
| image-provider | Base moved from `nginxinc/nginx-unprivileged:1.29.0-alpine3.22-otel`, whose image dates from 2025-08-18 and whose own Alpine packages carry 49 fixable HIGH and CRITICAL findings, to the stable `1.30.6-alpine3.24-otel` pinned by digest, which carries the same OpenTelemetry module version, 0.1.2; at the scanner database of 2026-10-15 its own packages carry no fixable HIGH or CRITICAL finding. The build-time `apk upgrade` that cleared the old base's findings is removed: it installed whatever the Alpine 3.22 index served on the day of the build, and it left nginx itself at 1.29.0. With no `RUN` step left, builds of the same tree from checkouts in three file modes produced identical files, modes and owners; their layer digests match too when the checked-out files carry the same modification times, which `COPY` keeps. `static/` and `nginx.conf.template` are copied owned by root with fixed modes, so the nginx user can read them and change none of them; before, they were owned by that user and writable by it. The runtime user stays 101, which chart 0.40.10 does not override. `EXPOSE` names port 8081 instead of the undefined `${IMAGE_PROVIDER_PORT}`; the base's own `EXPOSE 8080` is inherited, and the rendered configuration listens on `IMAGE_PROVIDER_PORT` only. The CMD still renders `/etc/nginx/nginx.conf` at startup, which the base leaves writable by the nginx user, so the image does not start on a read-only root filesystem |
| frontend | Builder and dependency stages pinned by digest to `node:22.23.3-bookworm-slim`, the image the floating `node:22-slim` tag resolved to when it was pinned; its own OS and npm packages carry fixable CRITICAL and HIGH findings that no gate reads, because only the runtime stage ships. Runtime base moved from `nodejs22-debian12`, whose libssl3 carried fixable CRITICAL and HIGH findings, to `nodejs22-debian13` and pinned by digest. The stage that installed libssl3t64 3.5.7-1~deb13u3 over the base was removed: the pinned `nodejs22-debian13:nonroot` digest ships that version itself, and the stage's own guard rejects such a base. Everything under `/app` is owned by root and readable, not writable, by the runtime user: `public/` and `Instrumentation.js` are copied with fixed modes rather than the checkout's, and the stage runs as root until its last `USER`, because BuildKit creates `WORKDIR` as the active user and the base sets 65532. The runtime user is set numerically to 65532:65532; chart 0.40.10 sets `runAsUser` and `runAsGroup` 1001 for frontend, an identity that owns nothing there either. `EXPOSE` names port 8080 instead of the undefined `${FRONTEND_PORT}`; the server still listens on the port `PORT` sets at runtime. Upstream's separate builder and dependency stages, the standalone output and the full production `node_modules` copied beside it are kept. Neither scan inventories the Node runtime in the base or the OpenSSL it bundles |
| payment | Builder pinned by digest to `node:22.23.3-bookworm-slim`, the image the floating `node:22-slim` tag resolved to when it was pinned; its own OS and npm packages carry fixable CRITICAL and HIGH findings that no gate reads, because only the runtime stage ships. Runtime base moved from `nodejs22-debian12`, whose libssl3 carried fixable CRITICAL and HIGH findings, to `nodejs22-debian13` and pinned by digest. The stage that installed libssl3t64 3.5.7-1~deb13u3 over the base was removed: the pinned `nodejs22-debian13:nonroot` digest ships that version itself, it is the only package that differs from the digest it replaces, and the stage's own guard rejects such a base. Everything under `/usr/src/app` is owned by root and readable, not writable, by the runtime user: `node_modules` and `demo.proto` are no longer owned by that user, files from the build context are copied with mode 644 rather than the checkout's mode, and the stage runs as root until its last `USER`, because BuildKit creates `WORKDIR` as the active user and the base sets 65532. The runtime user is set numerically to 65532:65532; chart 0.40.10 sets `runAsUser` and `runAsGroup` 1000 for payment, an identity that owns nothing there either. `EXPOSE` names port 8080 instead of the undefined `${PAYMENT_PORT}`; the process still binds the port `PAYMENT_PORT` sets at runtime. Neither scan inventories the Node runtime in the base or the OpenSSL it bundles |
| product-reviews | Builder and runtime moved from `python:3.12-alpine3.22`, whose last published image is 3.12.13 from 2026-04-17 and whose own packages carry 66 fixable findings, ten of them HIGH in OpenSSL and libuuid, to `3.12.15-alpine3.24` pinned by digest; at the scanner database of 2026-10-15 its packages carry no fixable HIGH or CRITICAL finding. The full runtime `apk upgrade`, which took whatever the Alpine 3.22 index served on the day of the build, is removed. Everything under `/app` and `/venv` is copied owned by root with fixed modes, readable and not writable by the runtime user, and checkouts in three file modes produced the same types, modes and owners. The image ran as root; the runtime user is set numerically to 65534:65534, the base's `nobody` account, and chart 0.40.10 sets no security context. `EXPOSE` names port 3551, the port chart 0.40.10 sets, instead of the undefined `${PRODUCT_REVIEWS_PORT}`; the CI health test sets 8080 through that variable. Dependency install stays constrained to the committed `requirements.lock`, and `pip freeze` inside the image equals it. Rebuilds differ in the timestamped bytecode pip writes and in psutil's compiled extension, which the builder compiles from source with whatever gcc the Alpine index serves. Below the gate, pip 25.0.1 in the base and in the virtual environment, python-dotenv 1.2.1 and zlib `1.3.2-r0` carry fixable MEDIUM and LOW findings. The zlib finding, CVE-2026-85091, is new to this definition: the removed upgrade had moved zlib to `1.3.2-r1`, which the pinned base does not carry yet |
| quote | Runtime base moved from `php:8.4-cli-alpine3.22`, which is no longer rebuilt and whose OpenSSL and c-ares carried fixable HIGH findings, to `php:8.4-cli-alpine3.23` pinned by digest, whose own packages carry the fixes the image scan requires. No `apk` package is pinned to an exact revision over it, because Alpine keeps one revision per package in a branch's index and drops it once it is superseded. Extension installer raised to 2.9.22, pinned by digest, for Alpine 3.23 support. `composer.lock` is copied into the vendor stage: upstream copies only `composer.json`, so `composer install` logged "No composer.lock file present. Updating dependencies to latest instead" and resolved afresh on every build. The set the source gate scans could then differ from the set the image installs. The vendor stage's `composer:2.8.12` is pinned by digest, the image the tag resolved to when it was pinned; its own OS packages carry fixable CRITICAL and HIGH findings that no gate reads, because only the runtime stage ships. The `protobuf` and `opentelemetry` extensions are pinned to `5.36.2` and `1.4.2`, the versions their unversioned names resolved to; unversioned, PECL chose the version at build time. `--ignore-platform-reqs` is kept: the Composer image lacks `ext-pcntl` and `ext-opentelemetry`, which the runtime stage installs, and the runtime meets every platform requirement `composer.lock` declares at this change; the build itself does not check that. Everything under `/var/www` that the build copies is owned by root and readable, not writable, by the runtime user. `app/`, `public/` and `src/` are copied with fixed modes rather than the checkout's: from a 0600 checkout the runtime user could not read them, and from a 0666 checkout it could rewrite them. `vendor/` keeps the modes Composer writes. The runtime user is set numerically to 82:82, the base's `www-data`; chart 0.40.10 sets `runAsUser` and `runAsGroup` 33 for quote, an identity with no account in this image that owns nothing there either. `EXPOSE` names port 8080 instead of the undefined `${QUOTE_PORT}`; the process still binds the port `QUOTE_PORT` sets at runtime. Neither scan inventories the PHP interpreter the base builds from source or the two PECL extensions compiled into the image |
| recommendation | Builder and runtime moved from `python:3.12-alpine3.22`, whose last published image is 3.12.13 from 2026-04-17 and whose own packages carry 66 fixable findings, ten of them HIGH in OpenSSL and libuuid, to `3.12.15-alpine3.24` pinned by digest; at the scanner database of 2026-10-15 its packages carry no fixable HIGH or CRITICAL finding. The runtime upgrade of `libcrypto3`, `libssl3` and `libuuid`, which took whatever the Alpine 3.22 index served on the day of the build, is removed, and so is the `chmod -R` step. Everything under `/app` and `/venv` is copied owned by root with fixed modes, readable and not writable by the runtime user, and checkouts in three file modes produced the same types, modes and owners. The image ran as root; the runtime user is set numerically to 65534:65534, the base's `nobody` account, and chart 0.40.10 sets no security context. `EXPOSE` names port 8080 instead of the undefined `${RECOMMENDATION_PORT}`. Dependency install stays constrained to the committed `requirements.lock`, and `pip freeze` inside the image equals it. Rebuilds differ in the timestamped bytecode pip writes and in psutil's compiled extension, which the builder compiles from source with whatever gcc the Alpine index serves. Below the gate, pip 25.0.1 in the base and in the virtual environment, python-dotenv 1.2.1 and zlib `1.3.2-r0` carry fixable MEDIUM and LOW findings |
| shipping | Runtime base pinned by digest; libssl3t64 3.5.7-1~deb13u3 installed over the base from Debian's security archive, with its package record, until a distroless build carries it |
| frontend-proxy | Base moved from `envoyproxy/envoy:v1.34.14`, past its 2026-04-15 end of life and carrying four fixable HIGH findings in its own OpenSSL packages, to `v1.37.9` pinned by digest, supported until 2027-01-13 and carrying the fixed OpenSSL itself; the rendered `envoy.yaml` is byte-identical for both and passes `envoy --mode validate` on both. The build installs only `gettext-base` `0.21-4ubuntu4`, which provides `envsubst` and is the one version the jammy archive carries. It no longer installs `libssl3` and `openssl`, which on the old base upgraded them to whatever the index served on the day of the build; below the gate, the image's fixable MEDIUM and LOW findings drop from 117 to none. The configuration template is copied to `/etc/envoy`, owned by root with mode 644: in `/home/envoy`, which the envoy user owns, that user could append to, chmod, touch, rename and delete it. The entrypoint still renders `envoy.yaml` into `/home/envoy` at startup, so the image does not start on a read-only root filesystem, and it now `exec`s envoy, so a stop signal reaches envoy: `docker stop` returned in 0 s with exit code 0, where the shell left it 10 s and exit code 137. The runtime user is set numerically to 101:101, which chart 0.40.10 also sets. `EXPOSE` names port 8080 instead of the undefined `${ENVOY_PORT}`; the undefined `${ENVOY_ADMIN_PORT}` is dropped, since the admin port is 9901 in CI and 10000 in the chart, and the base's own `EXPOSE 10000` is inherited. Builds of the same tree agree on files, modes and owners except the apt and dpkg logs; their layer digests differ |

### Rejected modifications

| Change | Origin | Why it is not carried |
|---|---|---|
| `/p:NuGetAudit=false` on the `accounting` build | Prior bare-metal project | Disables the .NET dependency vulnerability audit. Suppressing a security check to make a build succeed is the pattern the exception policy exists to prevent. If the audit blocks the build, the answer is a recorded, time-bound exception, not a silent disable. |
| Per-service build context with the `./src/<name>/` prefix dropped | Prior bare-metal project | Cannot reach `pb/`, which seven components copy from. Superseded by the root context described above. |
| Scanner ignore baselines per language tier | Prior bare-metal project | Both baseline files carried zero active rules. A file that suppresses nothing while appearing to govern something is worse than no file. Created when there is a real exception to record. |

### Modification notice format

Each modified file carries this near the top, in the comment syntax the file already uses,
below the retained upstream copyright and SPDX headers:

```
# Modified from the upstream OpenTelemetry Demo release 2.2.0.
# Change: <what changed, one line>
```

Each newly changed file gains its notice in the same change that modifies it, and the table
above is updated in the same change, so the two never drift.

That rule was not followed six times. `9406cac` modified
`services/shipping/src/shipping_service.rs` without adding the notice or recording the file
above, and `1b4deb0` modified `services/quote/composer.json` without recording it above,
which matters more there because JSON has no comment syntax, so the table is the only place
that file can be recorded. `0463437`, `94eeedf`, `d2f3481`, and `30c556a` changed the
dependency metadata of product-catalog, frontend, payment and cart without recording it, and
`30c556a` also left `cart.csproj` without the notice its XML syntax can carry. Every one of
those gaps was found by comparing this record against the measured tree and is closed above. The rule itself is unchanged: a file whose syntax
supports a comment carries the notice, and dependency metadata that cannot appropriately
carry one is recorded in the non-container table instead.

## Language Tiers

Ten tiers were discovered by inspecting the pinned source, not inferred from the container
base images.

| Tier | Services | Evidence at the pinned tag | Pipeline template |
|---|---|---|---|
| Go | checkout, product-catalog | `go.mod` | `ci/templates/lang-go.yml`, carried |
| Node | frontend, payment | `package.json` | `ci/templates/lang-node.yml` |
| .NET | accounting, cart | `Accounting.csproj`, `cart.sln` | `ci/templates/lang-dotnet.yml`, net-new |
| Java | ad, fraud-detection | `build.gradle`, `build.gradle.kts` | `ci/templates/lang-java.yml`, net-new |
| Python | product-reviews, recommendation | `requirements.txt` | `ci/templates/lang-python.yml`, net-new |
| Rust | shipping | `Cargo.toml` | `ci/templates/lang-rust.yml` |
| Ruby | email | `Gemfile` | `ci/templates/lang-ruby.yml`, net-new |
| PHP | quote | `composer.json` | `ci/templates/lang-php.yml` |
| C++ | currency | `CMakeLists.txt` | `ci/templates/lang-cpp.yml`, net-new |
| Elixir | flagd-ui | `mix.exs` | `ci/templates/lang-elixir.yml`, net-new |

All ten tiers have a template today.

`frontend-proxy` and `image-provider` have no application language. They package an
upstream binary with project-owned configuration, so no language-tier template applies to
them.

## Available Tests

Only tests that actually exist upstream are listed. No test was written for this repository,
and no service is claimed to have coverage it does not have.

| Component | Test artefacts at the pinned tag | Kind |
|---|---|---|
| cart | `tests/CartServiceTests.cs`, `tests/cart.tests.csproj` | Unit, .NET, all three skipped upstream |
| checkout | `money/money_test.go` | Unit, Go, one package only |
| flagd-ui | `test/flagd_ui/storage_test.exs`, four controller tests under `test/flagd_ui_web/controllers/`, `test/test_helper.exs`, `config/test.exs` | Unit and controller, Elixir; the flag file `config/test.exs:30` reads is absent and ignored at the tag, so upstream's own `src/flagd/demo.flagd.json` is carried as test data and the eleven tests run |
| frontend | `cypress.config.ts` with `Dockerfile.cypress` | Browser test harness configuration |
| shipping | `#[cfg(test)]` module in `src/shipping_service.rs` | Unit, Rust |

Twelve of the seventeen components carry no tests at the pinned tag. The pipeline runs
whatever tests a service actually has and does not fabricate a test stage for the rest.

## Build Scripts and Manifests

No build script was written for this repository. Each component builds through its own
language toolchain, driven by the manifest upstream ships.

| Component | Manifest | Toolchain |
|---|---|---|
| accounting | `Accounting.csproj`, `Accounting.sln` | .NET SDK |
| ad | `build.gradle`, `settings.gradle`, `gradlew`, resolved under the project-generated `gradle.lockfile` | Gradle wrapper |
| cart | `cart.sln`, `src/cart.csproj`, `Directory.Build.props`, `NuGet.config` | .NET SDK |
| checkout | `go.mod` | Go |
| currency | `CMakeLists.txt` | CMake |
| email | `Gemfile` | Bundler |
| flagd-ui | `mix.exs` | Mix |
| fraud-detection | `build.gradle.kts`, `settings.gradle.kts`, resolved under the project-generated `gradle.lockfile` | Gradle, from the builder image; the committed wrapper is not used |
| frontend | `package.json` | npm |
| payment | `package.json` | npm |
| product-catalog | `go.mod` | Go |
| product-reviews | `requirements.txt`, installed under the project-generated `requirements.lock` | pip |
| quote | `composer.json` | Composer |
| recommendation | `requirements.txt`, installed under the project-generated `requirements.lock` | pip |
| shipping | `Cargo.toml` | Cargo |
| frontend-proxy | None | Configuration only, built by its container definition |
| image-provider | None | Configuration and static assets, built by its container definition |

## Delivery Pipeline

Services contribute declarative configuration only. Shared behaviour lives in
[ci/templates/](ci/templates/), and service-local pipeline logic requires a written
justification.

### Carried from the prior project

The pipeline structure originates in a prior bare-metal Kubernetes project by the same
author. It was reviewed against this repository rather than copied, and everything tied to
that environment was removed: runner tags, the runner hostname, the docker-socket-from-host
build pattern, the private GitLab DNS name, container labels naming that project, its
container registry, and a personal image namespace.

| Carried artefact | Origin | Why it is valid here |
|---|---|---|
| Stage order in `.gitlab-ci.yml` | Prior project root pipeline | Matches the stage sequence ADR-0009 requires and carries no environment assumption |
| `ci/templates/hadolint.yml` | Prior project | Reusable Dockerfile linting template for the delivery model. Extended by every wired service; its jobs have executed for the services wired before cart |
| `ci/templates/lang-go.yml` | Prior project | Module download, lint, and compile check. Runs today against checkout and product-catalog |
| `ci/templates/lang-node.yml` | Prior project | Dependency install, lint, and type check, carried and extended today by frontend alone. The type check runs after the lint in the same script, so it is reached only when the lint passes. The JavaScript parse template beside it is project-added rather than carried, because payment declares no static-analysis tooling for the carried template to run |
| `ci/templates/trivy-scan.yml` | Prior project | The two-pass order is the reason it is carried. Pass one always writes findings as an artifact and pass two applies the gate, so a blocked pipeline still leaves triage evidence behind |

### Four carried per-service definitions

| File | Component | Tier | Origin and justification |
|---|---|---|---|
| `services/checkout/ci.yml` | checkout | Go | Structure follows the prior project's per-service configuration contract. Carried because the Go tier template exists, so these jobs run |
| `services/product-catalog/ci.yml` | product-catalog | Go | Same contract. This component was one of two the prior project had onboarded, so this configuration pattern had already been exercised in the prior project |
| `services/frontend/ci.yml` | frontend | Node | Same contract. The other component the prior project had onboarded |
| `services/payment/ci.yml` | payment | Node | Same contract. Carried because the Node tier template exists. It extends the parse template rather than the lint and type-check one, because the service declares no linter |

Each declares `SERVICE_NAME`, `SERVICE_PATH`, and `LANG_TIER`. The prior project's
per-service files also carried `IMAGE_REPO` and `PROMOTE_REPO` pointing at its own registry
and a personal image namespace. Neither is carried, and no registry coordinate is written into these files: the
account-bearing host and the role arrive as masked CI variables instead. Where a service
has no repository in the platform registry, as `currency` does not, its publish and evidence
jobs stay unwired rather than pointing somewhere wrong. It is still wired through build and
scan, because neither stage touches the registry.

`frontend-proxy` and `image-provider` have no application language, and each carries a
per-service `ci.yml` regardless, because a container definition is enough to build, lint and
scan.

`services/cart/ci.yml` is net-new rather than carried, and is the only per-service file
that declares `SERVICE_DOCKERFILE`, because cart is the only component whose container
definition is not at its service root. `services/currency/ci.yml` and the C++ tier template
it extends, `ci/templates/lang-cpp.yml`, are net-new as well, as are
`services/product-reviews/ci.yml`, `services/recommendation/ci.yml` and the Python tier
template they extend, `ci/templates/lang-python.yml`, `services/email/ci.yml` with the Ruby
tier template, `ci/templates/lang-ruby.yml`, `services/flagd-ui/ci.yml` with the Elixir tier
template, `ci/templates/lang-elixir.yml`, and `services/ad/ci.yml` and
`services/fraud-detection/ci.yml` with the Java tier template, `ci/templates/lang-java.yml`.
`services/accounting/ci.yml` is net-new too and extends the .NET tier template unchanged. It
carries the pipeline's one service-local step, which copies `pb/demo.proto` to the path
`Accounting.csproj` compiles, and the file states why no shared template can hold it: cart,
the other .NET service, reads `pb/` from its own project file.

### Not implemented

ADR-0017 selects the full justified project-built inventory as the target of an
owner-selected end-to-end programme. Selection is not delivery. All six tiers that breadth adds, .NET, C++,
Python, Ruby, Elixir and Java, now have a template, and every project-built component is wired
to the pipeline. Recorded as not implemented:

- Image size budgets.

Net-new and now implemented, executed for checkout, shipping and quote, and since then for image-provider:

- The build stage, on hosted runners.
- Publication to the platform registry, federated pipeline credentials, and SBOM
  generation. None existed in the prior project.
- Container health validation.
- Automatic promotion by immutable digest. The deployment repository exists and already pins checkout, shipping and quote by digest, but every pin is a manual owner-reviewed change and nothing in this pipeline writes to it.
- Scanner ignore baselines, created when there is a real exception to record.

Promote is declared as a stage and left unpopulated so the order stays visible, because
promotion is a change to the GitOps repository rather than a pipeline job. Build is
populated for every wired service. Publish is populated for checkout, shipping, quote and
image-provider and configured for frontend-proxy, and no other service has published. No
placeholder job was created.

## Licensing and Attribution

The upstream Apache License 2.0 travels with the code as [LICENSE](LICENSE), copied
unchanged from the pinned tag. Upstream copyright and licence headers inside source files
are retained as they were written, above any modification notice.

No NOTICE file is included, because the pinned upstream release does not contain one. A
NOTICE was not created, since inventing one would misstate the upstream project's own
attribution requirements.

Trademark and branding are separate from copyright. The upstream licence does not grant
permission to use the project's name or logos, and no such use is claimed here.

This record states compliance obligations and the evidence gathered for them. It offers no
legal guarantee.

## Reproducing This Tree

From a clone of the upstream repository:

```
git clone https://github.com/open-telemetry/opentelemetry-demo
cd opentelemetry-demo
git checkout b74a7bc7bbe66099c61951f42b24dab8b6f02d18

for s in accounting ad cart checkout currency email flagd-ui fraud-detection \
         frontend image-provider payment product-catalog product-reviews \
         quote recommendation shipping frontend-proxy; do
  mkdir -p ../out/services/$s
  git archive 2.2.0 src/$s | tar -x -C ../out/services/$s --strip-components=2
done

mkdir -p ../out/pb
git archive 2.2.0 pb | tar -x -C ../out/pb --strip-components=1
git show 2.2.0:LICENSE > ../out/LICENSE
```

The comparison scope is `services/`, `pb/`, and `LICENSE`. Within that scope, comparing
`../out` against this tree reports two kinds of difference and nothing else. Forty-seven
upstream-derived files differ in content: the twenty-two container definitions recorded as
modified above, plus the twenty-five the preceding section records. Those twenty-five are
what separates this result from the twenty-two figure, which counts modified container
definitions only. The remaining three hundred and five upstream-derived files in the scope
are byte-identical, and no upstream file in the scope is missing here. Twenty-six files are
present here and absent upstream: the per-service `ci.yml` under `checkout`,
`product-catalog`, `frontend`, `payment`, `shipping`, `quote`, `frontend-proxy`,
`image-provider`, `cart`, `currency`, `product-reviews`, `recommendation`, `email`,
`flagd-ui`, `ad`, `fraud-detection`, and `accounting`;
`services/flagd-ui/test/fixtures/demo.flagd.json`, a verbatim copy of upstream's
`src/flagd/demo.flagd.json` at the pinned tag carried as test data;
`services/frontend/eslint.config.mjs`; and seven lock files,
`services/cart/src/packages.lock.json`, `services/accounting/packages.lock.json`,
`services/quote/composer.lock`, the pip-generated `requirements.lock` under
`services/product-reviews` and `services/recommendation`, and the Gradle-generated
`gradle.lockfile` under `services/ad` and `services/fraud-detection`, which give the source
gate a declared dependency set to read. Those twenty-six are project-added,
and the fixture is an unmodified upstream file, so no modification notice applies to any of
them. The flat ESLint configuration is project-added rather than a modification because
ESLint 9 reads flat configuration only and upstream ships none; the upstream `.eslintrc`
beside it is retained unmodified and still counts among the byte-identical files.

Those figures describe that comparison and nothing wider. Files outside `services/`, `pb/`,
and `LICENSE` are not part of it and are not classified by these counts.

Inside the same scope, the notice correspondence covers the modified upstream-derived
container definitions, `services/checkout/main.go`, `services/product-catalog/main.go`,
`services/shipping/src/shipping_service.rs`, the five modified `services/frontend/` source
files, `services/cart/src/cart.csproj`, `services/accounting/Accounting.csproj`,
`services/flagd-ui/mix.exs`, `services/ad/build.gradle`, and
`services/fraud-detection/build.gradle.kts`. Every one of
them that differs carries a modification notice, and every one carrying a notice differs. The
`go.mod`, `go.sum`, `composer.json`, `package.json`, `package-lock.json`, `Gemfile.lock`,
`.ruby-version` and `mix.lock` files are excluded for the reason given in the preceding
section, and the table there is what records them. That correspondence is the check worth
running, because it fails loudly if a change is made without recording it.
