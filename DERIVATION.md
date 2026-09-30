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

The consequence is that `COPY` source paths change from `src/<name>/` to `services/<name>/`
and nothing else about any build changes.

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
| `services/accounting/Dockerfile` | accounting | Path-only modified |
| `services/ad/Dockerfile` | ad | Path-only modified |
| `services/checkout/Dockerfile` | checkout | Path retarget, plus a runtime-stage `COPY` correction and the builder raised from `golang:1.24-bookworm` to a pinned `golang:1.25.13-bookworm` |
| `services/checkout/genproto/Dockerfile` | checkout | Path-only modified |
| `services/currency/genproto/Dockerfile` | currency | Path-only modified |
| `services/fraud-detection/Dockerfile` | fraud-detection | Path-only modified |
| **`services/frontend/Dockerfile`** | **frontend** | **Path plus hardening** |
| `services/frontend/genproto/Dockerfile` | frontend | Path-only modified |
| `services/frontend/Dockerfile.cypress` | frontend | Path-only modified |
| **`services/product-catalog/Dockerfile`** | **product-catalog** | **Path-only modified** |
| `services/product-catalog/genproto/Dockerfile` | product-catalog | Path-only modified |
| `services/quote/Dockerfile` | quote | Path plus hardening |
| `services/shipping/Dockerfile` | shipping | Path plus hardening |
| `services/product-reviews/genproto/Dockerfile` | product-reviews | Upstream unchanged |
| `services/recommendation/genproto/Dockerfile` | recommendation | Upstream unchanged |
| `services/cart/src/Dockerfile` | cart | Path plus hardening |
| `services/currency/Dockerfile` | currency | Path plus hardening |
| `services/email/Dockerfile` | email | Path plus hardening |
| `services/flagd-ui/Dockerfile` | flagd-ui | Path plus hardening |
| `services/payment/Dockerfile` | payment | Path plus hardening |
| `services/product-reviews/Dockerfile` | product-reviews | Path plus hardening |
| `services/recommendation/Dockerfile` | recommendation | Path plus hardening |
| `services/frontend-proxy/Dockerfile` | frontend-proxy | Configured component, path plus hardening |
| `services/image-provider/Dockerfile` | image-provider | Configured component, path plus hardening |
| No container definition upstream | flagd | Upstream exception |

One change to `services/accounting/Dockerfile` was reviewed and rejected. The file itself is
retained and appears once above, as path-only modified. The rejection is recorded under
rejected modifications below.

`frontend` and `product-catalog` keep the root build context. The prior bare-metal project
had adapted both to a per-service build context, dropping the `./src/<name>/` prefix
entirely. That adaptation is not carried, because it does not work for the seven components
that copy from `pb/`, and using two different context models across one fleet would make
the pipeline harder to share than the problem it solves.

### Modified upstream files that are not container definitions

The table above covers container definitions. Eighteen upstream-derived files under
`services/checkout/`, `services/product-catalog/`, `services/shipping/`,
`services/quote/`, `services/frontend/`, `services/payment/`, and `services/cart/` also differ
from the pinned source, and they
are recorded here so the modification inventory is not limited to container definitions. Those applications remain
upstream work. What follows are corrections and dependency movement applied on top of them,
not authorship of the services.

