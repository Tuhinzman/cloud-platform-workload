# Service Inventory

Per-component evidence for the workload fleet. This is the single copy: the platform reference
repository links here instead of holding a second table, because two copies of a status table
drift apart.

## Current Status

All seventeen container definitions were hardened and merged through GitLab merge requests !44
to !54 between 2026-10-13 and 2026-10-16, each after its merge-request pipeline passed. That
overall pipeline status is the only result recorded for the hardened definitions. No job log,
scan report or SBOM artifact from those pipelines has been inspected, and no hardened image is
recorded as published, pinned in the deployment repository or run. These are workload images:
ADR-0009 and ADR-0014 govern them, and ADR-0015 governs platform-managed runtime components.

Every other result in this file belongs to an image built before its definition was hardened:

- checkout, shipping and quote were built, scanned, published with an SBOM, read back from the
  registry by digest, and exercised inside bounded EKS runtime windows.
- image-provider was built, scanned, published with an SBOM and read back from the registry by
  digest. It has no runtime evidence, because no runtime window has included it.
- An earlier frontend-proxy image was published on 2026-09-26 and its digest read back from the
  registry. It has no runtime evidence.
- The other twelve components have CI results only. None of them has published anything or run.

Two publications carry a provenance bundle the pipeline retained itself, shipping first and then
image-provider. The five images published later from one pipeline each carry one too. The
checkout, shipping, quote and image-provider bundles passed verification; frontend-proxy's did
not, so it is not counted as provenance.

Wiring is not execution, publication is not runtime evidence, and none of this is fleet-wide
delivery. Identity and classification are facts about the source and are recorded independently
of that evidence.

## Inventory

Five classes. Every component belongs to exactly one, and the class decides what evidence it
owes.

| Class | Components |
|---|---|
| 1. Project-built application services | accounting, ad, cart, checkout, currency, email, flagd-ui, fraud-detection, frontend, payment, product-catalog, product-reviews, quote, recommendation, shipping |
| 2. Project-built configured components | frontend-proxy, image-provider |
| 3. Justified upstream exceptions | flagd |
| 4. Infrastructure dependencies | message broker, cache, durable datastore |
| 5. Not deployed | load-generator, the workload bundled observability stack, the workload own collector, llm, react-native-app |

The seventeen components in classes 1 and 2 are built here. "Hardened in" is the merge request
that merged the current container definition. Every other column describes the image built
before that change.

| Component | Class | Hardened in | Build, scan, SBOM | Container health in CI | Publication | EKS runtime |
|---|---|---|---|---|---|---|
| checkout | 1 | !44 | Yes | Validated | Published, provenance verified | Bounded windows |
| shipping | 1 | !53 | Yes | Validated | Published, provenance verified | Bounded windows |
| quote | 1 | !47 | Yes | Validated | Published, provenance verified | Bounded windows |
| image-provider | 2 | !48 | Yes | Validated | Published, provenance verified | None |
| frontend-proxy | 2 | !49 | Yes | Validated | Earlier image, 2026-09-26; its bundle failed verification | None |
| payment | 1 | !45 | Yes | Validated | None; manual publish and evidence jobs on main | None |
| frontend | 1 | !46 | Yes | Validated | None; manual publish and evidence jobs on main | None |
| cart | 1 | !50 | Yes | Validated against a Valkey fixture | None | None |
| product-catalog | 1 | !44 | Yes | Validated against a PostgreSQL fixture | None; no publication jobs | None |
| currency | 1 | !53 | Yes | Validated | No publication stage | None |
| product-reviews | 1 | !50 | Yes | Validated | No publication stage | None |
| recommendation | 1 | !50 | Yes | Validated | No publication stage | None |
| email | 1 | !52 | Yes | Validated | No publication stage | None |
| ad | 1 | !51 | Yes | Validated | No publication stage | None |
| fraud-detection | 1 | !51 | Yes | Running check, not functional health | No publication stage | None |
| accounting | 1 | !52 | Yes | Running check, not functional health | No publication stage | None |
| flagd-ui | 1 | !54 | Yes, with its eleven upstream tests | Deferred to runtime | No publication stage | None |

## How to Read the Evidence

Each kind of evidence shows one thing and is never counted as another.

