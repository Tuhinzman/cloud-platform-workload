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
| flagd | `src/flagd` | No container definition at the pinned tag, verified. Deployed as a justified upstream exception rather than built here. |
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
| **`services/frontend/Dockerfile`** | **frontend** | **Path-only modified** |
| `services/frontend/genproto/Dockerfile` | frontend | Path-only modified |
| `services/frontend/Dockerfile.cypress` | frontend | Path-only modified |
| **`services/product-catalog/Dockerfile`** | **product-catalog** | **Path-only modified** |
| `services/product-catalog/genproto/Dockerfile` | product-catalog | Path-only modified |
| `services/quote/Dockerfile` | quote | Path plus hardening |
| `services/shipping/Dockerfile` | shipping | Path-only modified |
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

`frontend` and `product-catalog` carry the path change only. The prior bare-metal project
had adapted both to a per-service build context, dropping the `./src/<name>/` prefix
entirely. That adaptation is not carried, because it does not work for the seven components
that copy from `pb/`, and using two different context models across one fleet would make
the pipeline harder to share than the problem it solves.

### Modified upstream files that are not container definitions

The table above covers container definitions. Eleven upstream-derived files under
`services/checkout/`, `services/product-catalog/`, `services/shipping/`,
`services/quote/`, and `services/frontend/` also differ from the pinned source, and they
are recorded here so the modification inventory is not limited to container definitions. Those applications remain
upstream work. What follows are corrections and dependency movement applied on top of them,
not authorship of the services.

| File | Kind | Change measured against the pinned source |
|---|---|---|
| `services/checkout/main.go` | Application source | Three static-analysis corrections, each already stated in the file's own modification notice: `status.Errorf` replaced with `status.Error` where the message is a non-constant string, which `go vet` rejects as a non-constant format string; the error returned by `openfeature.SetProvider` explicitly discarded rather than silently dropped; and the receive from the Kafka `Successes()` channel no longer assigned to the blank identifier. Applied in `348490c`. |
| `services/checkout/go.mod` | Dependency and toolchain metadata | The `go` directive raised from `1.24.2` to `1.25.0`, direct dependencies advanced, and the indirect set re-resolved as a consequence, in `a384c3d` and `bf07e2e`. Later remediation in `14d12f3` advanced `google.golang.org/grpc` to `1.83.1`, `golang.org/x/crypto` to `0.55.0`, `golang.org/x/mod` to `0.40.0`, and the OpenTelemetry Go modules to `1.44.0`, with the consequential indirect movement that re-resolution produced. |
| `services/checkout/go.sum` | Dependency checksum metadata | Checksum metadata corresponding to the dependency changes recorded above. Applied in `a384c3d`, `bf07e2e`, and `14d12f3`. The earlier `a384c3d` and `bf07e2e` pair touched thirty-five distinct module paths. |
| `services/product-catalog/main.go` | Application source | One static-analysis correction, stated in the file's own modification notice: `status.Errorf` replaced with `status.Error` at the two call sites where the message is a non-constant string, which `go vet` rejects as a non-constant format string. The three remaining `status.Errorf` calls in the file pass constant format strings and are unchanged. Recorded in the same change that applies it, so no earlier commit is cited. |
| `services/shipping/src/shipping_service.rs` | Application source | Byte-identical to the pinned release until `9406cac`, verified against the upstream blob. That change removed an unnecessary `as u32` cast on an item quantity that is already `u32`, and initialised the required `address` and `items` fields of the `ShipOrderRequest` test fixture, which the upstream literal left empty. |
| `services/quote/composer.json` | Dependency metadata | `1b4deb0` moved `guzzlehttp/guzzle` from `7.10.0` to `7.15.2` to clear the HIGH-severity finding the image scan reported against it. No other dependency changed. |
| `services/frontend/pages/api/product-ask-ai-assistant/[productId]/index.ts` | Application source | The unused `AddItemRequest` import specifier removed. `Empty` is still imported from the same module, so the import statement and its side effects are unchanged. Recorded in the same change that applies it, so no earlier commit is cited. |
| `services/frontend/pages/api/product-reviews-avg-score/[productId]/index.ts` | Application source | The unused `ProductReview` import specifier removed, on the same basis: `Empty` is still imported from the same module. Recorded in the same change that applies it. |
| `services/frontend/providers/Ad.provider.tsx` | Application source | The unused `Money` import specifier removed. `Ad` and `Product` are still imported from the same module. Recorded in the same change that applies it. |
| `services/frontend/providers/ProductReview.provider.tsx` | Application source | The unused `useEffect` import specifier removed. The other three React imports are still used, so the import statement remains. Recorded in the same change that applies it. |
| `services/frontend/components/ProductReviews/ProductReviews.tsx` | Application source | `remainder` declared with `const` rather than `let`. It is assigned once and only read afterwards, so the change is behaviour-neutral. Recorded in the same change that applies it. |

