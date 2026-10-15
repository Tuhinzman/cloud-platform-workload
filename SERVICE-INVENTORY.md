# Service Inventory

Per-component evidence for the fleet. This is the single copy. The platform reference
repository links here rather than holding a second table, because two copies of a status
table drift apart.

**Evidence status is partial, and the kinds of evidence differ.** Checkout, shipping and
quote each have build, scan, SBOM, artifact-publication and bounded runtime evidence.
The checkout and product-catalog container definitions were rewritten on 2026-10-13, and
both modules moved to `go 1.26.0` with `golang.org/x/net` `v0.60.0` in the same change;
every pipeline, publication and runtime result recorded here for those two belongs to
images built before it, and the new state carries local validation only until a pipeline
has run it.
image-provider has build, scan, SBOM and artifact-publication evidence; it has no runtime
evidence, because no runtime window has included it. Its container definition moved on
2026-10-15 to the `1.30.6-alpine3.24-otel` base without the build-time package upgrade; that
evidence belongs to images built before the change, and the new definition carries local
validation only until a pipeline has run it. Two publications carry a provenance
bundle the pipeline retained itself, shipping first and then image-provider. frontend-proxy
is wired for build, scan, SBOM and container health and has published nothing. Its container
definition moved on 2026-10-15 to the Envoy `v1.37.9` base with only `gettext-base` installed;
the pipeline results recorded for it belong to the earlier definition, and the new one carries
local validation only until a pipeline has run it. cart has
executed build, scan and SBOM on a pipeline that passed, validates container health against
an ephemeral Valkey fixture, and has published nothing: no digest, no promotion, no
runtime. Its container definition moved on 2026-10-15 to the .NET
`runtime-deps:10.0.13-alpine3.24` base without the build-time package upgrade; the pipeline
results recorded for it belong to the earlier definition, and the new one carries local
validation only until a pipeline has run it. payment and frontend each carry build, both security gates, SBOM, container
health and the manual publish and evidence jobs on main; product-catalog carries all of
those but the publication jobs, and validates container health against an ephemeral
PostgreSQL fixture. None of the four has
published anything. frontend additionally returned
HTTP 200 with rendered HTML and served the `/_next/` assets that page referenced; that is a
bounded startup and static-asset result, not a check of any backend call it would make. Its container health is a real result rather
than an exception: it binds its gRPC port before anything external is needed. What that
does not cover is recorded with it - the Charge handler reaches flagd per request, so the
application path beyond the health service is not validated in CI.
currency, product-reviews, recommendation, email and ad carry build, both security gates,
SBOM and container health with no publication stage. The product-reviews and recommendation
container definitions moved on 2026-10-15 to the `python:3.12.15-alpine3.24` base without the
runtime package upgrade, and both now run as a non-root user; the pipeline results recorded
for them belong to the earlier definitions, and the new ones carry local validation only until
a pipeline has run them. fraud-detection and accounting carry
build, both security gates and SBOM with no publication stage, and a running check in place
of container health, because neither listens. flagd-ui carries build, both security gates,
SBOM and its eleven upstream tests, with container health deferred to runtime and no
publication stage. Wiring is not execution, publication is not runtime evidence, and none of
this is fleet-wide delivery. Identity and classification are facts about the source and are
populated independently of that evidence.

Five classes. Every component belongs to exactly one, and the class decides what evidence
it owes.

## 1. Project-Built Application Services

Derived from upstream application source and built here through this project's pipeline.
The application source is upstream work. This project owns the container definition, the
hardening, the pipeline, and the evidence.

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

### Language tiers

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

All ten tiers have a template today, and all fifteen services are wired to the pipeline.
Seventeen components are wired in total, the two configured components in section 2
included. ADR-0017 selects the full justified project-built inventory as the target of an
owner-selected end-to-end programme; wiring it is not delivering it. .NET was the first of
the six tiers to be implemented, C++ the second, Python the third, Ruby the fourth, Elixir
the fifth and Java the sixth, and nothing here says those components are delivered.

## 2. Project-Built Configured Components

A container definition and project-owned configuration, with no upstream application source
behind it. Built here, so each carries a build record, an SBOM, and its own validation. No
application provenance is claimed, and no language tier applies.

| Component | What it packages | Upstream path at tag `2.2.0` | Container definition |
|---|---|---|---|
| frontend-proxy | Envoy binary with a project configuration template | `src/frontend-proxy` | Path plus hardening |
| image-provider | nginx binary with a project configuration template and static assets | `src/image-provider` | Path plus hardening |

