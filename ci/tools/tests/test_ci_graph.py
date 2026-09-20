"""Which jobs a change instantiates, and how they depend on each other, checked before a
pipeline is paid for.

Expected sets are derived from the services' own declarations rather than written down as
numbers, so wiring a new service or tier changes the expectation with it. A test here failing
means a rule or dependency change altered a blast radius or an ordering guarantee; whichever
it was, it is a decision and not a side effect.

The security invariant is the reason this file exists: a publish job must never be able to
exist in a pipeline that does not also contain the blocking scan in front of it.
"""

import copy
import glob
import os
import sys
import unittest

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ci", "tools"))
import ci_graph  # noqa: E402

CHAIN_TEMPLATES = {
    "ci/templates/image.yml": ".image-build-template",
    "ci/templates/trivy-scan.yml": ".trivy-scan-template",
    "ci/templates/ecr-publish.yml": ".ecr-publish-template",
    "ci/templates/evidence-retain.yml": ".evidence-retain-template",
}
# The source gate shares trivy-scan.yml with the image gate, so it is checked against the
# same path list rather than counted as a fifth file.
SOURCE_SCAN_TEMPLATE = ".trivy-source-scan-template"
ROOT_FILE_ALLOWED_KEYS = {"include", "workflow", "stages", "variables", "secret_detection"}
ROOT_FILE_ALLOWED_VARIABLES = {"AST_ENABLE_MR_PIPELINES"}
GITLAB_TEMPLATE_JOBS = {"secret_detection"}
CONTROL_JOB = "evidence-tools:test"


def services():
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "services", "*", "ci.yml"))):
        name = path.split(os.sep)[-2]
        out[name] = {k: v for k, v in yaml.safe_load(open(path)).items() if not k.startswith(".")}
    return out


def jobs_extending(template):
    return {job for svc in services().values() for job, body in svc.items()
            if body.get("extends") == template}


def evaluate(paths, source="merge_request_event", branch=None, new_branch=False, config=None):
    config = config or ci_graph.load_config(ROOT)
    ctx = {"source": source, "branch": branch, "open_mr": False,
           "new_branch_no_compare": new_branch, "default_branch": "main"}
    jobs, unknown = ci_graph.evaluate(config, paths, ctx)
    assert not unknown, unknown
    return {j["job"] for j in jobs} - GITLAB_TEMPLATE_JOBS, config, jobs


def names(paths, **kw):
    return evaluate(paths, **kw)[0]