Every dependency change above was made to move off modules the image scan reported
findings against, which is the reason recorded in `a384c3d`, `bf07e2e`, `14d12f3`, and
`1b4deb0`. Neither the changes nor this record claims any review of those dependencies
beyond that.

Both `main.go` files, `shipping_service.rs`, and the five `services/frontend/` files above
carry an Apache-2.0 modification notice in the format described below. `go.mod`, `go.sum`, and `composer.json` carry none, and none is
added. `go.sum` is a line-oriented checksum list with no comment syntax, and `composer.json`
is strict JSON, which rejects comments outright, so neither can hold one. `go.mod` does
support `//` comments, but like the other two it carries no upstream copyright or licence
header for a notice to sit beneath, and all three are dependency metadata maintained by
their resolvers rather than authored source. This table is the record of their modification.

### Hardening applied, by component

| Component | Change beyond the path retargeting |
|---|---|
| cart | Base packages upgraded, application files owned by the built-in unprivileged user, container runs as that user |
| currency | Default pinned OpenTelemetry C++ version, dedicated unprivileged user, entrypoint corrected to an absolute path |
| email | Base packages upgraded |
| flagd-ui | Runtime base moved to Debian bookworm, newer OTP, packages upgraded, ncurses moved to the supported major version |
| image-provider | Packages upgraded in a temporary privileged stage, served content given explicit ownership and read permissions, returns to the unprivileged nginx user |
| payment | Application files and dependencies owned by the unprivileged runtime user |
| product-reviews | Base packages upgraded |
| quote | Vulnerable runtime packages pinned to measured fixed revisions rather than upgraded broadly |
| recommendation | TLS libraries upgraded, application directories given explicit read permissions |
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

That rule was not followed twice. `9406cac` modified
`services/shipping/src/shipping_service.rs` without adding the notice or recording the file
above, and `1b4deb0` modified `services/quote/composer.json` without recording it above,
which matters more there because JSON has no comment syntax, so the table is the only place
that file can be recorded. Both gaps were found by comparing this record against the
measured tree and are closed above. The rule itself is unchanged: a file whose syntax
supports a comment carries the notice, and dependency metadata that cannot appropriately
carry one is recorded in the non-container table instead.

## Language Tiers

Ten tiers were discovered by inspecting the pinned source, not inferred from the container
base images.

| Tier | Services | Evidence at the pinned tag | Pipeline template |
|---|---|---|---|
| Go | checkout, product-catalog | `go.mod` | `ci/templates/lang-go.yml`, carried |
| Node | frontend, payment | `package.json` | `ci/templates/lang-node.yml` |
| .NET | accounting, cart | `Accounting.csproj`, `cart.sln` | Net-new |
| Java | ad, fraud-detection | `build.gradle`, `build.gradle.kts` | Net-new |
| Python | product-reviews, recommendation | `requirements.txt` | Net-new |
| Rust | shipping | `Cargo.toml` | Net-new |
| Ruby | email | `Gemfile` | Net-new |
| PHP | quote | `composer.json` | Net-new |
| C++ | currency | `CMakeLists.txt` | Net-new |
| Elixir | flagd-ui | `mix.exs` | Net-new |