| Evidence | Meaning in this file |
|---|---|
| Merge-request pipeline passed | The pipeline for the hardened definition passed. Its job logs, scan reports and SBOM artifacts have not been inspected. |
| Build, scan, SBOM | CI built the image, scanned it and produced an SBOM. "Both security gates" means the image gate and the source dependency gate. |
| Container health | A CI check that the image starts and listens, or that a worker stays up. See Container Health Disposition below. |
| Publication | The image was published to the registry and its digest read back. Publication is not runtime evidence. |
| Provenance | A bundle the pipeline retained for a published image passed verification. A bundle that failed is not counted. |
| Governing records | ADR-0009 sets the security gate, the SBOM, digest identity and promotion for these images, and ADR-0014 extends the same threshold to justified upstream workload components. ADR-0015 admission applies only to platform-managed runtime components. |
| EKS runtime | The image ran inside a bounded EKS runtime window. |

## 1. Project-Built Application Services

Derived from upstream application source and built here through this project's pipeline. The
application source is upstream work. This project owns the container definition, the hardening,
the pipeline and the evidence.

| Component | Language tier | Upstream path at tag `2.2.0` | Container definition | Tests present upstream |
|---|---|---|---|---|
| accounting | .NET | `src/accounting` | Path plus hardening | None |
| ad | Java | `src/ad` | Path plus hardening | None |
| cart | .NET | `src/cart` | Path plus hardening | Unit, `tests/CartServiceTests.cs`, all skipped upstream |
| checkout | Go | `src/checkout` | Project-maintained since 2026-10-13 | Unit, `money/money_test.go` |
| currency | C++ | `src/currency` | Path plus hardening | None |
| email | Ruby | `src/email` | Path plus hardening | None |
| flagd-ui | Elixir | `src/flagd-ui` | Path plus hardening | Unit and controller, seven files |
| fraud-detection | Java | `src/fraud-detection` | Path plus hardening | None |
| frontend | Node | `src/frontend` | Path plus hardening | Cypress harness configuration |
| payment | Node | `src/payment` | Path plus hardening | None |
| product-catalog | Go | `src/product-catalog` | Project-maintained since 2026-10-13 | None |
| product-reviews | Python | `src/product-reviews` | Path plus hardening | None |
| quote | PHP | `src/quote` | Path plus hardening | None |
| recommendation | Python | `src/recommendation` | Path plus hardening | None |
| shipping | Rust | `src/shipping` | Path plus hardening | None |

### Language Tiers

Ten tiers, discovered by inspecting pinned source rather than inferred from base images.

| Tier | Services | Pipeline template |
|---|---|---|
| Go | checkout, product-catalog | `ci/templates/lang-go.yml`, carried |
| Node | frontend, payment | `ci/templates/lang-node.yml` |
| .NET | accounting, cart | `ci/templates/lang-dotnet.yml`, net-new |
| Java | ad, fraud-detection | `ci/templates/lang-java.yml`, net-new |
| Python | product-reviews, recommendation | `ci/templates/lang-python.yml`, net-new |
| Rust | shipping | `ci/templates/lang-rust.yml`, net-new |
| Ruby | email | `ci/templates/lang-ruby.yml`, net-new |
| PHP | quote | `ci/templates/lang-php.yml`, net-new |
| C++ | currency | `ci/templates/lang-cpp.yml`, net-new |
| Elixir | flagd-ui | `ci/templates/lang-elixir.yml`, net-new |

All ten tiers have a template, and all fifteen services are wired to the pipeline. Seventeen
components are wired in total, counting the two configured components in class 2.

ADR-0017 selects the full justified project-built inventory as the target of an owner-selected
end-to-end programme; wiring it is not delivering it. Of the programme's six language tiers,
.NET was implemented first, then C++, Python, Ruby, Elixir and Java. Nothing here says those
components are delivered.

Language checks differ in depth:

- payment declares no linter and no TypeScript, so its Node job checks only that every `.js`
  file in the service directory parses.
- product-reviews and recommendation check that each committed `requirements.lock` still
  reproduces the dependency install.
- frontend's ESLint job, on a project-added flat configuration, reported zero errors and twelve
  unremediated warnings in its last recorded validated run on main.

## 2. Project-Built Configured Components

A container definition and project-owned configuration, with no upstream application source
behind it. Built here, so each carries a build record, an SBOM and its own validation. No
application provenance is claimed, and no language tier applies.

| Component | What it packages | Upstream path at tag `2.2.0` | Container definition |
|---|---|---|---|
| frontend-proxy | Envoy binary with a project configuration template | `src/frontend-proxy` | Path plus hardening |
| image-provider | nginx binary with a project configuration template and static assets | `src/image-provider` | Path plus hardening |

