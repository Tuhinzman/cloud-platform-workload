#!/usr/bin/env python3
"""Assemble and verify one durable provenance bundle for a published artifact.

Pure assembly over files already on disk: no network, no registry call and no scanner run,
so the bundle is reproducible from the retained bytes alone. Every cross-check below is
fatal, because a bundle that cannot close the chain from source commit to published digest
is worse than no bundle: it would look like provenance without being it.
"""

import argparse
import hashlib
import json
import pathlib
import sys

SCHEMA_VERSION = 1

REQUIRED = (
    "schema_version",
    "component",
    "component_class",
    "source_commit",
    "pipeline_id",
    "image_config_digest",
    "published_image_digest",
    "registry_manifest_sha256",
    "trivy_sha256",
    "sbom_sha256",
    "gate_result",
    "gate_result_basis",
    "scanner_version",
    "publication_timestamp",
)


class EvidenceError(Exception):
    pass


def read(path, what):
    p = pathlib.Path(path)
    if not p.is_file():
        raise EvidenceError(f"{what}: missing required input {path}")
    data = p.read_bytes()
    if not data:
        raise EvidenceError(f"{what}: empty required input {path}")
    return data


def load_json(data, what):
    try:
        return json.loads(data)
    except ValueError as exc:
        raise EvidenceError(f"{what}: not parseable JSON ({exc})") from exc


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def optional(value):
    value = (value or "").strip()
    return value or None


def severity_counts(report):
    counts = {"high": 0, "critical": 0, "fixable_high": 0, "fixable_critical": 0}
    for result in report.get("Results") or []:
        for vuln in result.get("Vulnerabilities") or []:
            severity = (vuln.get("Severity") or "").upper()
            if severity not in ("HIGH", "CRITICAL"):
                continue
            key = severity.lower()
            counts[key] += 1
            if vuln.get("FixedVersion"):
                counts[f"fixable_{key}"] += 1
    return counts


def sbom_image_id(sbom):
    metadata = sbom.get("metadata") or {}
    component = metadata.get("component") or {}
    for prop in component.get("properties") or []:
        if prop.get("name") == "aquasecurity:trivy:ImageID":
            return prop.get("value")
    return None


def db_metadata(path):
    if not path:
        return None
    p = pathlib.Path(path)
    if not p.is_file() or not p.read_bytes().strip():
        return None
    try:
        payload = json.loads(p.read_bytes())
    except ValueError:
        return None
    db = payload.get("VulnerabilityDB")
    if not isinstance(db, dict):
        return None
    kept = {k: db.get(k) for k in ("Version", "UpdatedAt", "NextUpdate", "DownloadedAt") if db.get(k)}
    return kept or None