Two tiers of ten have a template today. Eight are net-new work.

`frontend-proxy` and `image-provider` have no application language. They package an
upstream binary with project-owned configuration, so no language-tier template applies to
them.

## Available Tests

Only tests that actually exist upstream are listed. No test was written for this repository,
and no service is claimed to have coverage it does not have.

| Component | Test artefacts at the pinned tag | Kind |
|---|---|---|
| cart | `tests/CartServiceTests.cs`, `tests/cart.tests.csproj` | Unit, .NET |
| checkout | `money/money_test.go` | Unit, Go, one package only |
| flagd-ui | `test/flagd_ui/storage_test.exs`, four controller tests under `test/flagd_ui_web/controllers/`, `test/test_helper.exs`, `config/test.exs` | Unit and controller, Elixir |
| frontend | `cypress.config.ts` with `Dockerfile.cypress` | Browser test harness configuration |

Thirteen of the seventeen components carry no tests at the pinned tag. The pipeline runs
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
| product-reviews | `requirements.txt` | pip |
| quote | `composer.json` | Composer |
| recommendation | `requirements.txt` | pip |
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
| `ci/templates/hadolint.yml` | Prior project | Reusable Dockerfile linting template for the delivery model. Not yet extended by a job, so it does not execute today |
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

Each declares `SERVICE_NAME`, `SERVICE_PATH`, and `LANG_TIER` only. The prior project's
per-service files also carried `IMAGE_REPO` and `PROMOTE_REPO` pointing at its own registry
and a personal image namespace. Neither is carried, and no registry coordinate is invented
in their place, so the scan job stays inactive rather than pointing somewhere wrong.

Thirteen components have no per-service configuration yet, because their language tier has
no template.

### Deferred work

Net-new implementation with nothing to carry forward:

- Language-tier templates for .NET, Java, Python, Rust, Ruby, PHP, C++, and Elixir.
- The build stage. The runner executor model is undecided, and the prior project's approach
  depended on infrastructure assumptions that do not transfer.
- Publication to the platform registry, federated pipeline credentials, and SBOM
  generation. None existed in the prior project.
- Promotion by immutable digest, which needs a deployment repository that does not exist.
- Container health validation and image size budgets, which need built images.
- Scanner ignore baselines, created when there is a real exception to record.

Build, publish, and promote are declared as stages and left unpopulated so the order stays
visible. No placeholder job was created.

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
`../out` against this tree reports two kinds of difference and nothing else. Thirty-three
upstream-derived files differ in content: the twenty-two container definitions recorded as
modified above, plus the eleven the preceding section records. Those eleven are what
separates this result from the twenty-two figure, which counts modified container
definitions only. The remaining three hundred and nineteen upstream-derived files in the
scope are byte-identical, and no upstream file in the scope is missing here. Seven files
are present here and absent upstream: the per-service `ci.yml` under `checkout`,
`product-catalog`, `frontend`, `payment`, `shipping`, and `quote`, and
`services/frontend/eslint.config.mjs`. Those seven are project-added configuration with
no upstream origin, so no modification notice applies to them. The flat ESLint
configuration is project-added rather than a modification because ESLint 9 reads flat
configuration only and upstream ships none; the upstream `.eslintrc` beside it is
retained unmodified and still counts among the byte-identical files.

Those figures describe that comparison and nothing wider. Files outside `services/`, `pb/`,
and `LICENSE` are not part of it and are not classified by these counts.

Inside the same scope, the notice correspondence covers the modified upstream-derived
container definitions, `services/checkout/main.go`, `services/product-catalog/main.go`,
`services/shipping/src/shipping_service.rs`, and the five modified `services/frontend/`
files. Every one of them that differs carries a
modification notice, and every one carrying a notice differs. `go.mod`, `go.sum`, and
`composer.json` are excluded for the reason given in the preceding section, and the table
there is what records them. That correspondence is the check worth running, because it
fails loudly if a change is made without recording it.