Both were confirmed against pinned source. The provisional classification listed
`image-provider` among the application services; inspection shows its directory holds a
container definition, an nginx configuration template and static assets with no application
code, the same shape as `frontend-proxy`.

## 3. Justified Upstream Exceptions

Deployed but not built here. Under ADR-0012, an upstream exception is pinned by digest, mirrored
into the platform registry so that no pod start depends on an external service, and scanned
there under the same threshold that gates built services. It carries no build provenance, and
that limit is stated rather than implied.

That is the required handling, not a record of what has happened. None of those controls has
been executed for flagd: it is not mirrored, not scanned, carries no project-owned digest, and
is disabled in the only environment that has run.

| Component | Why not built here | Condition to remove |
|---|---|---|
| flagd | No container definition exists at the pinned tag, verified | Upstream adds one, or the feature-control path is served by a component built here |

Full justification is in [UPSTREAM-EXCEPTIONS.md](UPSTREAM-EXCEPTIONS.md).

## 4. Infrastructure Dependencies

Required by the application but not application services. For the message broker and the cache,
the deployment form is an open implementation decision with its own cost gate, so no form is
recorded. The durable datastore has an implemented Dev configuration, which is not running now.

| Component | Role | Form |
|---|---|---|
| Message broker | Carries the asynchronous producer to consumer path | Undecided. In-cluster or managed. |
| Cache | Sits behind the cart | Undecided. In-cluster or managed. |
| Durable datastore | Holds data that must outlive its environment | Amazon RDS for PostgreSQL 17.11, a managed service with native backup, implemented for Dev in the reference repository's `terraform/dev-datastore`. The instance was decommissioned on 2026-10-06 and has not been recreated, and no workload ever connected to it. Its final snapshot is retained; restoring from it has not been validated. |

## 5. Not Deployed

Absent from every environment. A component excluded from the fleet is not an upstream exception;
it simply does not run.

| Component | Why |
|---|---|
| load-generator | Not deployed. Runs as root and carries a large volume of unfixed operating-system findings, and proves no platform capability the rest of the fleet does not. May be enabled inside a bounded, owner-approved validation window and is otherwise absent. |
| Workload bundled observability stack | Observability belongs to the platform, and duplicate collection is waste |
| Workload own collector | Telemetry reaches the platform gateway only |
| llm | Not part of a justified application path |
| react-native-app | Not part of a justified application path |

## Container Health Disposition

Fourteen of the seventeen wired components prove container health in CI. fraud-detection and
accounting never listen, so they have no port to prove. flagd-ui's health is deferred to
runtime, and a deferred entry is not a pass and not runtime evidence.

Every port probe first starts a container that listens on nothing on the same port and must read
it as closed. Where a proxy answers for published ports, the job fails instead of passing a
service it cannot prove.

Two components reach their listening state only after a startup dependency answers, so their
health job starts that dependency beside them as a digest-pinned fixture on a job-private
network. That proves the image starts against the dependency it needs. It is not runtime
readiness, and the readiness obligation stays open until a runtime window answers it. The
fixtures take no credential and no data, and they are not the runtime dependency: cart's cache
form and product-catalog's managed database are separate decisions.

A worker that never listens is checked in a running mode that proves only that the process stays
up for a bounded time, beside a control that aborts itself at once. Both run under an init
process, because as PID 1 a process that aborts, as .NET does on an unhandled exception, is left
running rather than exited. fraud-detection and accounting are the two components in that mode.

| Component | Container health |
|---|---|
| checkout, quote, shipping, frontend-proxy, image-provider, payment, frontend, currency, product-reviews, recommendation, email, ad | validated in CI |
| cart | validated in CI against an ephemeral fixture: Valkey 9.0.1 from the upstream chart, because `Program.cs:98` resolves ValkeyCartStore before `app.Run()` and `ValkeyCartStore.cs:101` throws without it |
| product-catalog | validated in CI against an ephemeral fixture: PostgreSQL 17.11, the Dev datastore's engine version, with trust authentication and no schema, because `main()` calls `initDatabase()` before the listener and exits 1 without it |
| flagd-ui | deferred to runtime: `application.ex:20` starts `FlagdUi.Storage` before the endpoint and `storage.ex:23` reads `/app/data/demo.flagd.json`, which its pod mounts, so without that file the release exits 1 before listening |
| fraud-detection | running in CI, not functional health: `main.kt` polls Kafka in a loop and opens no server socket, so there is no port to probe; given a `KAFKA_ADDR` that resolves with no broker behind it, the process must stay up for 30 s, and without the variable, or with an unresolvable address, it exits 1 and the job fails |
| accounting | running in CI, not functional health: `Program.cs:14` builds a host with no server and `Consumer.cs:66` blocks in the Kafka consume loop, so there is no port to probe; given an unresolvable `KAFKA_ADDR` the process retries and must stay up for 30 s, and without the variable `Consumer.cs:42` throws and the job fails. Measured: without an init that exception leaves the process running as PID 1 rather than exited |