class PublishSecurityInvariant(unittest.TestCase):
    """publish ⇒ its build and its blocking scan, in every reachable change-set."""

    def publishers(self):
        return {job.split(":")[0] for job in jobs_extending(".ecr-publish-template")}

    def test_every_publisher_declares_its_scan_as_a_mandatory_need(self):
        for svc in self.publishers():
            with self.subTest(service=svc):
                job = yaml.safe_load(open(os.path.join(ROOT, "services", svc, "ci.yml")))[f"{svc}:publish"]
                needed = dict(ci_graph.needs_of(job))
                self.assertIn(f"{svc}:scan-image", needed, "publish must need its scan")
                self.assertFalse(needed[f"{svc}:scan-image"], "the scan need must not be optional")
                self.assertIn(f"{svc}:build", needed, "publish must need its build")
                self.assertFalse(needed[f"{svc}:build"], "the build need must not be optional")
                self.assertIn(f"{svc}:scan-source", needed, "publish must need its source gate")
                self.assertFalse(needed[f"{svc}:scan-source"],
                                 "the source gate need must not be optional")

    def test_publish_never_appears_without_its_scan_in_any_changeset(self):
        probes = [[p] for p in (
            ".gitlab-ci.yml", "README.md", "pb/demo.proto", "ci/tools/ci_graph.py",
            *CHAIN_TEMPLATES, *sorted(glob.glob("ci/templates/lang-*.yml")),
        )] + [[f"services/{s}/ci.yml"] for s in services()]
        for source, branch in (("merge_request_event", None), ("push", "main")):
            for paths in probes:
                got, _, _ = evaluate(paths, source=source, branch=branch)
                for job in got:
                    if job.endswith(":publish"):
                        svc = job.split(":")[0]
                        self.assertIn(f"{svc}:scan-image", got,
                                      f"{paths} on {source}: {job} without its scan")
                        self.assertIn(f"{svc}:build", got,
                                      f"{paths} on {source}: {job} without its build")
                        self.assertIn(f"{svc}:scan-source", got,
                                      f"{paths} on {source}: {job} without its source gate")

    def test_evidence_never_appears_without_its_scan_and_publish(self):
        for source, branch in (("merge_request_event", None), ("push", "main")):
            for path in list(CHAIN_TEMPLATES) + [".gitlab-ci.yml"]:
                got, _, _ = evaluate([path], source=source, branch=branch)
                for job in got:
                    if job.endswith(":retain-evidence"):
                        svc = job.split(":")[0]
                        self.assertIn(f"{svc}:scan-image", got, f"{path}: evidence without scan")
                        self.assertIn(f"{svc}:scan-source", got,
                                      f"{path}: evidence without its source gate")
                        self.assertIn(f"{svc}:publish", got, f"{path}: evidence without publish")

    def test_the_graph_is_valid_in_every_probed_changeset(self):
        for source, branch in (("merge_request_event", None), ("push", "main")):
            for path in list(CHAIN_TEMPLATES) + [".gitlab-ci.yml", "pb/demo.proto", "README.md"]:
                _, config, jobs = evaluate([path], source=source, branch=branch)
                self.assertEqual(ci_graph.validate_needs(config, jobs), [],
                                 f"{path} on {source} produces a pipeline GitLab would reject")

    def test_removing_the_scan_prerequisite_is_caught(self):
        """The negative control. If the scan stops being instantiated alongside publish, the
        graph must become invalid rather than quietly producing an unscanned publish."""
        config = ci_graph.load_config(ROOT)
        broken = copy.deepcopy(config)
        broken[".trivy-scan-template"]["rules"] = [{"changes": ["ci/templates/trivy-scan.yml"]}]
        ctx = {"source": "push", "branch": "main", "open_mr": False,
               "new_branch_no_compare": False, "default_branch": "main"}
        jobs, _ = ci_graph.evaluate(broken, ["ci/templates/ecr-publish.yml"], ctx)
        present = {j["job"] for j in jobs}
        self.assertTrue(any(j.endswith(":publish") for j in present), "probe must reach publish")
        self.assertFalse(any(j.endswith(":scan-image") for j in present), "probe must drop the scan")
        errors = ci_graph.validate_needs(broken, jobs)
        self.assertTrue(errors, "a publish with no scan in the pipeline must be reported invalid")
        self.assertTrue(any("scan-image" in e for e in errors), errors)

    def test_chain_templates_share_one_path_list(self):
        """The defect this file was written for was two chain rules drifting apart."""
        lists = {}
        for path, key in CHAIN_TEMPLATES.items():
            rule = yaml.safe_load(open(os.path.join(ROOT, path)))[key]["rules"][0]
            lists[path] = rule["changes"]
        first = next(iter(lists.values()))
        for path, value in lists.items():
            self.assertEqual(value, first, f"{path} has drifted from the shared chain list")