Both were confirmed against pinned source. The provisional classification listed
`image-provider` among the application services, and inspection shows its directory holds a
container definition, an nginx configuration template, and static assets with no application
code, which is the same shape as `frontend-proxy`.

## 3. Justified Upstream Exceptions

Deployed but not built here. Under ADR-0012 these are pinned by digest, mirrored into the
platform registry so no pod start depends on an external service, and scanned there under the
same threshold that gates built services. They carry no build provenance, and that limit is
stated rather than implied. That is the required handling rather than a record of what has
happened: none of those controls has been executed for the entry below, which is not mirrored,
not scanned, carries no project-owned digest, and is disabled in the only environment that has
run.

| Component | Why not built here | Condition to remove |
|---|---|---|
| flagd | No container definition exists at the pinned tag, verified | Upstream adds one, or the feature-control path is served by a component built here |

Full justification is in [UPSTREAM-EXCEPTIONS.md](UPSTREAM-EXCEPTIONS.md).

## 4. Infrastructure Dependencies

Required by the application but not application services. Their deployment form is an open
implementation decision with its own cost gate, so no form is recorded here.

| Component | Role | Form |
|---|---|---|
| Message broker | Carries the asynchronous producer to consumer path | Undecided. In-cluster or managed. |
| Cache | Sits behind the cart | Undecided. In-cluster or managed. |
| Durable datastore | Holds data that must outlive its environment | Undecided product, constrained to a managed service with native backup |

## 5. Not Deployed

Absent from every environment. A component excluded from the fleet is not an upstream
exception. It simply does not run.

| Component | Why |
|---|---|
| load-generator | Not deployed. Runs as root and carries a large volume of unfixed operating-system findings, and proves no platform capability the rest of the fleet does not. May be enabled inside a bounded, owner-approved validation window and is otherwise absent. |
| Workload bundled observability stack | Observability belongs to the platform, and duplicate collection is waste |
| Workload own collector | Telemetry reaches the platform gateway only |
| llm | Not part of a justified application path |
| react-native-app | Not part of a justified application path |

## Container Health Disposition

Fourteen of the seventeen wired components prove container health in CI. fraud-detection and
accounting never listen, so they have no port to prove, and flagd-ui's health is deferred to
runtime: a deferred
entry is not a pass and not runtime evidence. Two reach their listening state only after a
startup dependency answers, so their health job starts that dependency beside them as a
digest-pinned fixture on a job-private network. That proves the image starts against the
dependency it needs; it is not runtime readiness, and the readiness obligation stays open
until a runtime window answers it. Every port probe first starts a container that listens on
nothing on the same port and must read it as closed, so where a proxy answers for published
ports the job fails instead of passing a service it cannot prove. A worker that never listens
is checked in a running mode that proves only that the process stays up for a bounded time
beside a control that aborts itself at once. Both run under an init process, because as PID 1
a process that aborts, as .NET does on an unhandled exception, is left running rather than
exited. fraud-detection and accounting are the two components in that mode. The fixtures take no credential
and no data, and they are not the runtime dependency: cart's cache form and
product-catalog's managed database are separate decisions.

| Component | Container health |
|---|---|
| checkout, quote, shipping, frontend-proxy, image-provider, payment, frontend, currency, product-reviews, recommendation, email, ad | validated in CI |
| cart | validated in CI against an ephemeral fixture: Valkey 9.0.1 from the upstream chart, because `Program.cs:98` resolves ValkeyCartStore before `app.Run()` and `ValkeyCartStore.cs:101` throws without it |
| product-catalog | validated in CI against an ephemeral fixture: PostgreSQL 17.11, the Dev datastore's engine version, with trust authentication and no schema, because `main()` calls `initDatabase()` before the listener and exits 1 without it |
| flagd-ui | health: deferred to runtime — `application.ex:20` starts `FlagdUi.Storage` before the endpoint and `storage.ex:23` reads `/app/data/demo.flagd.json`, which its pod mounts, so without that file the release exits 1 before listening |
| fraud-detection | running in CI, not functional health — `main.kt` polls Kafka in a loop and opens no server socket, so there is no port to probe; given a `KAFKA_ADDR` that resolves with no broker behind it, the process must stay up for 30 s, and without the variable, or with an unresolvable address, it exits 1 and the job fails |
| accounting | running in CI, not functional health — `Program.cs:14` builds a host with no server and `Consumer.cs:66` blocks in the Kafka consume loop, so there is no port to probe; given an unresolvable `KAFKA_ADDR` the process retries and must stay up for 30 s, and without the variable `Consumer.cs:42` throws and the job fails. Measured: without an init that exception leaves the process running as PID 1 rather than exited |

