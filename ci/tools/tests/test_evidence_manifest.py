#!/usr/bin/env python3
"""Fixture tests for the evidence manifest generator.

Every fixture below is synthetic and generated at run time:

    TEST FIXTURE - NOT HISTORICAL EVIDENCE - NOT SECURITY EVIDENCE

Nothing here reads or writes a real evidence tree. The registry manifest fixture is hashed
into its own digest so the self-proving check is exercised for real rather than stubbed.
"""

import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import evidence_manifest as em  # noqa: E402

COMMIT = "7890d4bb6f8427899ca2224a9281a51e822b4994"
CONFIG = "sha256:" + "a" * 64
FIXTURE_MARK = "TEST FIXTURE - NOT HISTORICAL EVIDENCE - NOT SECURITY EVIDENCE"


def trivy_report(config=CONFIG, tags=None, vulns=None):
    return {
        "_fixture": FIXTURE_MARK,
        "SchemaVersion": 2,
        "Trivy": {"Version": "0.70.0"},
        "CreatedAt": "2026-09-07T20:36:44.017933945Z",
        "ArtifactName": "image.tar",
        "Metadata": {
            "ImageID": config,
            "RepoTags": tags if tags is not None else ["shipping:7890d4bb"],
            "OS": {"Family": "debian", "Name": "13.6"},
        },
        "Results": [{"Target": "image.tar (debian 13.6)", "Vulnerabilities": vulns or []}],
    }


def sbom_doc(config=CONFIG):
    return {
        "_fixture": FIXTURE_MARK,
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": "urn:uuid:5f93eb45-14c6-44c5-b0ab-2b20aa713757",
        "metadata": {
            "component": {
                "type": "container",
                "name": "image.tar",
                "properties": [{"name": "aquasecurity:trivy:ImageID", "value": config}],
            }
        },
    }


def registry_manifest(config=CONFIG, layers=2):
    return {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {"mediaType": "application/vnd.docker.container.image.v1+json", "size": 1, "digest": config},
        "layers": [{"mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip", "size": 1, "digest": "sha256:" + f"{i:064x}"} for i in range(layers)],
    }


class Bundle:
    """Writes one synthetic input set and returns generator arguments for it."""

    def __init__(self, root, trivy=None, sbom=None, manifest=None, digest=None, gate_rc="0", db=True):
        self.root = pathlib.Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        manifest_obj = registry_manifest() if manifest is None else manifest
        manifest_bytes = json.dumps(manifest_obj).encode() if not isinstance(manifest_obj, bytes) else manifest_obj
        self.write("trivy-findings.json", trivy if trivy is not None else trivy_report())
        self.write("sbom.cdx.json", sbom if sbom is not None else sbom_doc())
        (self.root / "registry-manifest.json").write_bytes(manifest_bytes)
        computed = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
        (self.root / "digest.txt").write_text((digest or computed) + "\n")
        (self.root / "gate-rc.txt").write_text(gate_rc + "\n")
        if db:
            self.write("db.json", {"VulnerabilityDB": {"Version": 2, "UpdatedAt": "2026-09-07T12:00:00Z"}})
        self.db = db
        self.digest = digest or computed

    def write(self, name, obj):
        path = self.root / name
        path.write_bytes(obj if isinstance(obj, bytes) else json.dumps(obj).encode())

    def argv(self, out_dir, **overrides):
        argv = [
            "--component", "shipping",
            "--source-commit", COMMIT,
            "--pipeline-id", "2827817067",
            "--trivy", str(self.root / "trivy-findings.json"),
            "--sbom", str(self.root / "sbom.cdx.json"),
            "--registry-manifest", str(self.root / "registry-manifest.json"),
            "--digest-file", str(self.root / "digest.txt"),
            "--gate-rc-file", str(self.root / "gate-rc.txt"),
            "--publication-timestamp", "2026-09-07T20:40:00Z",
            "--out-dir", str(out_dir),
        ]
        if self.db:
            argv += ["--db-metadata", str(self.root / "db.json")]
        for flag, value in overrides.items():
            argv += [f"--{flag.replace('_', '-')}", value]
        return argv


class EvidenceManifestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def bundle_path(self, digest):
        return self.root / "out" / "shipping" / COMMIT / digest.split(":", 1)[-1]

    def read_manifest(self, digest):
        return json.loads((self.bundle_path(digest) / "evidence-manifest.json").read_text())

    def test_happy_path_writes_a_complete_bundle(self):
        b = Bundle(self.root / "in")
        self.assertEqual(0, em.main(b.argv(self.root / "out", scan_job_id="16355432446")))
        names = sorted(p.name for p in self.bundle_path(b.digest).iterdir())
        self.assertEqual(
            ["evidence-manifest.json", "registry-manifest.json", "sbom.cdx.json", "trivy-findings.json"], names
        )
        m = self.read_manifest(b.digest)
        self.assertEqual(1, m["schema_version"])
        self.assertEqual("DIRECT", m["published_digest_binding"])
        self.assertEqual(b.digest, m["published_image_digest"])
        self.assertEqual(CONFIG, m["image_config_digest"])
        self.assertEqual("PASS", m["gate_result"])
        self.assertEqual("0.70.0", m["scanner_version"])
        self.assertEqual("OBSERVED-EXIT-STATUS-OF-THE-BLOCKING-SCAN-PASS", m["gate_result_basis"])
        self.assertTrue(m["promotion_eligible"])
        self.assertEqual("16355432446", m["scan_job_id"])
        for field in em.REQUIRED:
            self.assertTrue(m.get(field), field)

    def test_raw_hashes_match_the_retained_bytes(self):
        b = Bundle(self.root / "in")
        em.main(b.argv(self.root / "out"))
        m = self.read_manifest(b.digest)
        bundle = self.bundle_path(b.digest)
        for name, field in (
            ("trivy-findings.json", "trivy_sha256"),
            ("sbom.cdx.json", "sbom_sha256"),
            ("registry-manifest.json", "registry_manifest_sha256"),
        ):
            self.assertEqual(hashlib.sha256((bundle / name).read_bytes()).hexdigest(), m[field], name)

    def test_severity_counts_separate_fixable_from_total(self):
        vulns = [
            {"Severity": "HIGH", "FixedVersion": "1.2.3"},
            {"Severity": "HIGH"},
            {"Severity": "CRITICAL", "FixedVersion": "4.5.6"},
            {"Severity": "MEDIUM", "FixedVersion": "9"},
        ]
        b = Bundle(self.root / "in", trivy=trivy_report(vulns=vulns))
        em.main(b.argv(self.root / "out"))
        m = self.read_manifest(b.digest)
        self.assertEqual((2, 1, 1, 1), (m["total_high"], m["total_critical"], m["fixable_high"], m["fixable_critical"]))

    def test_byte_identical_retry_is_a_no_op(self):
        b = Bundle(self.root / "in")
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        before = (self.bundle_path(b.digest) / "evidence-manifest.json").read_bytes()
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        self.assertEqual(before, (self.bundle_path(b.digest) / "evidence-manifest.json").read_bytes())

    def test_same_identity_with_different_bytes_is_refused(self):
        b = Bundle(self.root / "in")
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        b.write("trivy-findings.json", trivy_report(vulns=[{"Severity": "HIGH"}]))
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_missing_input_fails(self):
        b = Bundle(self.root / "in")
        (b.root / "sbom.cdx.json").unlink()
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_empty_input_fails(self):
        b = Bundle(self.root / "in")
        (b.root / "trivy-findings.json").write_bytes(b"")
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_malformed_json_fails(self):
        b = Bundle(self.root / "in")
        (b.root / "sbom.cdx.json").write_bytes(b"{not json")
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_manifest_bytes_that_do_not_hash_to_the_digest_fail(self):
        b = Bundle(self.root / "in", digest="sha256:" + "f" * 64)
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_manifest_pointing_at_another_config_fails(self):
        b = Bundle(self.root / "in", manifest=registry_manifest(config="sha256:" + "b" * 64))
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_scan_and_sbom_describing_different_images_fail(self):
        b = Bundle(self.root / "in", sbom=sbom_doc(config="sha256:" + "c" * 64))
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_source_commit_absent_from_repo_tags_fails(self):
        b = Bundle(self.root / "in", trivy=trivy_report(tags=["shipping:deadbeef"]))
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_blocking_gate_failure_produces_no_bundle(self):
        b = Bundle(self.root / "in", gate_rc="1")
        self.assertEqual(1, em.main(b.argv(self.root / "out")))
        self.assertFalse((self.root / "out").exists())

    def test_absent_database_metadata_is_recorded_as_unknown(self):
        b = Bundle(self.root / "in", db=False)
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        m = self.read_manifest(b.digest)
        self.assertIsNone(m["vulnerability_db_metadata"])
        self.assertTrue(any("database metadata UNKNOWN" in line for line in m["limitations"]))

    def test_present_database_metadata_is_captured(self):
        b = Bundle(self.root / "in")
        em.main(b.argv(self.root / "out"))
        m = self.read_manifest(b.digest)
        self.assertEqual("2026-09-07T12:00:00Z", m["vulnerability_db_metadata"]["UpdatedAt"])

    def test_unknown_job_ids_are_null_and_disclosed(self):
        b = Bundle(self.root / "in")
        em.main(b.argv(self.root / "out"))
        m = self.read_manifest(b.digest)
        self.assertIsNone(m["build_job_id"])
        self.assertTrue(any("job ids UNKNOWN" in line for line in m["limitations"]))

    def test_manifest_is_deterministic(self):
        first = Bundle(self.root / "a")
        second = Bundle(self.root / "b")
        em.main(first.argv(self.root / "out1"))
        em.main(second.argv(self.root / "out2"))
        self.assertEqual(
            (self.root / "out1" / "shipping" / COMMIT / first.digest.split(":")[1] / "evidence-manifest.json").read_bytes(),
            (self.root / "out2" / "shipping" / COMMIT / second.digest.split(":")[1] / "evidence-manifest.json").read_bytes(),
        )


if __name__ == "__main__":
    unittest.main()