class FanOut(unittest.TestCase):
    def test_service_change_touches_that_service_only(self):
        for name, jobs in services().items():
            with self.subTest(service=name):
                got = names([f"services/{name}/ci.yml"])
                expected = {j for j in jobs if j.startswith(f"{name}:")
                            and not j.endswith((":publish", ":retain-evidence"))}
                self.assertEqual(got, expected | {CONTROL_JOB})

    def test_language_tier_change_reaches_its_consumers_only(self):
        for tier in ("go", "node", "php", "rust", "dotnet"):
            with self.subTest(tier=tier):
                expected = set()
                for suffix in ("-template", "-test-template", "-parse-template"):
                    expected |= jobs_extending(f".lang-{tier}{suffix}")
                self.assertEqual(names([f"ci/templates/lang-{tier}.yml"]), expected | {CONTROL_JOB})
                self.assertTrue(expected, f"lang-{tier} has no consumer")

    def test_chain_template_change_reaches_the_whole_chain(self):
        build = jobs_extending(".image-build-template")
        scan = jobs_extending(".trivy-scan-template")
        for path in CHAIN_TEMPLATES:
            with self.subTest(template=path):
                got = names([path])
                self.assertEqual(got & build, build)
                self.assertEqual(got & scan, scan)

    def test_health_is_not_dragged_in_by_the_publish_chain(self):
        health = jobs_extending(".image-health-template")
        self.assertEqual(names(["ci/templates/ecr-publish.yml"]) & health, set())
        self.assertEqual(names(["ci/templates/image.yml"]) & health, health)

    def test_docs_only_change_instantiates_no_service_job(self):
        self.assertEqual(names(["README.md", "SERVICE-INVENTORY.md", "DERIVATION.md"]), set())

    def test_shared_proto_reaches_its_declared_consumers_only(self):
        """pb/ is copied by six services and compiled by one. A service is rebuilt by a proto
        change only where it declares SERVICE_SHARED_INPUTS, so the expectation is derived
        from those declarations rather than from a list kept here."""
        consumers = {name for name, jobs in services().items()
                     if any("pb/" in str((body.get("variables") or {}).get("SERVICE_SHARED_INPUTS", ""))
                            for body in jobs.values())}
        declared = {name for name, body in services().items()
                    if "pb/" in open(os.path.join(ROOT, "services", name, "ci.yml")).read()}
        consumers |= declared
        got = names(["pb/demo.proto"])
        self.assertTrue(got, "a proto change must reach at least its declared consumers")
        self.assertEqual({j.split(":")[0] for j in got}, consumers)

    def test_every_graph_affecting_change_runs_the_graph_tests(self):
        """The guard was previously gated on a rule that excluded the files it guards."""
        paths = (["ci/tools/ci_graph.py", "ci/tools/tests/test_ci_graph.py", ".gitlab-ci.yml"]
                 + sorted("ci/templates/" + os.path.basename(p)
                          for p in glob.glob(os.path.join(ROOT, "ci", "templates", "*.yml")))
                 + [f"services/{s}/ci.yml" for s in services()])
        for path in paths:
            with self.subTest(path=path):
                self.assertIn(CONTROL_JOB, names([path]), f"{path} must run the graph tests")


class RootFileOwnership(unittest.TestCase):
    """The root file is orchestration. Anything that changes how a service job executes
    belongs to the template that owns that job, because the rules cannot see the root file."""

    def test_root_file_carries_only_orchestration(self):
        root = yaml.safe_load(open(os.path.join(ROOT, ".gitlab-ci.yml")))
        self.assertEqual(set(root) - ROOT_FILE_ALLOWED_KEYS, set())

    def test_root_variables_do_not_reach_service_jobs(self):
        root = yaml.safe_load(open(os.path.join(ROOT, ".gitlab-ci.yml")))
        self.assertEqual(set(root.get("variables") or {}) - ROOT_FILE_ALLOWED_VARIABLES, set())

    def test_root_declares_no_default_section(self):
        root = yaml.safe_load(open(os.path.join(ROOT, ".gitlab-ci.yml")))
        self.assertNotIn("default", root)

    def test_no_service_facing_rule_is_broad(self):
        """A service job must never be instantiated by an unrelated template edit. The
        control job is exempt by design: watching broadly is its purpose."""
        for path in glob.glob(os.path.join(ROOT, "ci", "templates", "*.yml")):
            for key, body in (yaml.safe_load(open(path)) or {}).items():
                if not key.startswith("."):
                    continue  # concrete jobs here are controls, not service jobs
                for rule in body.get("rules") or []:
                    paths = rule.get("changes") or []
                    paths = paths.get("paths", []) if isinstance(paths, dict) else paths
                    for pattern in paths:
                        self.assertNotIn("ci/templates/**", pattern, f"{path}:{key}")
                        self.assertNotEqual(pattern, ".gitlab-ci.yml", f"{path}:{key}")