## Dependency Scanning Coverage

ADR-0009 asks one scanner to cover image *and* dependency scanning. Those are two views,
and measurement on this fleet shows neither one contains the other, so the pipeline runs
both and neither is recorded as evidence for the other.

What the image scan sees depends on what the build leaves legible in the image, and that
varies by language rather than by packaging. Measured at the current anchor:

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
| ad | Java | 70 Maven, from the installed jars and the OpenTelemetry agent, and 13 Go modules from the base image's `pebble` binary | 78, from `gradle.lockfile` |
| fraud-detection | Java | 46 Maven: the 45 whose metadata is inside the shadow jar, and the OpenTelemetry agent | 102, from `gradle.lockfile` |
| accounting | .NET | 48 NuGet, from the application's and the shared runtime's `.deps.json` | 67, from `packages.lock.json` |

Four of the seventeen carry no managed dependency into the image at all. For shipping, cart
and flagd-ui the source pass is the only dependency coverage there is, and flagd-ui's bundled
OTP runtime is read by neither scan; currency has neither:
opentelemetry-cpp is cloned at a release tag and compiled into the image, and neither scan
reads it. product-reviews and recommendation install under a pip-generated
`requirements.lock`; Trivy's pip analyzer reads only files named `requirements.txt`, so a
file pattern adds the lock, and the resolved count includes the manifest's own entries. ad
and fraud-detection lock every Gradle configuration, compile-only, test and build-tool
configurations included, so the source pass reads more than either image carries;
fraud-detection's image shows 45 of its 74 runtime lock entries, because its dependencies are
merged into one shadow jar and the scan identifies only those whose Maven metadata is inside it. payment is the opposite case: its
image carries more component records than the lock file resolves, because the scanner
reads the installed tree while the source pass reads the declared one. The counts are not
expected to match and neither number is the other's check. The reverse also holds: the source pass
never sees the operating-system layer, which is what the image gate reads.

`SOURCE_DEPENDENCIES` is why an empty result is readable. Trivy reports nothing for a
project whose dependency set it cannot resolve, and nothing is indistinguishable from
clean: before this control, cart and quote each resolved zero packages and reported zero
findings. A service declaring managed dependencies must now resolve at least one package
or its job fails, so a scanner blind spot blocks instead of passing quietly. Only
frontend-proxy, image-provider and currency declare `none`. The first two genuinely have no
package manager; currency has no language package manager, and its compiled-in library is
the blind spot recorded above.

The gate blocks on fixable HIGH and CRITICAL, the same threshold and the same
`--ignore-unfixed` semantics the image gate uses. Findings without an available fix are
reported and not hidden.

## Evidence Owed by Every Deployed Component

Sixteen items. No component carries the full set: checkout, shipping and quote carry
most of them, image-provider carries the build, scan, SBOM, registry-digest and pipeline
items but none of the runtime ones, frontend-proxy carries its pipeline configuration
alone, cart, payment, frontend, product-catalog, currency, product-reviews, recommendation,
email, flagd-ui, ad, fraud-detection and accounting each carry their pipeline configuration
and an executed build, both security gates and an SBOM with no publication or runtime behind
them.
Upstream or external image origin, classification, modification record, container
definition or image source, reusable pipeline configuration where project-built, build
result where project-built, current scan result, SBOM where project-built, registry digest,
desired-state digest that deploys it, runtime health, dependency purpose, telemetry
presence where the component technically supports it, known limitations, any active
security exception, and teardown result.

## Evidence Owed by Paths Rather Than Components

Depth is not uniform across a polyglot fleet, and claiming otherwise would be dishonest.
Nine paths carry the deep validation: browser entry, synchronous multi-service checkout,
asynchronous producer to broker to consumer, durable data, feature control, rollback,
induced-fault investigation, recovery, and fleet teardown with orphan verification.

## Prior Work Is Not Evidence Here

A previous bare-metal Kubernetes project built and exercised much of this application. That
lowers uncertainty about what is likely to work. It is not a prerequisite, not a dependency,
and not proof about this platform. Nothing in this repository may cite it as evidence that
the implementation works. Every item above is produced fresh.
