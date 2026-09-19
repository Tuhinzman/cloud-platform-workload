"""Which jobs a change instantiates, checked before a pipeline is paid for.

Expected sets are derived from the services' own declarations rather than written down as
numbers, so wiring a new service or tier changes the expectation with it. A test here failing
means a rule change widened or narrowed a blast radius; whichever it was, it is a decision
and not a side effect.
"""

import glob
import os
import sys
import unittest

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ci", "tools"))
import ci_graph  # noqa: E402

CHAIN = ("ci/templates/image.yml", "ci/templates/trivy-scan.yml",
         "ci/templates/ecr-publish.yml", "ci/templates/evidence-retain.yml")
GITLAB_TEMPLATE_JOBS = {"secret_detection"}  # rules live outside this repository


def services():
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "services", "*", "ci.yml"))):
        name = path.split(os.sep)[-2]
        doc = yaml.safe_load(open(path))
        out[name] = {k: v for k, v in doc.items() if not k.startswith(".")}
    return out


def jobs_extending(template):
    return {job for svc in services().values() for job, body in svc.items()
            if body.get("extends") == template}


def evaluate(paths, source="merge_request_event", branch=None, new_branch=False):
    config = ci_graph.load_config(ROOT)
    ctx = {"source": source, "branch": branch, "open_mr": False,
           "new_branch_no_compare": new_branch, "default_branch": "main"}
    jobs, unknown = ci_graph.evaluate(config, paths, ctx)
    assert not unknown, unknown
    return {j["job"] for j in jobs} - GITLAB_TEMPLATE_JOBS


class FanOut(unittest.TestCase):
    def test_service_change_touches_that_service_only(self):
        for name, jobs in services().items():
            with self.subTest(service=name):
                got = evaluate([f"services/{name}/ci.yml"])
                expected = {j for j in jobs if j.startswith(f"{name}:")
                            and not j.endswith((":publish", ":retain-evidence"))}
                self.assertEqual(got, expected)

    def test_language_tier_change_reaches_its_consumers_only(self):
        for tier in ("go", "node", "php", "rust", "dotnet"):
            with self.subTest(tier=tier):
                got = evaluate([f"ci/templates/lang-{tier}.yml"])
                expected = set()
                for suffix in ("-template", "-test-template", "-parse-template"):
                    expected |= jobs_extending(f".lang-{tier}{suffix}")
                self.assertEqual(got, expected)
                self.assertTrue(expected, f"lang-{tier} has no consumer")

    def test_image_template_change_reaches_every_build_and_health_job(self):
        got = evaluate(["ci/templates/image.yml"])
        expected = jobs_extending(".image-build-template") | jobs_extending(".image-health-template")
        self.assertEqual(got, expected)

    def test_scanner_template_change_rebuilds_only_what_the_scan_needs(self):
        got = evaluate(["ci/templates/trivy-scan.yml"])
        expected = jobs_extending(".trivy-scan-template") | jobs_extending(".image-build-template")
        self.assertEqual(got, expected)

    def test_evidence_template_change_rebuilds_the_artifact_chain_but_not_health(self):
        got = evaluate(["ci/templates/evidence-retain.yml"])
        self.assertIn("evidence-tools:test", got)
        self.assertEqual(got & jobs_extending(".image-health-template"), set())
        self.assertEqual(got & jobs_extending(".image-build-template"), jobs_extending(".image-build-template"))

    def test_docs_only_change_instantiates_no_service_job(self):
        self.assertEqual(evaluate(["README.md", "SERVICE-INVENTORY.md", "DERIVATION.md"]), set())

    def test_root_pipeline_change_alone_instantiates_no_service_job(self):
        self.assertEqual(evaluate([".gitlab-ci.yml"]), set())

    def test_ci_tools_change_runs_the_tool_tests(self):
        self.assertEqual(evaluate(["ci/tools/tests/test_ci_graph.py"]), {"evidence-tools:test"})

    def test_no_shared_template_rule_is_broad(self):
        for path in glob.glob(os.path.join(ROOT, "ci", "templates", "*.yml")):
            text = open(path).read()
            self.assertNotIn("ci/templates/**", text, path)
            self.assertNotIn('".gitlab-ci.yml"', text, path)


class PipelineSelection(unittest.TestCase):
    def test_branch_push_with_open_merge_request_creates_no_pipeline(self):
        config = ci_graph.load_config(ROOT)
        ctx = {"source": "push", "branch": "ci/x", "open_mr": True, "default_branch": "main"}
        self.assertFalse(ci_graph.pipeline_created(config, ctx))

    def test_branch_push_without_merge_request_creates_no_pipeline(self):
        config = ci_graph.load_config(ROOT)
        ctx = {"source": "push", "branch": "ci/x", "open_mr": False, "default_branch": "main"}
        self.assertFalse(ci_graph.pipeline_created(config, ctx))

    def test_merge_request_event_and_main_create_pipelines(self):
        config = ci_graph.load_config(ROOT)
        self.assertTrue(ci_graph.pipeline_created(config, {"source": "merge_request_event", "default_branch": "main"}))
        self.assertTrue(ci_graph.pipeline_created(config, {"source": "push", "branch": "main", "default_branch": "main"}))

    def test_publish_and_evidence_exist_only_on_main(self):
        self.assertEqual(evaluate(["services/shipping/ci.yml"]) & {"shipping:publish", "shipping:retain-evidence"}, set())
        on_main = evaluate(["services/shipping/ci.yml"], source="push", branch="main")
        self.assertIn("shipping:publish", on_main)
        self.assertIn("shipping:retain-evidence", on_main)


if __name__ == "__main__":
    unittest.main()
