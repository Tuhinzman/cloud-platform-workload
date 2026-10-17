# Cloud Platform Workload

> Authoritative repository: [GitLab, tuinzaman/cloud-platform-workload](https://gitlab.com/tuinzaman/cloud-platform-workload).
> The copy on GitHub is a read-only mirror. Merge requests and CI run on GitLab only.

This repository holds the application the Cloud Platform Reference runs to validate itself:
seventeen components derived from the OpenTelemetry Demo, with their container definitions,
build and CI configuration, and the provenance record that makes the derivation reproducible.
Architecture, infrastructure and the reasoning behind them live in the
[platform reference repository](https://github.com/Tuhinzman/cloud-platform-reference).

The platform is the product. This application exists to validate it under conditions a
smaller workload cannot create: one delivery pipeline serving many services, reconciliation
holding across a fleet, telemetry attribution surviving when many services emit at once, and
teardown proving clean when there is something substantial to tear down. The platform stays
valid if the application is replaced.

## Current Status

All seventeen container definitions were hardened between 2026-10-13 and 2026-10-16 and
merged through GitLab merge requests !44 to !54, each after its merge-request pipeline
passed. That milestone is not delivery. For the hardened images:

| Evidence | Status |
|---|---|
| Container hardening | Merged for all seventeen components |
| Merge-request pipelines | Passed; only the overall status is recorded, and job logs and artifacts have not been inspected |
| Security scanning evidence | No scan report or SBOM artifact from those pipelines has been inspected |
| Image publication | None verified; no hardened image is recorded as published to ECR |
| GitOps digest binding | None; no hardened image is pinned in the deployment repository |
| EKS runtime validation | None; no hardened image has run on AWS |

The earlier evidence belongs to images built before the hardening. checkout, shipping and
quote were built, scanned, published with an SBOM, read back from the registry by digest,
and exercised inside bounded EKS runtime windows: shipping carries a four-of-four telemetry
signal digest match, and quote's induced fault and recovery were observed end to end.

image-provider was published the same way and has not run. An earlier frontend-proxy image
was published on 2026-09-26 and its digest read back from the registry; it has not run, and
the provenance bundle the pipeline retained for it failed verification, so it is not counted
as provenance. Every runtime was torn down, and no runtime is currently live.

ADR-0009 and ADR-0014 govern these workload images; ADR-0015 governs platform-managed runtime
components. ADR-0017 selects the full justified project-built inventory as the target of an
owner-selected end-to-end programme. Selecting it is not delivering it, and promotion remains
a separate implementation and validation obligation.

## What Is Here

The seventeen components live in [services/](services/), with the shared protobuf contract
in [pb/](pb/). Fifteen are application services across ten language tiers: Go, Node, .NET,
Java, Python, Rust, Ruby, PHP, C++ and Elixir. Two, `frontend-proxy` and `image-provider`,
package an upstream binary with project-owned configuration and carry no upstream application
source.

| Document | What it records |
|---|---|
| [SERVICE-INVENTORY.md](SERVICE-INVENTORY.md) | Every component's class, pipeline coverage, tests and evidence, and what each result does not show |
| [DERIVATION.md](DERIVATION.md) | What was taken from upstream, what was excluded, what changed and how to reproduce the tree |
| [UPSTREAM-EXCEPTIONS.md](UPSTREAM-EXCEPTIONS.md) | Components deployed but not built here, each with its justification and removal condition |

## Container Hardening

The upstream definitions were written to run the demo, not to supply a platform that admits
images by digest and runs them as unprivileged users. Most bases were referenced by tag
rather than digest, and many of those tags float. Several images ran as root, others let the
runtime user replace or delete what it ran, and the scans reported fixable HIGH and CRITICAL
findings that the pipeline's gates block on.

Each definition now pins its base images by digest, runs as a numeric non-root user over
application files owned by root, and, where it listens, declares the port it uses. The
fixable HIGH and CRITICAL findings were cleared by moving bases and dependencies, with no
scanner exception or ignore rule. Several images still read a moving package index at build
time. The per-component changes are in
[DERIVATION.md](DERIVATION.md#hardening-applied-by-component).

## Upstream, Licence and Ownership

The application originates in the OpenTelemetry Demo project, release `2.2.0`, licensed
Apache-2.0. The upstream licence is included as [LICENSE](LICENSE), copied unchanged from the
pinned release. The upstream release contains no NOTICE file, so none is included here.

Upstream wrote the application, its service architecture, its protobuf contracts and its
OpenTelemetry instrumentation. This project owns the container definitions as modified here,
the delivery pipeline and its scanning, and the derivation and evidence records, as the
[ownership boundary](DERIVATION.md#ownership-boundary) sets out.

Twenty-two container definitions are modified, each carrying an Apache-2.0 modification
notice: the seventeen component definitions and five auxiliary ones changed only in their
paths. Twenty-five further upstream-derived files carry recorded project changes to
application source, dependency or version metadata, or build files. Every other
upstream-derived file in `services/`, `pb/` and `LICENSE` is byte-identical to the pinned
release, and [DERIVATION.md](DERIVATION.md#reproducing-this-tree) shows how to reproduce and
check that comparison.

The licence lets you use, study and adapt this work: keep its notices and the upstream
attribution, and mark the files you change.

## Feedback

The record is meant to be checked rather than taken on trust: the Git history, the merge
requests and their pipelines on GitLab, DERIVATION.md and SERVICE-INVENTORY.md show what
changed, when, and with what result. Issues and merge requests are welcome on the
[GitLab repository](https://gitlab.com/tuinzaman/cloud-platform-workload), where review
happens.
