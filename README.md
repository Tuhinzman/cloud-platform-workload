# Cloud Platform Workload

> Authoritative repository: [GitLab, tuinzaman/cloud-platform-workload](https://gitlab.com/tuinzaman/cloud-platform-workload).
> The copy on GitHub is a read-only mirror. Merge requests and CI run on GitLab only.

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
reported.

## Why We Hardened the Containers

The container definitions came from the upstream demo, which was written to run the demo,
not to supply a platform that admits images by digest and runs them as unprivileged users.
Most bases were referenced by tag instead of digest, and many of those tags float, such as
`golang:1.25-bookworm`, `node:22-slim` and `rust:1.91`, so one commit could build a
different image later. Several images ran as root, and in others the runtime user owned the
application directory and could replace or delete what it ran. Most wrote `EXPOSE` with a
variable that is undefined at build time, which declares nothing, and the scans reported
fixable HIGH and CRITICAL findings that the pipeline's gates block on.

Between 2026-10-13 and 2026-10-16 all seventeen definitions went through a hardening pass.
Each now pins its base images by digest, runs as a numeric non-root user over application
files owned by root, and, where it listens, declares the port it uses. The fixable HIGH and
CRITICAL findings were cleared by moving bases and dependencies, with no scanner exception
or ignore rule. Some examples from the per-component record in
[DERIVATION.md](DERIVATION.md#hardening-applied-by-component):

- Built on an arm64 host for amd64, shipping's earlier definition put an aarch64 binary into
  the amd64 image, which then failed to start. The amd64 target is now cross-compiled, and
  the stage that installed libssl3t64 over the base is gone, because the newest base digest
  ships the fixed package.
- fraud-detection's runtime user owned its application directory and could rename or delete
  the jars it ran. Root now creates that directory, and lz4-java moved to `1.11.4` for
  CVE-2026-106451, a HIGH both scans reported.
- frontend-proxy now `exec`s Envoy, so a stop signal reaches it: `docker stop` returned in
  0 s with exit code 0, where the shell had left it 10 s and exit code 137.
- flagd-ui ran as root and now runs as `nobody`. Its lock moved bandit to 1.13.1 for
  EEF-CVE-2026-105659, a HIGH advisory that OSV and the Hex advisory feed listed while the
  scanner's database did not.

In practice, the base under each build changes only when someone changes its pin, the
processes cannot modify the code they run, and the user and port are explicit for the
platform's security context. Several images still read a moving package index at build
time, which DERIVATION.md records per component.

The application inside these images remains upstream's work. The hardening changed how it
is built, packaged and run; the few source and dependency changes are listed in
DERIVATION.md.

## Current Status

The Dockerfile and merge-request CI milestone is complete for all seventeen components:
each hardened definition was merged through a GitLab merge request, !44 to !54, after its
merge-request pipeline passed. Only the pipelines' overall status is recorded; their job
logs and artifacts have not been inspected for this record. The milestone is not delivery. No hardened image is recorded as published to ECR,
and none is pinned in the deployment repository or run on AWS. Publication, digest binding and
EKS runtime validation of the hardened images remain unverified. ADR-0009 and ADR-0014 govern
these workload images; ADR-0015 governs platform-managed runtime components.

The earlier evidence belongs to images built before the hardening. Checkout, shipping and
quote were each built, scanned, published with an SBOM, read back from the registry by
digest, and exercised inside bounded EKS runtime windows: shipping carries a four-of-four
telemetry signal digest match, and quote's induced fault and recovery were observed end to
end. image-provider was published the same way and has not run in a window. An earlier
frontend-proxy image was published on 2026-09-26 and its digest read back from the registry;
it has not run in a window either. One shipping and one image-provider publication also had
the pipeline retain the provenance itself, keeping the registry manifest bytes whose sha256 is
the published digest, and so did the checkout, shipping, quote and image-provider images
published alongside frontend-proxy's. The bundle the pipeline retained for frontend-proxy
failed verification, so it is not counted as provenance. Every runtime was torn
down, and no runtime is currently live.

[SERVICE-INVENTORY.md](SERVICE-INVENTORY.md) records each component's pipeline coverage,
the tests it actually has and what each result does not show. ADR-0017 selects the full
justified project-built inventory as the target of an owner-selected end-to-end programme;
selecting it is not delivering it, and promotion remains a separate implementation and
validation obligation.

Twenty-two container definitions are modified, each carrying an Apache-2.0 modification
notice: the seventeen component definitions above and five auxiliary ones changed only in
their paths. They are adapted deliberately, for this repository's build layout and for the
platform work this workload exists to exercise.

Beyond those, `checkout` and `product-catalog` carry project modifications to their application
source and their Go dependency metadata, `shipping` to its application source, `quote`,
`payment`, `cart`, `flagd-ui` and `accounting` to their dependency metadata, `email` to its
dependency and Ruby version metadata, `ad` and `fraud-detection` to their Gradle build scripts,
and `frontend` to five application-source files and its npm dependency metadata. Every other
upstream-derived file in the compared scope, including all remaining application source and the
protobuf contract, is byte-identical to the pinned upstream release. That scope is `services/`,
`pb/` and `LICENSE`, and the comparison makes no claim about files outside it.
[DERIVATION.md](DERIVATION.md) is the per-file record of what differs and how to reproduce
the tree.

## Licence and Attribution

The application originates in the OpenTelemetry Demo project, licensed Apache-2.0. The
upstream licence is included as [LICENSE](LICENSE), copied unchanged from the pinned
release. The upstream release contains no NOTICE file, so none is included here.

Upstream wrote the application, its service architecture, its protobuf contracts, and its
OpenTelemetry instrumentation. What this project adds is stated in
[DERIVATION.md](DERIVATION.md) rather than implied here.

## Ownership, Reuse and Feedback

This repository records the platform engineering this project did on the workload: the
container definitions as modified here, the delivery pipeline and its scanning, and the
derivation and evidence records. The application stays upstream's, as the
[ownership boundary](DERIVATION.md#ownership-boundary) sets out. The record is meant to be
checked rather than taken on trust: the Git history, the merge requests and their pipelines
on GitLab, [DERIVATION.md](DERIVATION.md) and [SERVICE-INVENTORY.md](SERVICE-INVENTORY.md)
show what changed, when, and with what result.

The licence above lets you use, study and adapt this work; keep its notices and the
upstream attribution, and mark the files you change. Feedback and suggested improvements are
welcome as issues or merge requests on the
[GitLab repository](https://gitlab.com/tuinzaman/cloud-platform-workload), where review
happens. If the project is useful to you, a star on the
[GitHub mirror](https://github.com/Tuhinzman/cloud-platform-workload) is appreciated and
entirely optional.