What two of the validated results do not cover:

- payment binds its gRPC port before anything external is needed, so its container health is a
  real result rather than an exception. Its Charge handler reaches flagd per request, so the
  application path beyond the health service is not validated in CI.
- frontend also returned HTTP 200 with rendered HTML and served the `/_next/` assets that page
  referenced. That is a bounded startup and static-asset result, not a check of any backend call
  it would make.

## Dependency Scanning Coverage

ADR-0009 asks one scanner to cover image *and* dependency scanning. Those are two views, and
measurement on this fleet shows neither one contains the other, so the pipeline runs both and
neither is recorded as evidence for the other.

What the image scan sees depends on what the build leaves legible in the image, and that varies
by language rather than by packaging. Measured on the images built before the hardening:

| Component | Tier | Managed deps in the image SBOM | Packages the source pass resolves |
|---|---|---|---|
| checkout | Go | 73, from the module graph inside the binary | 74, from `go.mod` |
| quote | PHP | 52, from the vendor directory | 52, from `composer.lock` |
| shipping | Rust | none: 14 OS packages only | 237, from `Cargo.lock` |
| cart | .NET | none: 18 OS packages only | 41, from `packages.lock.json` |
| payment | Node | 314, from the installed `node_modules` tree | 254, from `package-lock.json` |
| frontend | Node | 489, from the installed `node_modules` tree | 322, from `package-lock.json` |
| product-catalog | Go | 57, from the module graph inside the binary | 58, from `go.mod` |
| frontend-proxy | Envoy config | no application dependencies exist | none, declared |
| image-provider | nginx + assets | no application dependencies exist | none, declared |
| currency | C++ | none: OS packages only; the compiled-in opentelemetry-cpp is not visible | none, declared |
| product-reviews | Python | 62, from the installed venv and the base image's pip | 71: 60 from `requirements.lock`, 11 from `requirements.txt` |
| recommendation | Python | 40, from the installed venv and the base image's pip | 46: 38 from `requirements.lock`, 8 from `requirements.txt` |
| email | Ruby | the bundle's gems and the gems shipped with Ruby, read from their gemspecs | 90, from `Gemfile.lock` |
| flagd-ui | Elixir | none: Debian packages only; the Hex dependencies and the bundled OTP runtime are not visible | 54, from `mix.lock` |
| ad | Java | 70 Maven, from the installed jars and the OpenTelemetry agent | 78, from `gradle.lockfile` |
| fraud-detection | Java | 46 Maven: the 45 whose metadata is inside the shadow jar, and the OpenTelemetry agent | 102, from `gradle.lockfile` |
| accounting | .NET | 48 NuGet, from the application's and the shared runtime's `.deps.json` | 67, from `packages.lock.json` |

Four of the seventeen carry no managed dependency into the image at all. For shipping, cart and
flagd-ui, the source pass is the only dependency coverage there is, and flagd-ui's bundled OTP
runtime is read by neither scan. currency has neither: opentelemetry-cpp is cloned at a release
tag and compiled into the image, and neither scan reads it.

The counts are not expected to match, and neither number is the other's check:

- product-reviews and recommendation install under a pip-generated `requirements.lock`. Trivy's
  pip analyzer reads only files named `requirements.txt`, so a file pattern adds the lock, and
  the resolved count includes the manifest's own entries.
- ad and fraud-detection lock every Gradle configuration, compile-only, test and build-tool
  configurations included, so the source pass reads more than either image carries.
  fraud-detection's image shows 45 of its 74 runtime lock entries, because its dependencies are
  merged into one shadow jar and the scan identifies only those whose Maven metadata is inside
  it.
- payment is the opposite case: its image carries more component records than the lock file
  resolves, because the scanner reads the installed tree while the source pass reads the
  declared one.
- The source pass never sees the operating-system layer, which is what the image gate reads.

### The Source Dependency Gate