| File | Kind | Change measured against the pinned source |
|---|---|---|
| `services/checkout/main.go` | Application source | Three static-analysis corrections, each already stated in the file's own modification notice: `status.Errorf` replaced with `status.Error` where the message is a non-constant string, which `go vet` rejects as a non-constant format string; the error returned by `openfeature.SetProvider` explicitly discarded rather than silently dropped; and the receive from the Kafka `Successes()` channel no longer assigned to the blank identifier. Applied in `348490c`. |
| `services/checkout/go.mod` | Dependency and toolchain metadata | The `go` directive raised from `1.24.2` to `1.25.0`, direct dependencies advanced, and the indirect set re-resolved as a consequence, in `a384c3d` and `bf07e2e`. Later remediation in `14d12f3` advanced `google.golang.org/grpc` to `1.83.1`, `golang.org/x/crypto` to `0.55.0`, `golang.org/x/mod` to `0.40.0`, and the OpenTelemetry Go modules to `1.44.0`, with the consequential indirect movement that re-resolution produced. |
| `services/checkout/go.sum` | Dependency checksum metadata | Checksum metadata corresponding to the dependency changes recorded above. Applied in `a384c3d`, `bf07e2e`, and `14d12f3`. The earlier `a384c3d` and `bf07e2e` pair touched thirty-five distinct module paths. |
| `services/product-catalog/main.go` | Application source | One static-analysis correction, stated in the file's own modification notice: `status.Errorf` replaced with `status.Error` at the two call sites where the message is a non-constant string, which `go vet` rejects as a non-constant format string. The three remaining `status.Errorf` calls in the file pass constant format strings and are unchanged. Recorded in the same change that applies it, so no earlier commit is cited. |
| `services/product-catalog/go.mod` | Dependency and toolchain metadata | `0463437` raised the `go` directive from `1.24.2` to `1.25.0`, which the fixed module versions require; moved `github.com/open-feature/go-sdk-contrib/providers/flagd` from `v0.3.1` to `v0.4.0`, the lowest version that builds against the fixed flagd core; moved `google.golang.org/grpc` from `v1.78.0` to `v1.83.2` and `go.opentelemetry.io/otel` with its `sdk`, `sdk/metric` and `trace` modules from `v1.39.0` to `v1.44.0`; and promoted `go.opentelemetry.io/otel/metric` from an indirect to a direct `v1.44.0` requirement. The indirect set moved as re-resolution required. |
| `services/product-catalog/go.sum` | Dependency checksum metadata | Checksum metadata corresponding to the `go.mod` change above, applied in `0463437`. |
| `services/shipping/src/shipping_service.rs` | Application source | Byte-identical to the pinned release until `9406cac`, verified against the upstream blob. That change removed an unnecessary `as u32` cast on an item quantity that is already `u32`, and initialised the required `address` and `items` fields of the `ShipOrderRequest` test fixture, which the upstream literal left empty. |
| `services/quote/composer.json` | Dependency metadata | `1b4deb0` moved `guzzlehttp/guzzle` from `7.10.0` to `7.15.2` to clear the HIGH-severity finding the image scan reported against it, and changed nothing else at that time. `8bcc926` later moved `react/http` from `v1.11.0` to `v1.11.1` for CVE-2026-84997, a HIGH the blocking scan gate reported against a subsequent build. Each entry records the scan result of its own moment: the digest published before that second change was built from the earlier source and is not retrospectively remediated by it, and republishing quote and promoting the remediated digest are separate work that has not been done. |
| `services/frontend/pages/api/product-ask-ai-assistant/[productId]/index.ts` | Application source | The unused `AddItemRequest` import specifier removed. `Empty` is still imported from the same module, so the import statement and its side effects are unchanged. Recorded in the same change that applies it, so no earlier commit is cited. |
| `services/frontend/pages/api/product-reviews-avg-score/[productId]/index.ts` | Application source | The unused `ProductReview` import specifier removed, on the same basis: `Empty` is still imported from the same module. Recorded in the same change that applies it. |
| `services/frontend/providers/Ad.provider.tsx` | Application source | The unused `Money` import specifier removed. `Ad` and `Product` are still imported from the same module. Recorded in the same change that applies it. |
| `services/frontend/providers/ProductReview.provider.tsx` | Application source | The unused `useEffect` import specifier removed. The other three React imports are still used, so the import statement remains. Recorded in the same change that applies it. |
| `services/frontend/components/ProductReviews/ProductReviews.tsx` | Application source | `remainder` declared with `const` rather than `let`. It is assigned once and only read afterwards, so the change is behaviour-neutral. Recorded in the same change that applies it. |
| `services/frontend/package.json` | Dependency metadata | `94eeedf` moved six direct pins: `next` from `16.1.1` to `16.3.3`, `sharp` from `0.34.5` to `0.35.4`, `styled-components` from `6.2.0` to `6.4.0`, `@grpc/grpc-js` from `1.12.6` to `1.12.7`, `@opentelemetry/auto-instrumentations-node` from `0.67.3` to `0.78.0` and `@opentelemetry/sdk-node` from `0.208.0` to `0.220.0`. A later change moved `next` to `16.3.6` for GHSA-vcvr-r3jv-pc5j and `@grpc/grpc-js` to `1.13.6` for CVE-2026-101916, and `@openfeature/flagd-provider` from `0.13.3` to `0.13.4`, the first release whose peer range admits a fixed `@grpc/grpc-js`. |
| `services/frontend/package-lock.json` | Dependency lock metadata | Re-resolved by npm for those pins, in `94eeedf`, and again for the later ones, which move twelve entries and add or remove none. |
| `services/payment/package.json` | Dependency metadata | `d2f3481` moved three direct pins: `@grpc/grpc-js` from `1.12.6` to `1.12.7`, `@opentelemetry/auto-instrumentations-node` from `0.67.3` to `0.78.0` and `@opentelemetry/sdk-node` from `0.208.0` to `0.220.0`. A later change moved `@grpc/grpc-js` to `1.13.6` for CVE-2026-101916 and `@openfeature/flagd-provider` from `0.13.3` to `0.13.4`, the first release whose peer range admits it. |
| `services/payment/package-lock.json` | Dependency lock metadata | Re-resolved by npm for those pins, in `d2f3481`, and again for the later ones, which move two entries and add or remove none. |
| `services/cart/src/cart.csproj` | Dependency metadata | `30c556a` moved `OpenTelemetry.Resources.Host` from `1.14.0-beta.1` to `1.16.0-beta.2`, the first published version carrying the fix for GHSA-v8pv-4842-x354, and changed nothing else. |

