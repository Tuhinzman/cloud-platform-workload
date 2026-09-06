# Cloud Platform Workload

The application this platform runs, and nothing else. Architecture, infrastructure, and
the reasoning behind them live in the platform reference repository. This repository holds
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

Implementation evidence is partial. Checkout has been built, scanned, published with an
SBOM, and validated during a bounded EKS runtime window. That runtime was subsequently
torn down, and no runtime is currently live.

Twenty-two container definitions are modified, each carrying an Apache-2.0 modification
notice. They are adapted deliberately, for this repository's build layout and for the
platform work this workload exists to exercise.

Beyond those, `checkout` carries project modifications to its application source and its Go
dependency metadata, `product-catalog` and `shipping` to their application source, and
`quote` to its dependency metadata. Every other upstream-derived file in the compared scope,
including all remaining application source and the protobuf contract, is byte-identical to
the pinned upstream release. That scope is `services/`, `pb/` and `LICENSE`, and the
comparison makes no claim about files outside it.

Upstream wrote this application and none of it is claimed as this project's work.
[DERIVATION.md](DERIVATION.md) is the per-file record of what differs and how to reproduce
the tree.

The pipeline now has shared templates for Go, Node/TypeScript, PHP, and Rust, but validation
coverage is not uniform across the fleet. Checkout has an executed and passing Dockerfile
lint path. Shipping and quote have executed validated build, scan, SBOM, and container
health paths. Frontend, payment, and product-catalog have executed lint-only pipelines.
Their language-lint jobs remain non-blocking: product-catalog reports golangci-lint
findings, while frontend and payment exit before lint findings are produced because
neither carries an ESLint flat configuration.

Checkout has also completed build, scan, SBOM, and artifact-publication stages. Those
stages are not yet evidenced fleet-wide, and promotion remains a separate implementation
and validation obligation.

## Licence and Attribution

The application originates in the OpenTelemetry Demo project, licensed Apache-2.0. The
upstream licence is included as [LICENSE](LICENSE), copied unchanged from the pinned
release. The upstream release contains no NOTICE file, so none is included here.

Upstream wrote the application, its service architecture, its protobuf contracts, and its
OpenTelemetry instrumentation. What this project adds is stated in
[DERIVATION.md](DERIVATION.md) rather than implied here.
