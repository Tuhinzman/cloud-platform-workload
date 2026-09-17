# Cloud Platform Workload

The application this platform runs, and nothing else. Architecture, infrastructure, and
the reasoning behind them live in the
[platform reference repository](https://github.com/Tuhinzman/cloud-platform-reference). This repository holds
workload source, container definitions, build configuration, and the provenance record
that makes the derivation reproducible.

## Why This Repository Exists

The platform is the product. This application exists to validate it under conditions a
smaller workload cannot create: one delivery pipeline serving many services rather than a
few hand-tuned ones, reconciliation holding across a fleet, telemetry attribution
surviving when many services emit at once, and teardown proving clean when there is
something substantial to tear down.

The application is not the subject, and the platform stays valid if it is replaced.

## What Is Here

Seventeen components derived from a pinned upstream release, extracted into
[services/](services/), with the shared protobuf contract in [pb/](pb/).

Fifteen are application services across ten language tiers. Two, `frontend-proxy` and
`image-provider`, package an upstream binary with project-owned configuration and carry no
upstream application source.

[DERIVATION.md](DERIVATION.md) records what was taken, what was excluded and why, what this
project owns, and how to reproduce the tree byte for byte.

[UPSTREAM-EXCEPTIONS.md](UPSTREAM-EXCEPTIONS.md) records components deployed but not built
here, each with a justification and the condition that would remove it.

[SERVICE-INVENTORY.md](SERVICE-INVENTORY.md) is where per-component evidence is
reported. Its status columns remain empty until corresponding per-component evidence
is recorded.

## Current Status

Implementation evidence is partial. Checkout, shipping and quote have each been built,
scanned, published with an SBOM, and exercised inside bounded EKS runtime windows:
shipping carries a four-of-four telemetry signal digest match, and quote's induced fault
and recovery were observed end to end. Every runtime was torn down, and no runtime is
currently live.

Twenty-two container definitions are modified, each carrying an Apache-2.0 modification
notice. They are adapted deliberately, for this repository's build layout and for the
platform work this workload exists to exercise.

Beyond those, `checkout` carries project modifications to its application source and its Go
dependency metadata, `product-catalog` and `shipping` to their application source, and
`quote` to its dependency metadata, and `frontend` to five application-source files. Every
other upstream-derived file in the compared scope,
including all remaining application source and the protobuf contract, is byte-identical to
the pinned upstream release. That scope is `services/`, `pb/` and `LICENSE`, and the
comparison makes no claim about files outside it.

Upstream wrote this application and none of it is claimed as this project's work.
[DERIVATION.md](DERIVATION.md) is the per-file record of what differs and how to reproduce
the tree.

The pipeline now has shared templates for Go, Node, PHP, and Rust, but validation
coverage is not uniform across the fleet. Checkout has an executed and passing Dockerfile
lint path. Shipping and quote have executed validated build, scan, SBOM, and container
health paths. Frontend, payment, and product-catalog have executed pipelines that reach the
lint stage only. frontend-proxy and image-provider are wired through the same shared
templates for build, scan, SBOM and container health; neither carries a language tier,
because neither directory holds application source. The product-catalog Go lint job is now
configured as blocking and its latest validated run reports no findings. payment declares
no linter and no TypeScript, so
it extends a Node parse check rather than a lint, which asserts only that every `.js` file
in the service directory parses; that job is now configured as blocking and its first
validated run passed. The frontend Node lint job is blocking: the service now carries a
project-added flat ESLint configuration, and the latest validated run on main reports zero
errors and twelve reported-but-unremediated warnings, with the TypeScript check reached and
passing.

Checkout, shipping and quote have each completed build, scan, SBOM and artifact-publication
stages, and each published digest was read back independently from the registry.
image-provider has since completed the same stages, and its pipeline also produced a
retained provenance bundle whose published digest is the sha256 of the registry manifest
bytes the bundle keeps. frontend-proxy is wired for those stages and has published nothing.
Those stages are not evidenced fleet-wide, nine components have no pipeline configuration at
all, and promotion remains a separate implementation and validation obligation.

## Licence and Attribution

The application originates in the OpenTelemetry Demo project, licensed Apache-2.0. The
upstream licence is included as [LICENSE](LICENSE), copied unchanged from the pinned
release. The upstream release contains no NOTICE file, so none is included here.

Upstream wrote the application, its service architecture, its protobuf contracts, and its
OpenTelemetry instrumentation. What this project adds is stated in
[DERIVATION.md](DERIVATION.md) rather than implied here.
