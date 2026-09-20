# Service Inventory

Per-component evidence for the fleet. This is the single copy. The platform reference
repository links here rather than holding a second table, because two copies of a status
table drift apart.

**Evidence status is partial, and the kinds of evidence differ.** Checkout, shipping and
quote each have build, scan, SBOM, artifact-publication and bounded runtime evidence.
image-provider has build, scan, SBOM and artifact-publication evidence; it has no runtime
evidence, because no runtime window has included it. Two publications carry a provenance
bundle the pipeline retained itself, shipping first and then image-provider. frontend-proxy
is wired for build, scan, SBOM and container health and has published nothing. cart has
executed build, scan and SBOM on a pipeline that passed, has no container health job,
and has published nothing: no registry repository, no digest, no promotion, no runtime.
payment, frontend and product-catalog each carry build, both security gates, SBOM and
container health, and have published nothing for the same reason cart has not. frontend additionally returned
HTTP 200 with rendered HTML and served the `/_next/` assets that page referenced; that is a
bounded startup and static-asset result, not a check of any backend call it would make. Its container health is a real result rather
than an exception: it binds its gRPC port before anything external is needed. What that
does not cover is recorded with it - the Charge handler reaches flagd per request, so the
application path beyond the health service is not validated in CI.
Evidence for the remaining eight components is unpopulated until the corresponding
implementation and validation have actually occurred. Wiring is not execution,
publication is not runtime evidence, and none of this is fleet-wide delivery: eight
components have no pipeline configuration at all. Identity and classification are facts
about the source and are populated independently of that evidence.

Five classes. Every component belongs to exactly one, and the class decides what evidence
it owes.

## 1. Project-Built Application Services

Derived from upstream application source and built here through this project's pipeline.
The application source is upstream work. This project owns the container definition, the
hardening, the pipeline, and the evidence.

| Component | Language tier | Upstream path at tag `2.2.0` | Container definition | Tests present upstream |
|---|---|---|---|---|
| accounting | .NET | `src/accounting` | Path-only modified | None |
| ad | Java | `src/ad` | Path-only modified | None |
| cart | .NET | `src/cart` | Path plus hardening | Unit, `tests/CartServiceTests.cs`, all skipped upstream |
| checkout | Go | `src/checkout` | Modified beyond path retarget | Unit, `money/money_test.go` |
| currency | C++ | `src/currency` | Path plus hardening | None |
| email | Ruby | `src/email` | Path plus hardening | None |
| flagd-ui | Elixir | `src/flagd-ui` | Path plus hardening | Unit and controller, seven files |
| fraud-detection | Java | `src/fraud-detection` | Path-only modified | None |
| frontend | Node | `src/frontend` | Path-only modified | Cypress harness configuration |
| payment | Node | `src/payment` | Path plus hardening | None |
| product-catalog | Go | `src/product-catalog` | Path-only modified | None |
| product-reviews | Python | `src/product-reviews` | Path plus hardening | None |
| quote | PHP | `src/quote` | Path plus hardening | None |
| recommendation | Python | `src/recommendation` | Path plus hardening | None |
| shipping | Rust | `src/shipping` | Path-only modified | None |

### Language tiers

Ten tiers, discovered by inspecting pinned source rather than inferred from base images.

| Tier | Services | Pipeline template |
|---|---|---|
| Go | checkout, product-catalog | `ci/templates/lang-go.yml`, carried |
| Node | frontend, payment | `ci/templates/lang-node.yml` |
| .NET | accounting, cart | `ci/templates/lang-dotnet.yml`, net-new |
| Java | ad, fraud-detection | Net-new |
| Python | product-reviews, recommendation | Net-new |
| Rust | shipping | `ci/templates/lang-rust.yml`, net-new |
| Ruby | email | Net-new |
| PHP | quote | `ci/templates/lang-php.yml`, net-new |
| C++ | currency | Net-new |
| Elixir | flagd-ui | Net-new |

Five tiers of ten have a template today. Seven services are wired to the pipeline. Eight
are not: seven because their tier has no template, and accounting because its .NET tier
has one only as of this change and it has not been wired to it. Nine components are
wired in total, the two configured components in section 2 included. ADR-0017 selects
the full justified project-built inventory as the target of an owner-selected end-to-end
programme, so the remaining five tiers are selected work rather than work ruled out.
.NET was the first of the six to be implemented, and nothing here says those components
are delivered.

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

Two of the nine carry no managed dependency into the image at all, so for those the
source pass is the only dependency coverage there is. payment is the opposite case: its
image carries more component records than the lock file resolves, because the scanner
reads the installed tree while the source pass reads the declared one. The counts are not
expected to match and neither number is the other's check. The reverse also holds: the source pass
never sees the operating-system layer, which is what the image gate reads.

`SOURCE_DEPENDENCIES` is why an empty result is readable. Trivy reports nothing for a
project whose dependency set it cannot resolve, and nothing is indistinguishable from
clean: before this control, cart and quote each resolved zero packages and reported zero
findings. A service declaring managed dependencies must now resolve at least one package
or its job fails, so a scanner blind spot blocks instead of passing quietly. Only
frontend-proxy and image-provider declare `none`, and each genuinely has no package
manager.

The gate blocks on fixable HIGH and CRITICAL, the same threshold and the same
`--ignore-unfixed` semantics the image gate uses. Findings without an available fix are
reported and not hidden.

## Evidence Owed by Every Deployed Component

Sixteen items. No component carries the full set: checkout, shipping and quote carry
most of them, image-provider carries the build, scan, SBOM, registry-digest and pipeline
items but none of the runtime ones, frontend-proxy carries its pipeline configuration
alone, cart, payment, frontend and product-catalog each carry their pipeline configuration
and an executed build, both security gates and an SBOM with no publication or runtime behind
them, and the remaining eight components carry none.
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