class PipelineSelection(unittest.TestCase):
    def test_branch_push_creates_no_pipeline_with_or_without_a_merge_request(self):
        config = ci_graph.load_config(ROOT)
        for open_mr in (True, False):
            ctx = {"source": "push", "branch": "ci/x", "open_mr": open_mr, "default_branch": "main"}
            self.assertFalse(ci_graph.pipeline_created(config, ctx))

    def test_merge_request_event_and_main_create_exactly_one_pipeline_each(self):
        config = ci_graph.load_config(ROOT)
        self.assertTrue(ci_graph.pipeline_created(config, {"source": "merge_request_event", "default_branch": "main"}))
        self.assertTrue(ci_graph.pipeline_created(config, {"source": "push", "branch": "main", "default_branch": "main"}))

    def test_publish_and_evidence_exist_only_on_the_default_branch(self):
        self.assertEqual(names(["services/shipping/ci.yml"]) & {"shipping:publish", "shipping:retain-evidence"}, set())
        on_main = names(["services/shipping/ci.yml"], source="push", branch="main")
        self.assertIn("shipping:publish", on_main)
        self.assertIn("shipping:retain-evidence", on_main)

    def test_publish_stays_blocking_manual(self):
        _, _, jobs = evaluate(["services/shipping/ci.yml"], source="push", branch="main")
        publish = [j for j in jobs if j["job"] == "shipping:publish"]
        self.assertEqual([j["when"] for j in publish], ["manual"])
        text = open(os.path.join(ROOT, "ci", "templates", "ecr-publish.yml")).read()
        self.assertNotIn("allow_failure", text)


if __name__ == "__main__":
    unittest.main()


