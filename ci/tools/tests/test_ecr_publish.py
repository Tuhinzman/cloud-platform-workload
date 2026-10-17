#!/usr/bin/env python3
"""Offline tests of the shared ECR publish template's own script.

The script runs under sh as CI joins it, with aws and docker replaced by a fake immutable
registry that refuses to overwrite a tag. No network, no credential and no AWS call:

    TEST FIXTURE - NOT HISTORICAL EVIDENCE - NOT SECURITY EVIDENCE
"""

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import ci_graph  # noqa: E402

ROOT = str(pathlib.Path(__file__).resolve().parents[3])
COMMIT = "7890d4bb6f8427899ca2224a9281a51e822b4994"
SHORT = COMMIT[:8]
PIPELINE_ID = "2960000001"
CREATED_AT = "2026-01-02T23:59:59Z"
READABLE = "2026.01.02-build.2960000001-v1.4.2"
LOCAL_CONFIG = "sha256:" + "a" * 64
OTHER_CONFIG = "sha256:" + "b" * 64
MEDIA_TYPE = "application/vnd.docker.distribution.manifest.v2+json"

STUB = r'''
import hashlib, json, os, pathlib, sys

state = pathlib.Path(os.environ["FAKE_ECR_STATE"])
fail = set(filter(None, os.environ.get("FAKE_FAIL", "").split(",")))
tool, args = pathlib.Path(sys.argv[0]).name, sys.argv[1:]
with open(state / "calls.log", "a") as log:
    log.write(" ".join([tool] + args[:2]) + "\n")


def load(name):
    return json.loads((state / name).read_text())


def save(name, obj):
    (state / name).write_text(json.dumps(obj))


def opt(flag):
    return args[args.index(flag) + 1]


tags, images, local = load("tags.json"), load("images.json"), load("local.json")
if tool == "docker":
    if args[:2] == ["image", "inspect"]:
        print(local["config"])
    elif args[0] == "login":
        sys.stdin.read()
    elif args[0] == "push":
        if "push" in fail:
            sys.exit("push failed")
        tag = args[1].rsplit(":", 1)[1]
        if tag in tags:
            sys.exit(f"tag invalid: {tag} already exists and the repository is immutable")
        manifest = json.dumps({
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {"mediaType": "application/vnd.docker.container.image.v1+json", "size": 1469,
                       "digest": local["config"]},
            "layers": [{"mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip", "size": 100,
                        "digest": "sha256:" + "1" * 64}],
        }, indent=3)
        digest = "sha256:" + hashlib.sha256(manifest.encode()).hexdigest()
        tags[tag], images[digest], local["pushed"] = digest, [manifest, "application/vnd.docker.distribution.manifest.v2+json"], digest
        save("tags.json", tags), save("images.json", images), save("local.json", local)
    elif args[0] == "inspect":
        print(f"{os.environ['ECR_REGISTRY']}/{os.environ['ECR_REPOSITORY']}@{local.get('pushed', '')}")
    elif args[0] not in ("load", "tag"):
        sys.exit(f"unexpected docker call {args}")
elif args[:2] == ["sts", "assume-role-with-web-identity"]:
    print("fake-key\tfake-secret\tfake-session")
elif args[:2] == ["ecr", "get-login-password"]:
    print("fake-password")
elif args[:2] == ["ecr", "batch-get-image"]:
    if "lookup" in fail:
        sys.exit("An error occurred (ThrottlingException) when calling the BatchGetImage operation")
    kind, _, value = opt("--image-ids").partition("=")
    digest = tags.get(value) if kind == "imageTag" else (value if value in images else None)
    if "readback" in fail and kind == "imageTag" and digest:
        digest = "sha256:" + "9" * 64
    query = opt("--query")
    if query == "[images[0].imageId.imageDigest, failures[0].failureCode]":
        code = "RepositoryNotFoundException" if "code" in fail else "ImageNotFound"
        print(f"{digest}\tNone" if digest else f"None\t{code}")
    elif query == "images[0].imageId.imageDigest":
        print(digest or "None")
    elif query == "images[0].imageManifest":
        manifest = images[digest][0] if digest in images and "nomanifest" not in fail else "None"
        print(manifest.replace('"size": 100', '"size": 101') if "badbytes" in fail else manifest)
    elif query == "images[0].imageManifestMediaType":
        print(images[digest][1] if digest in images else "None")
    else:
        sys.exit(f"unexpected query {query}")
elif args[:2] == ["ecr", "put-image"]:
    if "put" in fail:
        sys.exit("An error occurred (ServerException) when calling the PutImage operation")
    tag, digest = opt("--image-tag"), opt("--image-digest")
    manifest = pathlib.Path(opt("--image-manifest").removeprefix("file://")).read_text()
    if "sha256:" + hashlib.sha256(manifest.encode()).hexdigest() != digest:
        sys.exit("ImageDigestDoesNotMatchException")
    if tag in tags:
        sys.exit("ImageTagAlreadyExistsException")
    tags[tag] = digest
    save("tags.json", tags)
    print(digest)
else:
    sys.exit(f"unexpected aws call {args}")
'''