def build(args):
    trivy_raw = read(args.trivy, "trivy report")
    sbom_raw = read(args.sbom, "sbom")
    manifest_raw = read(args.registry_manifest, "registry manifest")

    trivy = load_json(trivy_raw, "trivy report")
    sbom = load_json(sbom_raw, "sbom")
    registry_manifest = load_json(manifest_raw, "registry manifest")

    published_digest = read(args.digest_file, "published digest").decode().strip()
    gate_rc_text = read(args.gate_rc_file, "gate exit status").decode().strip()

    meta = trivy.get("Metadata") or {}
    config_digest = meta.get("ImageID")
    repo_tags = meta.get("RepoTags") or []

    # The registry computes its manifest digest over these exact bytes, so recomputing them
    # here is what makes the published digest self-proving rather than merely reported.
    recomputed = "sha256:" + sha256(manifest_raw)
    manifest_config_digest = ((registry_manifest.get("config") or {}).get("digest"))

    if not config_digest:
        raise EvidenceError("trivy report carries no Metadata.ImageID, so the scan cannot be bound to an image")
    if sbom_image_id(sbom) != config_digest:
        raise EvidenceError(
            f"scan and sbom describe different images: {config_digest} vs {sbom_image_id(sbom)}"
        )
    if recomputed != published_digest:
        raise EvidenceError(
            f"registry manifest bytes hash to {recomputed} but the published digest is {published_digest}"
        )
    if manifest_config_digest != config_digest:
        raise EvidenceError(
            f"published manifest points at config {manifest_config_digest}, scanned image was {config_digest}"
        )
    short = args.source_commit[:8]
    if not any(tag.endswith(f":{short}") for tag in repo_tags):
        raise EvidenceError(f"trivy RepoTags {repo_tags} do not carry source commit {short}")
    if gate_rc_text != "0":
        raise EvidenceError(f"blocking security gate exited {gate_rc_text}; no artifact is eligible")

    counts = severity_counts(trivy)
    db = db_metadata(args.db_metadata)

    limitations = []
    if db is None:
        limitations.append(
            "vulnerability database metadata UNKNOWN: the scanner exposed none for this run"
        )
    unknown_jobs = [
        name
        for name, value in (
            ("build", args.build_job_id),
            ("scan", args.scan_job_id),
            ("publish", args.publish_job_id),
            ("evidence", args.evidence_job_id),
        )
        if not optional(value)
    ]
    if unknown_jobs:
        limitations.append(f"job ids UNKNOWN for: {', '.join(unknown_jobs)}")
    limitations.append(
        "the scan and sbom describe the pre-publication image, bound to the published digest "
        "through the image config digest rather than measured against the registry"
    )
    limitations.append(
        "a point-in-time result for the recorded scan timestamp, not a current vulnerability attestation"
    )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "component": args.component,
        "component_class": args.component_class,
        "source_commit": args.source_commit,
        "pipeline_id": args.pipeline_id,
        "build_job_id": optional(args.build_job_id),
        "scan_job_id": optional(args.scan_job_id),
        "publish_job_id": optional(args.publish_job_id),
        "evidence_job_id": optional(args.evidence_job_id),
        "image_repo_tags": repo_tags,
        "image_config_digest": config_digest,
        "published_image_digest": published_digest,
        "published_digest_binding": "DIRECT",
        "published_digest_binding_basis": (
            "sha256 over the retained registry manifest bytes equals the published digest, and that "
            "manifest declares the same image config digest the scan and sbom recorded"
        ),
        "registry_manifest_sha256": sha256(manifest_raw),
        "registry_manifest_media_type": registry_manifest.get("mediaType"),
        "registry_manifest_layers": len(registry_manifest.get("layers") or []),
        "trivy_sha256": sha256(trivy_raw),
        "sbom_sha256": sha256(sbom_raw),
        "scanner": "trivy",
        "scanner_version": (trivy.get("Trivy") or {}).get("Version"),
        "scan_timestamp": trivy.get("CreatedAt"),
        "vulnerability_db_metadata": db,
        "os_family": (meta.get("OS") or {}).get("Family"),
        "os_version": (meta.get("OS") or {}).get("Name"),
        "total_high": counts["high"],
        "total_critical": counts["critical"],
        "fixable_high": counts["fixable_high"],
        "fixable_critical": counts["fixable_critical"],
        "gate_result": "PASS",
        "gate_result_basis": "OBSERVED-EXIT-STATUS-OF-THE-BLOCKING-SCAN-PASS",
        "sbom_format": sbom.get("bomFormat"),
        "sbom_spec_version": sbom.get("specVersion"),
        "sbom_serial_number": sbom.get("serialNumber"),
        "publication_timestamp": args.publication_timestamp,
        "promotion_eligible": True,
        "limitations": limitations,
    }

    missing = [field for field in REQUIRED if not manifest.get(field)]
    if missing:
        raise EvidenceError(f"required manifest fields are empty: {', '.join(missing)}")
    return manifest, {
        "trivy-findings.json": trivy_raw,
        "sbom.cdx.json": sbom_raw,
        "registry-manifest.json": manifest_raw,
    }


def write_bundle(out_dir, component, source_commit, published_digest, manifest, raw):
    bundle = pathlib.Path(out_dir) / component / source_commit / published_digest.split(":", 1)[-1]
    rendered = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    payload = dict(raw)
    payload["evidence-manifest.json"] = rendered

    # Evidence identity is component plus source commit plus published digest. Re-running a
    # job must reproduce it byte for byte; anything else means two different artifacts are
    # claiming one identity, which no later reader could resolve.
    for name, data in payload.items():
        existing = bundle / name
        if existing.is_file() and existing.read_bytes() != data:
            raise EvidenceError(f"{existing} already exists with different bytes for the same evidence identity")

    bundle.mkdir(parents=True, exist_ok=True)
    for name, data in payload.items():
        (bundle / name).write_bytes(data)
    return bundle


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", required=True)
    parser.add_argument("--component-class", default="project-built-application-service")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--pipeline-id", required=True)
    parser.add_argument("--trivy", required=True)
    parser.add_argument("--sbom", required=True)
    parser.add_argument("--registry-manifest", required=True)
    parser.add_argument("--digest-file", required=True)
    parser.add_argument("--gate-rc-file", required=True)
    parser.add_argument("--db-metadata")
    parser.add_argument("--build-job-id")
    parser.add_argument("--scan-job-id")
    parser.add_argument("--publish-job-id")
    parser.add_argument("--evidence-job-id")
    parser.add_argument("--publication-timestamp", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    try:
        manifest, raw = build(args)
        bundle = write_bundle(
            args.out_dir, args.component, args.source_commit, manifest["published_image_digest"], manifest, raw
        )
    except EvidenceError as exc:
        print(f"evidence retention FAILED: {exc}", file=sys.stderr)
        return 1

    print(f"evidence bundle written to {bundle}")
    print(f"published digest {manifest['published_image_digest']} binding {manifest['published_digest_binding']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