Every dependency change above was made to move off modules a scan reported findings against:
the image scan, which is the reason recorded in `a384c3d`, `bf07e2e`, `14d12f3`, and `1b4deb0`;
the source gate, which is the reason recorded in `0463437`, `94eeedf`, `d2f3481`, and
`30c556a`; and both gates for the later frontend and payment moves. Neither the changes nor
this record claims any review of those dependencies beyond that.

Both `main.go` files, `shipping_service.rs`, the five `services/frontend/` source files and
`cart.csproj` above carry an Apache-2.0 modification notice in the format described below.
The `go.mod` and `go.sum` files, `composer.json`, and the `package.json` and
`package-lock.json` files carry none, and none is added. `go.sum` is a line-oriented checksum
list with no comment syntax, and the others apart from `go.mod` are strict JSON, which rejects
comments outright, so none of them can hold one. `go.mod` does support `//` comments, but
neither copy carries an upstream copyright or licence header for a notice to sit beneath, and
both are dependency metadata maintained by the Go toolchain rather than authored source. This
table is the record of their modification.

### Hardening applied, by component

| Component | Change beyond the path retargeting |
|---|---|
| cart | Base packages upgraded, application files owned by the built-in unprivileged user, container runs as that user |
| currency | Default pinned OpenTelemetry C++ version, dedicated unprivileged user, entrypoint corrected to an absolute path |
| email | Base packages upgraded |
| flagd-ui | Runtime base moved to Debian bookworm, newer OTP, packages upgraded, ncurses moved to the supported major version |
| image-provider | Packages upgraded in a temporary privileged stage, served content given explicit ownership and read permissions, returns to the unprivileged nginx user |
| frontend | Runtime base moved from `nodejs22-debian12` to `nodejs22-debian13` and pinned by digest; libssl3t64 3.5.7-1~deb13u3 installed over the base from Debian's security archive, with its package record, until a distroless build carries it |
| payment | Application files and dependencies owned by the unprivileged runtime user; runtime base moved from `nodejs22-debian12` to `nodejs22-debian13` and pinned by digest; libssl3t64 3.5.7-1~deb13u3 installed over the base from Debian's security archive, with its package record, until a distroless build carries it |
| product-reviews | Base packages upgraded, dependency install constrained to the committed `requirements.lock` |
| quote | Runtime base moved from `php:8.4-cli-alpine3.22`, which is no longer rebuilt, to `php:8.4-cli-alpine3.23` pinned by digest, whose own packages carry the fixes the image scan requires; extension installer raised to 2.9.22, pinned by digest, for Alpine 3.23 support |
| recommendation | TLS libraries and libuuid upgraded, application directories given explicit read permissions, dependency install constrained to the committed `requirements.lock` |
| shipping | Runtime base pinned by digest; libssl3t64 3.5.7-1~deb13u3 installed over the base from Debian's security archive, with its package record, until a distroless build carries it |
| frontend-proxy | Base image pinned to an immutable digest, package installation narrowed, TLS libraries added, configuration template given explicit ownership and read-only permissions |

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
| Java | ad, fraud-detection | `build.gradle`, `build.gradle.kts` | Net-new |
| Python | product-reviews, recommendation | `requirements.txt` | `ci/templates/lang-python.yml`, net-new |
| Rust | shipping | `Cargo.toml` | `ci/templates/lang-rust.yml` |
| Ruby | email | `Gemfile` | Net-new |
| PHP | quote | `composer.json` | `ci/templates/lang-php.yml` |
| C++ | currency | `CMakeLists.txt` | `ci/templates/lang-cpp.yml`, net-new |
| Elixir | flagd-ui | `mix.exs` | Net-new |

