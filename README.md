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

[SERVICE-INVENTORY.md](SERVICE-INVENTORY.md) is where per-component evidence will be
reported. Its status columns are empty, because a filled-in inventory ahead of
implementation would be a claim rather than a record.

## Current Status

Nothing is implemented. No image has been built, no scan has run, no SBOM exists, no
artifact has been published, and no cluster has run any of this.

Twenty-two container definitions are modified, each carrying an Apache-2.0 modification
notice. Everything else, including all application source and the protobuf contract, is
byte-identical to the pinned upstream release.

The pipeline runs real static validation today for Dockerfiles, Go, and TypeScript, across
four services in the two language tiers whose templates exist. Building, scanning,
publishing, and promotion are defined as stages but not yet populated, because each
depends on a decision that has not been made.

## Licence and Attribution

The application originates in the OpenTelemetry Demo project, licensed Apache-2.0. The
upstream licence is included as [LICENSE](LICENSE), copied unchanged from the pinned
release. The upstream release contains no NOTICE file, so none is included here.

Upstream wrote the application, its service architecture, its protobuf contracts, and its
OpenTelemetry instrumentation. What this project adds is stated in
[DERIVATION.md](DERIVATION.md) rather than implied here.
