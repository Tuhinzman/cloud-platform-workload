# Upstream Exception Register

A component belongs here when it runs in an environment but is not built in this
repository. Every entry states why it cannot be built here, what is lost by not building
it, and the condition that would move it out of this register.

Components that simply do not run are not exceptions. They are recorded as exclusions in
[DERIVATION.md](DERIVATION.md).

## Active Exceptions

### flagd

| | |
|---|---|
| Upstream path at the pinned tag | `src/flagd` |
| Why it is not built here | The directory contains no container definition. Verified at tag `2.2.0`, where the component has zero Dockerfiles. There is nothing to build from. |
| Role | Feature-flag evaluation, which the feature-control validation path depends on. |
| What is lost | No build provenance and no SBOM produced by this project. The image is upstream work end to end. |
| Handling | Pinned by digest and mirrored into the platform registry, so no pod start depends on an external service. Scanned in that registry under the same threshold that gates built services. |
| Condition to remove | Upstream adds a container definition, or the feature-control path is served by a component this project builds. |

## Components Deployed but Not Yet Classified Here

The message broker, the cache behind the cart, and the durable datastore are
infrastructure dependencies. Their deployment form is an open implementation decision, and
whether any of them ends up as an upstream exception depends on that decision. They are
not listed above because listing them now would record a classification that has not been
made.

## Standing Rule

The security admission gate is never weakened to keep a component in the fleet. When an
exploitable finding has no acceptable mitigation, the component is held or dropped. A held
component is an honest state and is recorded as one rather than hidden.