Seven tiers of ten have a template today. The other three have none. ADR-0017 selects the
full justified project-built inventory as the programme target, so those three tiers are
selected work; no schedule for them is claimed here.

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
| flagd-ui | `test/flagd_ui/storage_test.exs`, four controller tests under `test/flagd_ui_web/controllers/`, `test/test_helper.exs`, `config/test.exs` | Unit and controller, Elixir |
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
| ad | `build.gradle` | Gradle |
| cart | `cart.sln`, `src/cart.csproj`, `Directory.Build.props`, `NuGet.config` | .NET SDK |
| checkout | `go.mod` | Go |
| currency | `CMakeLists.txt` | CMake |
| email | `Gemfile` | Bundler |
| flagd-ui | `mix.exs` | Mix |
| fraud-detection | `build.gradle.kts`, `settings.gradle.kts`, `gradlew` | Gradle wrapper |
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

Five components have no per-service configuration. Four of them have a language tier with
no template; accounting is the exception, because the .NET tier now has one and accounting
is not yet wired to it. `frontend-proxy` and `image-provider` have no application
language, and each carries a per-service `ci.yml` regardless, because a container
definition is enough to build, lint and scan.

`services/cart/ci.yml` is net-new rather than carried, and is the only per-service file
that declares `SERVICE_DOCKERFILE`, because cart is the only component whose container
definition is not at its service root. `services/currency/ci.yml` and the C++ tier template
it extends, `ci/templates/lang-cpp.yml`, are net-new as well, as are
`services/product-reviews/ci.yml`, `services/recommendation/ci.yml` and the Python tier
template they extend, `ci/templates/lang-python.yml`.

### Not implemented

ADR-0017 selects the full justified project-built inventory as the target of an
owner-selected end-to-end programme. Selection is not delivery, and .NET, C++ and Python are the
only tiers of that breadth implemented so far, so the following are recorded as not
implemented:

- Language-tier templates for Java, Ruby, and Elixir.
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
`../out` against this tree reports two kinds of difference and nothing else. Forty
upstream-derived files differ in content: the twenty-two container definitions recorded as
modified above, plus the eighteen the preceding section records. Those eighteen are what
separates this result from the twenty-two figure, which counts modified container
definitions only. The remaining three hundred and twelve upstream-derived files in the
scope are byte-identical, and no upstream file in the scope is missing here. Seventeen files
are present here and absent upstream: the per-service `ci.yml` under `checkout`,
`product-catalog`, `frontend`, `payment`, `shipping`, `quote`, `frontend-proxy`,
`image-provider`, `cart`, `currency`, `product-reviews`, and `recommendation`;
`services/frontend/eslint.config.mjs`; and four lock files, `services/cart/src/packages.lock.json`,
`services/quote/composer.lock` and the pip-generated `requirements.lock` under
`services/product-reviews` and `services/recommendation`, which exist so the source gate has a
declared dependency set to read. Those seventeen are project-added with no upstream origin, so
no modification notice applies to them. The flat ESLint configuration is project-added rather
than a modification because ESLint 9 reads flat configuration only and upstream ships none; the upstream
`.eslintrc` beside it is retained unmodified and still counts among the byte-identical
files.

Those figures describe that comparison and nothing wider. Files outside `services/`, `pb/`,
and `LICENSE` are not part of it and are not classified by these counts.

Inside the same scope, the notice correspondence covers the modified upstream-derived
container definitions, `services/checkout/main.go`, `services/product-catalog/main.go`,
`services/shipping/src/shipping_service.rs`, the five modified `services/frontend/` source
files, and `services/cart/src/cart.csproj`. Every one of them that differs carries a
modification notice, and every one carrying a notice differs. The `go.mod`, `go.sum`,
`composer.json`, `package.json` and `package-lock.json` files are excluded for the reason
given in the preceding section, and the table there is what records them. That correspondence is the check worth running, because it
fails loudly if a change is made without recording it.