def manifest_for(config):
    return json.dumps({
        "schemaVersion": 2,
        "mediaType": MEDIA_TYPE,
        "config": {"mediaType": "application/vnd.docker.container.image.v1+json", "size": 1469, "digest": config},
        "layers": [{"mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip", "size": 100,
                    "digest": "sha256:" + "2" * 64}],
    }, indent=3)


def template_script(name):
    return "\n".join(ci_graph.resolve(ci_graph.load_config(ROOT), name)["script"])


class Publish(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)
        self.state, self.bin = self.tmp / "state", self.tmp / "bin"
        for d in (self.state, self.bin):
            d.mkdir()
        for tool in ("aws", "docker"):
            stub = self.bin / tool
            stub.write_text(f"#!{sys.executable}\n{STUB}")
            stub.chmod(0o755)
        self.save("tags.json", {})
        self.save("images.json", {})
        self.save("local.json", {"config": LOCAL_CONFIG})

    def save(self, name, obj):
        (self.state / name).write_text(json.dumps(obj))

    def load(self, name):
        return json.loads((self.state / name).read_text())

    def seed(self, tag, config):
        manifest = manifest_for(config)
        digest = "sha256:" + hashlib.sha256(manifest.encode()).hexdigest()
        images, tags = self.load("images.json"), self.load("tags.json")
        images[digest], tags[tag] = [manifest, MEDIA_TYPE], digest
        self.save("images.json", images)
        self.save("tags.json", tags)
        return digest

    def run_publish(self, version_text="1.4.2\n", fail="", **env):
        # Each run gets a fresh workspace, as a retried GitLab job does; the registry state persists.
        self.job = pathlib.Path(tempfile.mkdtemp(dir=self.tmp, prefix="job-"))
        version = self.job / "services" / "frontend-proxy" / "VERSION"
        version.parent.mkdir(parents=True)
        if version_text is not None:
            version.write_text(version_text)
        base = {
            "PATH": f"{self.bin}:{os.environ['PATH']}", "HOME": str(self.tmp), "FAKE_ECR_STATE": str(self.state),
            "FAKE_FAIL": fail, "SERVICE_NAME": "frontend-proxy", "SERVICE_PATH": "services/frontend-proxy",
            "ECR_REGISTRY": "registry.invalid", "ECR_REPOSITORY": "astroshop/frontend-proxy", "AWS_REGION": "us-east-1",
            "AWS_ROLE_ARN": "fake-role", "AWS_ID_TOKEN": "fake-id-token", "CI_PROJECT_ID": "1",
            "CI_PIPELINE_ID": PIPELINE_ID, "CI_PIPELINE_CREATED_AT": CREATED_AT, "CI_COMMIT_SHA": COMMIT,
            "CI_COMMIT_SHORT_SHA": SHORT, "CI_JOB_ID": "17000000001",
        }
        base.update(env)
        program = "set -e\n" + template_script(".ecr-publish-template")
        return subprocess.run(["sh", "-c", program], cwd=self.job, env=base, capture_output=True, text=True,
                              timeout=60)

    def calls(self, prefix):
        log = self.state / "calls.log"
        return [] if not log.exists() else [c for c in log.read_text().splitlines() if c.startswith(prefix)]

    def assert_published(self, r, readable=READABLE, version="1.4.2"):
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        published = (self.job / "digest.txt").read_text().strip()
        manifest = (self.job / "registry-manifest.json").read_bytes()
        self.assertEqual(published, "sha256:" + hashlib.sha256(manifest).hexdigest())
        tags = self.load("tags.json")
        self.assertEqual((published, published), (tags[SHORT], tags[readable]))
        self.assertEqual(f"{SHORT} {published}\n{readable} {published}\n", (self.job / "published-tags.txt").read_text())
        self.assertEqual(readable + "\n", (self.job / "readable-tag.txt").read_text())
        self.assertEqual(version + "\n", (self.job / "release-version.txt").read_text())
        return published

    def assert_refused(self, r, tags_before=None):
        self.assertNotEqual(0, r.returncode, r.stdout)
        self.assertIn("FAIL:", r.stdout)
        self.assertFalse((self.job / "digest.txt").exists(), "a refused publication must not look complete")
        if tags_before is not None:
            self.assertEqual(tags_before, self.load("tags.json"), "no tag may be written or overwritten")

    def test_valid_version_publishes_both_tags_at_one_digest(self):
        self.assert_published(self.run_publish())
        self.assertEqual(1, len(self.calls("docker push")))
        self.assertEqual(1, len(self.calls("aws ecr put-image")), "the readable tag is added, never pushed again")

    def test_readable_name_uses_the_pipeline_creation_date_not_the_clock(self):
        self.assert_published(self.run_publish())
        self.assertTrue((self.job / "readable-tag.txt").read_text().startswith("2026.01.02-build."))

    def test_missing_version_is_refused_before_any_registry_call(self):
        r = self.run_publish(version_text=None)
        self.assert_refused(r, tags_before={})
        self.assertIn("VERSION is missing", r.stdout)
        self.assertEqual([], self.calls(""))

    def test_invalid_versions_are_refused_before_any_registry_call(self):
        for text in ("v1.4.2\n", "1.4\n", "1.4.2-rc.1\n", "01.4.2\n", " 1.4.2\n", "1.4.2\r\n", "1.4.2\n1.4.3\n",
                     "1.4.2\n\n", "\n", "", "1.4.2.0\n", "1.4.2 # release\n"):
            with self.subTest(text=text):
                r = self.run_publish(version_text=text)
                self.assert_refused(r, tags_before={})
                self.assertEqual([], self.calls(""))

    def test_valid_versions_are_accepted(self):
        for text, version in (("1.4.2", "1.4.2"), ("0.0.0\n", "0.0.0"), ("10.20.30\n", "10.20.30")):
            with self.subTest(text=text):
                self.setUp()
                self.assert_published(self.run_publish(version_text=text),
                                      readable=f"2026.01.02-build.{PIPELINE_ID}-v{version}", version=version)

    def test_a_variable_never_stands_in_for_the_version_file(self):
        overrides = {"VERSION": "9.9.9", "RELEASE_VERSION": "9.9.9", "version": "9.9.9", "version_file": "/dev/null"}
        self.assert_refused(self.run_publish(version_text=None, **overrides), tags_before={})
        self.assert_published(self.run_publish(**overrides))

    def test_a_creation_time_that_is_not_a_real_utc_timestamp_is_refused(self):
        for created in ("2026-01-02T23:59:59+02:00", "", "2026/01/02 23:59:59", "2026-99-99TgarbageZ",
                        "2026-02-30T00:00:00Z", "2026-02-29T12:00:00Z", "2100-02-29T12:00:00Z", "2026-04-31T00:00:00Z",
                        "2026-01-02T24:00:00Z", "2026-01-02T23:59:60Z", "2026-01-02T23:59:59.123Z", "0999-01-02T00:00:00Z",
                        "2026-01-02T23:59:59Z\n2026-01-03T00:00:00Z"):
            with self.subTest(created=created):
                self.assert_refused(self.run_publish(CI_PIPELINE_CREATED_AT=created), tags_before={})
                self.assertEqual([], self.calls(""))

    def test_real_leap_days_are_accepted(self):
        for created in ("2028-02-29T12:00:00Z", "2000-02-29T00:00:00Z"):
            with self.subTest(created=created):
                self.setUp()
                readable = f"{created[:10].replace('-', '.')}-build.{PIPELINE_ID}-v1.4.2"
                self.assert_published(self.run_publish(CI_PIPELINE_CREATED_AT=created), readable=readable)

    def test_a_non_numeric_pipeline_id_is_refused(self):
        for pipeline in ("", "12a", "-1"):
            with self.subTest(pipeline=pipeline):
                self.assert_refused(self.run_publish(CI_PIPELINE_ID=pipeline), tags_before={})

    def test_retry_after_full_publication_is_refused_and_writes_nothing(self):
        self.assert_published(self.run_publish())
        tags = self.load("tags.json")
        r = self.run_publish()
        self.assert_refused(r, tags_before=tags)
        self.assertIn("never adopted or overwritten", r.stdout)
        self.assertEqual(1, len(self.calls("docker push")))
        self.assertEqual(1, len(self.calls("aws ecr put-image")))

    def test_existing_commit_tag_with_the_same_config_and_another_manifest_is_refused(self):
        """Same image config, different manifest digest: a config match proves no binding."""
        self.seed(SHORT, LOCAL_CONFIG)
        tags = self.load("tags.json")
        r = self.run_publish()
        self.assert_refused(r, tags_before=tags)
        self.assertIn("never adopted or overwritten", r.stdout)
        self.assertEqual(([], []), (self.calls("docker push"), self.calls("aws ecr put-image")))

    def test_failed_readable_tagging_is_not_a_publication_and_its_retry_is_refused(self):
        self.assert_refused(self.run_publish(fail="put"))
        tags = self.load("tags.json")
        self.assertNotIn(READABLE, tags)
        self.assert_refused(self.run_publish(), tags_before=tags)
        self.assertEqual(1, len(self.calls("docker push")), "the retry must not push again")

    def test_commit_tag_holding_another_build_is_refused(self):
        self.seed(SHORT, OTHER_CONFIG)
        tags = self.load("tags.json")
        r = self.run_publish()
        self.assert_refused(r, tags_before=tags)
        self.assertIn("never adopted or overwritten", r.stdout)
        self.assertEqual(([], []), (self.calls("docker push"), self.calls("aws ecr put-image")))

    def test_readable_tag_at_another_digest_is_refused(self):
        self.seed(SHORT, LOCAL_CONFIG)
        self.seed(READABLE, OTHER_CONFIG)
        tags = self.load("tags.json")
        r = self.run_publish()
        self.assert_refused(r, tags_before=tags)
        self.assertIn("never adopted or overwritten", r.stdout)
        self.assertEqual([], self.calls("aws ecr put-image"))

    def test_manifest_bytes_that_do_not_hash_to_the_digest_are_never_tagged(self):
        r = self.run_publish(fail="badbytes")
        self.assert_refused(r)
        self.assertIn("does not hash to", r.stdout)
        self.assertEqual([], self.calls("aws ecr put-image"))
        self.assertNotIn(READABLE, self.load("tags.json"))

    def test_readable_tag_without_its_commit_tag_stops_before_any_push(self):
        self.seed(READABLE, LOCAL_CONFIG)
        tags = self.load("tags.json")
        self.assert_refused(self.run_publish(), tags_before=tags)
        self.assertEqual([], self.calls("docker push"))

    def test_registry_failures_never_become_a_publication(self):
        for fail in ("lookup", "code", "push", "readback", "nomanifest"):
            with self.subTest(fail=fail):
                self.setUp()
                r = self.run_publish(fail=fail)
                self.assert_refused(r)
                self.assertNotIn(READABLE, self.load("tags.json"))
                if fail in ("lookup", "code"):
                    self.assertEqual([], self.calls("docker push"))

    @unittest.skipUnless(shutil.which("sha256sum"), "the evidence script checks its bundle with sha256sum")
    def test_evidence_bundle_keeps_the_tags_with_version_pipeline_commit_and_digest(self):
        published = self.assert_published(self.run_publish())
        (self.job / "ci").symlink_to(pathlib.Path(ROOT) / "ci")
        scan = {"Trivy": {"Version": "0.70.0"}, "CreatedAt": "2026-01-02T23:50:00Z",
                "Metadata": {"ImageID": LOCAL_CONFIG, "RepoTags": [f"frontend-proxy:{SHORT}"]}, "Results": []}
        sbom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "metadata": {"component": {
            "properties": [{"name": "aquasecurity:trivy:ImageID", "value": LOCAL_CONFIG}]}}}
        (self.job / "trivy-findings.json").write_text(json.dumps(scan))
        (self.job / "sbom.cdx.json").write_text(json.dumps(sbom))
        (self.job / "trivy-gate-rc.txt").write_text("0\n")
        env = {"PATH": os.environ["PATH"], "SERVICE_NAME": "frontend-proxy", "COMPONENT_CLASS": "project-built-application-service",
               "CI_COMMIT_SHA": COMMIT, "CI_PIPELINE_ID": PIPELINE_ID, "CI_PIPELINE_CREATED_AT": CREATED_AT,
               "CI_JOB_ID": "17000000002", "CI_PROJECT_DIR": str(self.job)}
        r = subprocess.run(["sh", "-c", "set -e\n" + template_script(".evidence-retain-template")], cwd=self.job,
                           env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        bundle = self.job / "evidence" / "frontend-proxy" / COMMIT / published.split(":")[1]
        m = json.loads((bundle / "evidence-manifest.json").read_text())
        self.assertEqual(
            (READABLE, "1.4.2", SHORT, PIPELINE_ID, COMMIT, published),
            (m["readable_tag"], m["release_version"], m["commit_tag"], m["pipeline_id"], m["source_commit"],
             m["published_image_digest"]),
        )
        self.assertIn("published-tags.txt", (bundle / "SHA256SUMS").read_text())


if __name__ == "__main__":
    unittest.main()