class SourceDependencyGate(unittest.TestCase):
    """ADR-0009 requires image AND dependency scanning. These are the invariants that keep
    the second half of that sentence from degrading into a job that reports nothing."""

    def source_scanned(self):
        return jobs_extending(SOURCE_SCAN_TEMPLATE)

    def test_every_service_that_builds_an_image_also_scans_its_source(self):
        """The gate applies to the artifact chain, which is the same scope the image gate
        has. A service that can produce an artifact must pass both."""
        builders = {job.split(":")[0] for job in jobs_extending(".image-build-template")}
        scanned = {job.split(":")[0] for job in self.source_scanned()}
        self.assertEqual(builders, scanned,
                         "every service with a build job must declare a source scan")

    def test_every_source_scan_declares_its_coverage_expectation(self):
        """A scanner that resolves nothing reports nothing, and nothing looks like clean.
        The declaration is what makes an empty result interpretable."""
        allowed = {"declared", "none"}
        for svc_job in sorted(self.source_scanned()):
            svc = svc_job.split(":")[0]
            with self.subTest(service=svc):
                body = yaml.safe_load(open(os.path.join(ROOT, "services", svc, "ci.yml")))[svc_job]
                declared = (body.get("variables") or {}).get("SOURCE_DEPENDENCIES", "declared")
                self.assertIn(declared, allowed)

    def test_services_declaring_none_are_the_measured_ones_only(self):
        """none is a claim about the service, not an escape hatch. Only components with no
        package manager at all carry it, and adding another one has to be a decision."""
        measured_none = {"frontend-proxy", "image-provider"}
        actual = set()
        for svc_job in self.source_scanned():
            svc = svc_job.split(":")[0]
            body = yaml.safe_load(open(os.path.join(ROOT, "services", svc, "ci.yml")))[svc_job]
            if (body.get("variables") or {}).get("SOURCE_DEPENDENCIES") == "none":
                actual.add(svc)
        self.assertEqual(actual, measured_none)

    def test_the_gate_is_blocking_and_carries_no_escape(self):
        """Read the source template's own script, not the file. Both gates live in one file
        and an earlier version of this test passed while the source gate had been changed to
        --exit-code 0, because the image gate's own --exit-code 1 satisfied it."""
        template = yaml.safe_load(open(os.path.join(ROOT, "ci/templates/trivy-scan.yml")))[SOURCE_SCAN_TEMPLATE]
        self.assertNotIn("allow_failure", template)
        script = "\n".join(template["script"])
        self.assertIn("--ignore-unfixed", script)
        self.assertIn("--severity HIGH,CRITICAL", script)
        self.assertIn("--exit-code 1", script, "the source gate itself must block")
        self.assertIn('exit "${gate_rc}"', script, "the job must carry the gate status")

    def test_each_gate_blocks_on_its_own_command(self):
        """Neither gate may rely on the other's flags. Every blocking trivy invocation in
        this file is checked individually so a weakened one cannot hide behind a strict one."""
        cfg = yaml.safe_load(open(os.path.join(ROOT, "ci/templates/trivy-scan.yml")))
        for key in (".trivy-scan-template", SOURCE_SCAN_TEMPLATE):
            with self.subTest(template=key):
                script = "\n".join(cfg[key]["script"])
                blocking = [b for b in script.split("trivy ") if "--ignore-unfixed" in b]
                self.assertEqual(len(blocking), 1, f"{key} must have exactly one blocking pass")
                self.assertIn("--exit-code 1", blocking[0])
                self.assertNotIn("--exit-code 0", blocking[0])

    def test_the_source_gate_starts_without_waiting_for_the_build(self):
        """A dependency finding does not need an image, and failing before a twenty minute
        container build is the cheaper order. needs: [] is what expresses that."""
        template = yaml.safe_load(open(os.path.join(ROOT, "ci/templates/trivy-scan.yml")))[SOURCE_SCAN_TEMPLATE]
        self.assertEqual(template.get("needs"), [])

    def test_both_gates_use_the_same_pinned_scanner(self):
        cfg = yaml.safe_load(open(os.path.join(ROOT, "ci/templates/trivy-scan.yml")))
        self.assertEqual(cfg[".trivy-scan-template"]["image"]["name"],
                         cfg[SOURCE_SCAN_TEMPLATE]["image"]["name"])

    def test_source_gate_fans_out_with_its_service_and_not_beyond(self):
        for svc in ("cart", "checkout", "shipping"):
            with self.subTest(service=svc):
                got = names([f"services/{svc}/src/anything"] if svc == "cart"
                            else [f"services/{svc}/main.go"])
                self.assertIn(f"{svc}:scan-source", got)
                others = {j for j in got if j.endswith(":scan-source") and not j.startswith(svc)}
                self.assertEqual(others, set(), "a service change must not scan other services")

    def test_docs_only_instantiates_no_source_gate(self):
        for source, branch in (("merge_request_event", None), ("push", "main")):
            got = names(["README.md"], source=source, branch=branch)
            self.assertEqual({j for j in got if j.endswith(":scan-source")}, set())

    def test_dropping_the_source_gate_makes_the_graph_invalid(self):
        """The negative control for the new invariant. If the source gate stops being
        instantiated while publish survives, GitLab must refuse the pipeline rather than
        offer a publish whose dependency gate never ran."""
        config = ci_graph.load_config(ROOT)
        broken = copy.deepcopy(config)
        broken[SOURCE_SCAN_TEMPLATE]["rules"] = [{"changes": ["ci/templates/nothing.yml"]}]
        ctx = {"source": "push", "branch": "main", "open_mr": False,
               "new_branch_no_compare": False, "default_branch": "main"}
        jobs, _ = ci_graph.evaluate(broken, ["ci/templates/ecr-publish.yml"], ctx)
        present = {j["job"] for j in jobs}
        self.assertTrue(any(j.endswith(":publish") for j in present), "probe must reach publish")
        self.assertFalse(any(j.endswith(":scan-source") for j in present),
                         "probe must drop the source gate")
        errors = ci_graph.validate_needs(broken, jobs)
        self.assertTrue(errors, "a publish with no source gate must be reported invalid")
        self.assertTrue(any("scan-source" in e for e in errors), errors)
