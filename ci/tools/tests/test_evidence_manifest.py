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
PIPELINE_ID = "2827817067"
CREATED_AT = "2026-09-07T20:36:40Z"
VERSION = "1.4.2"
READABLE = "2026.09.07-build.2827817067-v1.4.2"


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

    def __init__(self, root, trivy=None, sbom=None, manifest=None, digest=None, gate_rc="0", db=True,
                 version_text=VERSION + "\n", readable=READABLE, tags_text=None):
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
        if version_text is not None:
            (self.root / "release-version.txt").write_text(version_text)
        (self.root / "readable-tag.txt").write_text(readable + "\n")
        if tags_text is None:
            tags_text = f"{COMMIT[:8]} {self.digest}\n{readable} {self.digest}\n"
        (self.root / "published-tags.txt").write_text(tags_text)

    def write(self, name, obj):
        path = self.root / name
        path.write_bytes(obj if isinstance(obj, bytes) else json.dumps(obj).encode())

    def argv(self, out_dir, **overrides):
        argv = [
            "--component", "shipping",
            "--source-commit", COMMIT,
            "--pipeline-id", PIPELINE_ID,
            "--pipeline-created-at", CREATED_AT,
            "--release-version-file", str(self.root / "release-version.txt"),
            "--readable-tag-file", str(self.root / "readable-tag.txt"),
            "--published-tags-file", str(self.root / "published-tags.txt"),
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
            [
                "evidence-manifest.json",
                "published-tags.txt",
                "readable-tag.txt",
                "registry-manifest.json",
                "release-version.txt",
                "sbom.cdx.json",
                "trivy-db-metadata.json",
                "trivy-findings.json",
                "trivy-gate-rc.txt",
            ],
            names,
        )
        m = self.read_manifest(b.digest)
        self.assertEqual(3, m["schema_version"])
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


    def test_gate_exit_status_is_retained_as_bytes_not_only_asserted(self):
        """Schema 2: the gate claim is checkable from the bundle instead of taken on trust."""
        b = Bundle(self.root / "in")
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        retained = (self.bundle_path(b.digest) / "trivy-gate-rc.txt").read_bytes()
        self.assertEqual((b.root / "gate-rc.txt").read_bytes(), retained)
        m = self.read_manifest(b.digest)
        self.assertEqual("0", m["gate_rc"])
        self.assertEqual(hashlib.sha256(retained).hexdigest(), m["gate_rc_sha256"])
        self.assertEqual("OBSERVED-EXIT-STATUS-OF-THE-BLOCKING-SCAN-PASS", m["gate_result_basis"])

    def test_database_metadata_is_retained_as_bytes_and_sourced(self):
        b = Bundle(self.root / "in")
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        retained = (self.bundle_path(b.digest) / "trivy-db-metadata.json").read_bytes()
        self.assertEqual((b.root / "db.json").read_bytes(), retained)
        m = self.read_manifest(b.digest)
        self.assertEqual("trivy-db-metadata.json", m["vulnerability_db_metadata_source"])
        self.assertEqual(hashlib.sha256(retained).hexdigest(), m["vulnerability_db_metadata_sha256"])

    def test_absent_database_metadata_retains_no_file_and_says_so(self):
        b = Bundle(self.root / "in", db=False)
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        self.assertFalse((self.bundle_path(b.digest) / "trivy-db-metadata.json").exists())
        m = self.read_manifest(b.digest)
        self.assertEqual("UNAVAILABLE", m["vulnerability_db_metadata_source"])
        self.assertIsNone(m["vulnerability_db_metadata"])
        self.assertIsNone(m["vulnerability_db_metadata_sha256"])

    def test_promotion_eligible_carries_an_explicit_basis(self):
        b = Bundle(self.root / "in")
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        m = self.read_manifest(b.digest)
        self.assertTrue(m["promotion_eligible"])
        basis = m["promotion_eligible_basis"]
        self.assertIn("gate exited 0", basis)
        self.assertIn("trivy-gate-rc.txt", basis)
        self.assertIn("sha256 of the retained registry manifest bytes", basis)

    def test_a_failed_gate_still_produces_no_bundle_under_schema_2(self):
        """Retaining the exit status must not turn a blocking failure into a recorded one."""
        b = Bundle(self.root / "in", gate_rc="1")
        self.assertEqual(1, em.main(b.argv(self.root / "out")))
        self.assertFalse((self.root / "out").exists())

    def test_schema_1_bundles_stay_readable_and_are_not_relabelled(self):
        """A historical bundle is a record of what it measured; nothing here rewrites it."""
        legacy = {
            "_fixture": FIXTURE_MARK,
            "schema_version": 1,
            "component": "shipping",
            "published_image_digest": "sha256:" + "b" * 64,
            "published_digest_binding": "DIRECT",
            "gate_result": "PASS",
            "gate_result_basis": "OBSERVED-EXIT-STATUS-OF-THE-BLOCKING-SCAN-PASS",
        }
        path = self.root / "legacy-evidence-manifest.json"
        path.write_text(json.dumps(legacy, indent=2, sort_keys=True) + "\n")
        before = path.read_bytes()
        loaded = json.loads(path.read_text())
        self.assertEqual(1, loaded["schema_version"])
        self.assertEqual("DIRECT", loaded["published_digest_binding"])
        self.assertNotIn("promotion_eligible_basis", loaded)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(3, em.SCHEMA_VERSION)

    def test_new_bundle_files_are_covered_by_the_identity_refusal(self):
        """The overwrite guard must cover the schema 2 files, not just the original three."""
        b = Bundle(self.root / "in")
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        (self.bundle_path(b.digest) / "trivy-gate-rc.txt").write_bytes(b"0\n\n")
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_readable_tag_is_retained_with_version_pipeline_commit_and_digest(self):
        """Schema 3: one bundle names the version, both tags, the pipeline, the commit and the digest."""
        b = Bundle(self.root / "in")
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        m = self.read_manifest(b.digest)
        self.assertEqual(
            (VERSION, READABLE, COMMIT[:8], PIPELINE_ID, COMMIT, b.digest, CREATED_AT),
            (m["release_version"], m["readable_tag"], m["commit_tag"], m["pipeline_id"], m["source_commit"],
             m["published_image_digest"], m["pipeline_created_at"]),
        )
        self.assertEqual(
            [{"tag": COMMIT[:8], "digest": b.digest}, {"tag": READABLE, "digest": b.digest}], m["published_tags"]
        )
        bundle = self.bundle_path(b.digest)
        for name in ("release-version.txt", "readable-tag.txt", "published-tags.txt"):
            self.assertEqual((b.root / name).read_bytes(), (bundle / name).read_bytes(), name)

    def test_missing_release_version_fails(self):
        b = Bundle(self.root / "in", version_text=None)
        self.assertEqual(1, em.main(b.argv(self.root / "out")))
        self.assertFalse((self.root / "out").exists())

    def test_invalid_release_versions_fail(self):
        for i, text in enumerate(("v1.4.2\n", "1.4\n", "01.4.2\n", "1.4.2-rc.1\n", "1.4.2\n1.4.3\n", "1.4.2\n\n", "1.4.2",
                                  " 1.4.2\n")):
            with self.subTest(text=text):
                b = Bundle(self.root / f"invalid-{i}", version_text=text,
                           readable=f"2026.09.07-build.{PIPELINE_ID}-v{text.strip()}")
                self.assertEqual(1, em.main(b.argv(self.root / "out-invalid")))
        self.assertFalse((self.root / "out-invalid").exists())

    def test_readable_tag_that_does_not_follow_the_pipeline_fails(self):
        for readable in (
            "2026.09.08-build.2827817067-v1.4.2",
            "2026.09.07-build.2827817068-v1.4.2",
            "2026.09.07-build.2827817067-v1.4.3",
            "2026-09-07-build.2827817067-v1.4.2",
        ):
            with self.subTest(readable=readable):
                b = Bundle(self.root / readable, readable=readable)
                self.assertEqual(1, em.main(b.argv(self.root / "out-mismatch")))
        self.assertFalse((self.root / "out-mismatch").exists())

    def test_creation_time_that_is_not_a_real_utc_timestamp_fails(self):
        b = Bundle(self.root / "in")
        for created in ("2026-09-07T22:36:40+02:00", "", "2026-99-99TgarbageZ", "2026-02-30T00:00:00Z", "2026-02-29T12:00:00Z",
                        "2100-02-29T12:00:00Z", "2026-04-31T00:00:00Z", "2026-09-07T24:00:00Z", "2026-09-07T20:36:60Z",
                        "2026-09-07T20:36:40.123Z", "0999-09-07T20:36:40Z", "2026-09-07T20:36:40Z\n2026-09-08T00:00:00Z"):
            with self.subTest(created=created):
                self.assertEqual(1, em.main(b.argv(self.root / "out", pipeline_created_at=created)))
        self.assertFalse((self.root / "out").exists())

    def test_a_real_leap_day_is_accepted(self):
        readable = f"2028.02.29-build.{PIPELINE_ID}-v{VERSION}"
        b = Bundle(self.root / "in", readable=readable)
        self.assertEqual(0, em.main(b.argv(self.root / "out", pipeline_created_at="2028-02-29T12:00:00Z")))
        self.assertEqual(readable, self.read_manifest(b.digest)["readable_tag"])

    def test_published_tags_at_another_digest_fail(self):
        b = Bundle(self.root / "in")
        other = "sha256:" + "e" * 64
        b.root.joinpath("published-tags.txt").write_text(f"{COMMIT[:8]} {b.digest}\n{READABLE} {other}\n")
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_commit_tag_that_is_not_the_source_commit_fails(self):
        b = Bundle(self.root / "in")
        b.root.joinpath("published-tags.txt").write_text(f"deadbeef {b.digest}\n{READABLE} {b.digest}\n")
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

    def test_tag_files_are_covered_by_the_identity_refusal(self):
        b = Bundle(self.root / "in")
        self.assertEqual(0, em.main(b.argv(self.root / "out")))
        (self.bundle_path(b.digest) / "readable-tag.txt").write_bytes(b"2026.09.07-build.1-v1.4.2\n")
        self.assertEqual(1, em.main(b.argv(self.root / "out")))

if __name__ == "__main__":
    unittest.main()
