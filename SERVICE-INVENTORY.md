# Service Inventory

Per-component evidence for the fleet. This is the single copy. The platform reference
repository links here rather than holding a second table, because two copies of a status
table drift apart.

**Evidence status is partial.** Checkout has build, scan, SBOM, artifact-publication, and
bounded runtime evidence. Evidence for other components remains unpopulated until the
corresponding implementation and validation have actually occurred. Identity and
classification are facts about the source and are populated independently of that evidence.

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
| cart | .NET | `src/cart` | Path plus hardening | Unit, `tests/CartServiceTests.cs` |
| checkout | Go | `src/checkout` | Modified beyond path retarget | Unit, `money/money_test.go` |
| currency | C++ | `src/currency` | Path plus hardening | None |
| email | Ruby | `src/email` | Path plus hardening | None |
| flagd-ui | Elixir | `src/flagd-ui` | Path plus hardening | Unit and controller, seven files |
| fraud-detection | Java | `src/fraud-detection` | Path-only modified | None |
| frontend | TypeScript | `src/frontend` | Path-only modified | Cypress harness configuration |
| payment | TypeScript | `src/payment` | Path plus hardening | None |
| product-catalog | Go | `src/product-catalog` | Path-only modified | None |
| product-reviews | Python | `src/product-reviews` | Path plus hardening | None |
| quote | PHP | `src/quote` | Path-only modified | None |
| recommendation | Python | `src/recommendation` | Path plus hardening | None |
| shipping | Rust | `src/shipping` | Path-only modified | None |

### Language tiers

Ten tiers, discovered by inspecting pinned source rather than inferred from base images.

| Tier | Services | Pipeline template |
|---|---|---|
| Go | checkout, product-catalog | `ci/templates/lang-go.yml`, carried |
| TypeScript | frontend, payment | `ci/templates/lang-node.yml`, carried |
| .NET | accounting, cart | Net-new |
| Java | ad, fraud-detection | Net-new |
| Python | product-reviews, recommendation | Net-new |
| Rust | shipping | Net-new |
| Ruby | email | Net-new |
| PHP | quote | Net-new |
| C++ | currency | Net-new |
| Elixir | flagd-ui | Net-new |

Two tiers of ten have a template today. Eight are net-new work. Four services are wired to
the pipeline, and eleven are not, because their tier has no template yet.

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

Deployed but not built here. Pinned by digest, mirrored into the platform registry so no pod
start depends on an external service, and scanned there under the same threshold that gates
built services. They carry no build provenance, and that limit is stated rather than implied.

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

## Evidence Owed by Every Deployed Component

Sixteen items, none of which exists yet: upstream or external image origin, classification,
modification record, container definition or image source, reusable pipeline configuration
where project-built, build result where project-built, current scan result, SBOM where
project-built, registry digest, desired-state digest that deploys it, runtime health,
dependency purpose, telemetry presence where the component technically supports it, known
limitations, any active security exception, and teardown result.

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