`SOURCE_DEPENDENCIES` is why an empty result is readable. Trivy reports nothing for a project
whose dependency set it cannot resolve, and nothing is indistinguishable from clean: before this
control, cart and quote each resolved zero packages and reported zero findings. A service
declaring managed dependencies must now resolve at least one package or its job fails, so a
scanner blind spot blocks instead of passing quietly. Only frontend-proxy, image-provider and
currency declare `none`. The first two genuinely have no package manager; currency has no
language package manager, and its compiled-in library is the blind spot recorded above.

The gate blocks on fixable HIGH and CRITICAL, the same threshold and the same `--ignore-unfixed`
semantics the image gate uses. Findings without an available fix are reported and not hidden.

A passing source gate is only as current as the scanner's database. On 2026-10-16 the database
of 2026-10-15 reported nothing against bandit 1.12.5, while `mix deps.get` printed, and OSV
listed, a HIGH advisory against it, EEF-CVE-2026-105659. flagd-ui's lock was moved off it on that
evidence.

## Evidence Owed by Every Deployed Component

Sixteen items:

1. Upstream or external image origin
2. Classification
3. Modification record
4. Container definition or image source
5. Reusable pipeline configuration, where project-built
6. Build result, where project-built
7. Current scan result
8. SBOM, where project-built
9. Registry digest
10. Desired-state digest that deploys it
11. Runtime health
12. Dependency purpose
13. Telemetry presence, where the component technically supports it
14. Known limitations
15. Any active security exception
16. Teardown result

No component carries the full set. checkout, shipping and quote carry most of them.
image-provider carries the build, scan, SBOM, registry-digest and pipeline items but none of the
runtime ones. The other thirteen each carry their pipeline configuration and an executed build,
both security gates and an SBOM, with no runtime behind them. frontend-proxy is the only one of
those thirteen with a recorded publication, for an earlier image whose digest was read back from
the registry; its hardened image has no verified publication.

## Evidence Owed by Paths Rather Than Components

Depth is not uniform across a polyglot fleet, and claiming otherwise would be dishonest. Nine
paths carry the deep validation: browser entry, synchronous multi-service checkout, asynchronous
producer to broker to consumer, durable data, feature control, rollback, induced-fault
investigation, recovery, and fleet teardown with orphan verification.

## Prior Work Is Not Evidence Here

A previous bare-metal Kubernetes project built and exercised much of this application. That
lowers uncertainty about what is likely to work. It is not a prerequisite, not a dependency, and
not proof about this platform. Nothing in this repository may cite it as evidence that the
implementation works. Every item above is produced fresh.

## Hardening History

Every hardened definition was merged through one of these merge requests after its pipeline
passed. Dates are UTC.

| Merge request | Date | Components | Change |
|---|---|---|---|
| !44 | 2026-10-13 | checkout, product-catalog | Container definitions rewritten and now project-maintained; both modules moved to `go 1.26.0` with `golang.org/x/net` `v0.60.0` in the same change |
| !45 | 2026-10-14 | payment | Image hardened and the libssl override dropped |
| !46 | 2026-10-14 | frontend | Image hardened and build inputs pinned |
| !47 | 2026-10-15 | quote | Image hardened and build inputs pinned |
| !48 | 2026-10-15 | image-provider | Base moved to `1.30.6-alpine3.24-otel` without the build-time package upgrade |
| !49 | 2026-10-15 | frontend-proxy | Base moved to Envoy `v1.37.9` with only `gettext-base` installed |
| !50 | 2026-10-15 | cart, product-reviews, recommendation | cart: base moved to .NET `runtime-deps:10.0.13-alpine3.24` without the build-time package upgrade. product-reviews and recommendation: base moved to `python:3.12.15-alpine3.24` without the runtime package upgrade, and both now run as a non-root user |
| !51 | 2026-10-15 | ad, fraud-detection | ad: base moved to `eclipse-temurin:21.0.12.1_1-jre-noble`, the Ubuntu 24.04 build of the same JRE, without the OpenSSL pin that no longer installed, and it now runs as a non-root user. fraud-detection: digest-pinned bases and a root-owned application directory, and its lock takes lz4-java `1.11.4` in place of the `1.10.1` kafka-clients asks for |
| !52 | 2026-10-16 | accounting, email | Digest-pinned bases with root-owned application files and numeric non-root users, so email no longer runs as root |
| !53 | 2026-10-16 | shipping, currency | Digest-pinned images |
| !54 | 2026-10-16 | flagd-ui | Digest-pinned images, a root-owned release and a numeric non-root user; its lock takes bandit 1.13.1 for a HIGH advisory the source gate's database did not yet carry |
