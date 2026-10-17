#!/usr/bin/env python3
"""Assemble and verify one durable provenance bundle for a published artifact.

Pure assembly over files already on disk: no network, no registry call and no scanner run,
so the bundle is reproducible from the retained bytes alone. Every cross-check below is
fatal, because a bundle that cannot close the chain from source commit to published digest
is worse than no bundle: it would look like provenance without being it.
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys

SCHEMA_VERSION = 3

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
    "gate_rc",
    "vulnerability_db_metadata_source",
    "scanner_version",
    "publication_timestamp",
    "promotion_eligible_basis",
    "commit_tag",
    "readable_tag",
    "release_version",
)

# Schema 2 retains the raw basis for two claims schema 1 carried only as derived values: the
# blocking gate's exit status and the vulnerability database the scan actually used. Both were
# already produced and kept as job artifacts; they were simply not copied into the bundle, so a
# reader holding only the bundle had to take those two fields on trust. Nothing else changed,
# and schema 1 bundles are still valid records of what they measured.
GATE_RC_FILE = "trivy-gate-rc.txt"
DB_METADATA_FILE = "trivy-db-metadata.json"

# Schema 3 adds the readable image tag: its version and both tags are checked against
# the pipeline and the published digest, and the three files they come from are retained. The
# version and timestamp rules match ci/templates/ecr-publish.yml.
RELEASE_VERSION_FILE = "release-version.txt"
READABLE_TAG_FILE = "readable-tag.txt"
PUBLISHED_TAGS_FILE = "published-tags.txt"
VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
UTC_TIMESTAMP_PATTERN = re.compile(
    r"[1-9][0-9]{3}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z"
)

PROMOTION_BASIS = (
    "the blocking gate exited 0 as retained in " + GATE_RC_FILE + ", the published digest is the "
    "sha256 of the retained registry manifest bytes, and that manifest declares the image config "
    "the scan and sbom recorded"
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


def db_metadata_raw(path):
    """The database metadata bytes as written by the scan job, or None when it produced none."""
    if not path:
        return None
    p = pathlib.Path(path)
    if not p.is_file():
        return None
    raw = p.read_bytes()
    return raw if raw.strip() else None


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


def one_line(data, what):
    text = data.decode()
    if not text.endswith("\n") or "\n" in text[:-1]:
        raise EvidenceError(f"{what}: expected exactly one line")
    return text[:-1]


def tag_fields(args, published_digest):
    """Both published tags, cross-checked against the pipeline and the published digest."""
    version_raw = read(args.release_version_file, "release version")
    readable_raw = read(args.readable_tag_file, "readable tag")
    tags_raw = read(args.published_tags_file, "published tags")

    version = one_line(version_raw, "release version")
    if not VERSION_PATTERN.fullmatch(version):
        raise EvidenceError(f"release version {version!r} is not MAJOR.MINOR.PATCH")
    created = args.pipeline_created_at
    if not UTC_TIMESTAMP_PATTERN.fullmatch(created):
        raise EvidenceError(f"pipeline creation time {created!r} is not a UTC timestamp YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise EvidenceError(f"pipeline creation time {created!r} names a day that does not exist") from exc
    if not args.pipeline_id.isdigit():
        raise EvidenceError(f"pipeline id {args.pipeline_id!r} is not numeric")
    readable = one_line(readable_raw, "readable tag")
    expected = f"{created[:10].replace('-', '.')}-build.{args.pipeline_id}-v{version}"
    if readable != expected:
        raise EvidenceError(f"readable tag {readable} is not {expected}")
    commit_tag = args.source_commit[:8]
    expected_lines = f"{commit_tag} {published_digest}\n{readable} {published_digest}\n"
    if tags_raw.decode() != expected_lines:
        raise EvidenceError(
            f"published tags do not show {commit_tag} and {readable} both at {published_digest}: "
            f"{tags_raw.decode().splitlines()}"
        )

    fields = {
        "commit_tag": commit_tag,
        "readable_tag": readable,
        "release_version": version,
        "pipeline_created_at": created,
        "published_tags": [
            {"tag": commit_tag, "digest": published_digest},
            {"tag": readable, "digest": published_digest},
        ],
        "published_tags_basis": (
            "the publish job read both tags back from the registry as the published digest, "
            "retained in " + PUBLISHED_TAGS_FILE
        ),
    }
    raw = {RELEASE_VERSION_FILE: version_raw, READABLE_TAG_FILE: readable_raw, PUBLISHED_TAGS_FILE: tags_raw}
    return fields, raw


def build(args):
    trivy_raw = read(args.trivy, "trivy report")
    sbom_raw = read(args.sbom, "sbom")
    manifest_raw = read(args.registry_manifest, "registry manifest")

    trivy = load_json(trivy_raw, "trivy report")
    sbom = load_json(sbom_raw, "sbom")
    registry_manifest = load_json(manifest_raw, "registry manifest")

    published_digest = read(args.digest_file, "published digest").decode().strip()
    gate_rc_raw = read(args.gate_rc_file, "gate exit status")
    gate_rc_text = gate_rc_raw.decode().strip()

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
    tags, tags_raw = tag_fields(args, published_digest)

    counts = severity_counts(trivy)
    db = db_metadata(args.db_metadata)
    db_raw = db_metadata_raw(args.db_metadata)

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
    limitations.append(
        "the tag read-back is the publish job's registry answer; this job makes no registry call"
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
        "gate_rc": gate_rc_text,
        "gate_rc_sha256": sha256(gate_rc_raw),
        "vulnerability_db_metadata_source": DB_METADATA_FILE if db_raw else "UNAVAILABLE",
        "vulnerability_db_metadata_sha256": sha256(db_raw) if db_raw else None,
        "sbom_format": sbom.get("bomFormat"),
        "sbom_spec_version": sbom.get("specVersion"),
        "sbom_serial_number": sbom.get("serialNumber"),
        "publication_timestamp": args.publication_timestamp,
        "promotion_eligible": True,
        "promotion_eligible_basis": PROMOTION_BASIS,
        "limitations": limitations,
    }
    manifest.update(tags)

    missing = [field for field in REQUIRED if not manifest.get(field)]
    if missing:
        raise EvidenceError(f"required manifest fields are empty: {', '.join(missing)}")
    raw = {
        "trivy-findings.json": trivy_raw,
        "sbom.cdx.json": sbom_raw,
        "registry-manifest.json": manifest_raw,
        GATE_RC_FILE: gate_rc_raw,
    }
    if db_raw:
        raw[DB_METADATA_FILE] = db_raw
    raw.update(tags_raw)
    return manifest, raw


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
    parser.add_argument("--pipeline-created-at", required=True)
    parser.add_argument("--release-version-file", required=True)
    parser.add_argument("--readable-tag-file", required=True)
    parser.add_argument("--published-tags-file", required=True)
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
