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
        health = health_jobs()
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
        package manager at all carry it, and adding another one has to be a decision.
        currency is C++ with no language package manager; measured, the source pass resolves
        zero packages there."""
        measured_none = {"currency", "frontend-proxy", "image-provider"}
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


class LockBuildBinding(unittest.TestCase):
    """The source gate scans a lock file. These are the checks that keep the build from
    resolving something else, which would make the scan evidence for an artifact nobody
    built. Both mechanisms were measured against the real toolchains before being asserted
    here: NU1004 for NuGet, a non-zero composer validate for Composer."""

    LOCKFILES = {
        "nuget": "packages.lock.json",
        "composer": "composer.lock",
    }

    def committed_lockfiles(self, filename):
        return {p.split(os.sep)[-3] if p.split(os.sep)[-2] == "src" else p.split(os.sep)[-2]
                for p in glob.glob(os.path.join(ROOT, "services", "*", "**", filename), recursive=True)}

    def tier_script(self, template_file, key):
        return "\n".join(yaml.safe_load(open(os.path.join(ROOT, template_file)))[key]["script"])

    def test_dotnet_tier_restores_in_locked_mode(self):
        """A committed packages.lock.json that restore is free to ignore is decoration.
        Measured: with --locked-mode a changed package version fails NU1004; without it,
        restore rewrites the lock file and exits 0."""
        script = self.tier_script("ci/templates/lang-dotnet.yml", ".lang-dotnet-template")
        self.assertIn("dotnet restore --locked-mode", script)
        self.assertNotIn("\n    - dotnet restore\n", "\n" + script + "\n")

    def test_php_tier_does_not_disable_the_lock_check(self):
        """composer validate checks manifest against lock by default. --no-check-lock was
        correct while no lock file existed and would now disable the check the evidence
        model depends on. Measured: composer install alone reports the same drift as a
        Warning and exits 0 unless the edit also breaks a constraint."""
        script = self.tier_script("ci/templates/lang-php.yml", ".lang-php-template")
        self.assertIn("composer validate", script)
        self.assertNotIn("--no-check-lock", script)

    def test_a_committed_lockfile_has_a_tier_that_enforces_it(self):
        """The pairing, stated once rather than per service: if a service commits an
        ecosystem lock file, that ecosystem's shared tier must enforce it."""
        enforced = {
            "nuget": ("ci/templates/lang-dotnet.yml", ".lang-dotnet-template", "--locked-mode"),
            "composer": ("ci/templates/lang-php.yml", ".lang-php-template", "composer validate"),
        }
        for ecosystem, filename in self.LOCKFILES.items():
            services_with = self.committed_lockfiles(filename)
            if not services_with:
                continue
            path, key, token = enforced[ecosystem]
            with self.subTest(ecosystem=ecosystem, services=sorted(services_with)):
                self.assertIn(token, self.tier_script(path, key))

    def test_every_source_scanned_service_declaring_dependencies_commits_a_lock(self):
        """--locked-mode does not require a lock file to exist: measured, against a project
        with none it exits 0 and writes nothing. That fail-open is closed by the source
        gate rather than here, so the two controls have to stay paired."""
        scanned = {j.split(":")[0] for j in jobs_extending(SOURCE_SCAN_TEMPLATE)}
        declaring = set()
        for svc in scanned:
            body = yaml.safe_load(open(os.path.join(ROOT, "services", svc, "ci.yml")))[f"{svc}:scan-source"]
            if (body.get("variables") or {}).get("SOURCE_DEPENDENCIES", "declared") == "declared":
                declaring.add(svc)
        for svc in sorted(declaring):
            with self.subTest(service=svc):
                # One name per ecosystem the fleet actually uses. npm's file is
                # package-lock.json, which a *.lock* pattern does not match, and this test
                # failed on payment for exactly that reason the first time a Node service
                # declared dependencies.
                names = ("package-lock.json", "packages.lock.json", "composer.lock",
                         "Cargo.lock", "go.sum", "poetry.lock", "Gemfile.lock", "mix.lock")
                found = [m for name in names
                         for m in glob.glob(os.path.join(ROOT, "services", svc, "**", name), recursive=True)
                         if "node_modules" not in m and "/vendor/" not in m]
                self.assertTrue(found, f"{svc} declares managed dependencies but commits no lock file")


HEALTH_TEMPLATE = ".image-health-template"
HEALTH_PUBLISHER_TEMPLATE = ".image-health-publisher-template"
DEFERRED = "deferred-to-runtime"
VALIDATED = "validated-in-ci"
RUNNING = "running"


def health_jobs():
    return jobs_extending(HEALTH_TEMPLATE) | jobs_extending(HEALTH_PUBLISHER_TEMPLATE)


def health_mode(config, job):
    return (ci_graph.resolve(config, job).get("variables") or {}).get("HEALTH_MODE")


def mode_dispatch():
    """The template's own first script step, so the controls below run what CI runs."""
    config = ci_graph.load_config(ROOT)
    return ci_graph.resolve(config, HEALTH_TEMPLATE)["script"][0]


def run_dispatch(**env):
    import subprocess
    return subprocess.run(["sh", "-c", mode_dispatch()], capture_output=True, text=True,
                          env={"PATH": os.environ["PATH"], **env})


class DeferredHealth(unittest.TestCase):
    """A service that cannot listen until a dependency exists must say so rather than
    silently omit the stage. Recording the deferral is not a health result."""

    def test_deferred_mode_requires_a_reason(self):
        config = ci_graph.load_config(ROOT)
        for job in sorted(health_jobs()):
            if health_mode(config, job) != DEFERRED:
                continue
            with self.subTest(job=job):
                reason = (ci_graph.resolve(config, job)["variables"] or {}).get("HEALTH_REASON", "")
                self.assertTrue(reason.strip(), "deferred health must carry a measured reason")

    def test_empty_reason_fails_the_job(self):
        r = run_dispatch(HEALTH_MODE=DEFERRED, HEALTH_REASON="")
        self.assertEqual(r.returncode, 1)
        self.assertIn("requires HEALTH_REASON", r.stdout)

    def test_unknown_mode_fails_the_job(self):
        for mode in ("skipped", "passed", "true", ""):
            with self.subTest(mode=mode):
                r = run_dispatch(HEALTH_MODE=mode, HEALTH_REASON="anything")
                self.assertEqual(r.returncode, 1)
                self.assertIn("unknown HEALTH_MODE", r.stdout)

    def test_deferred_records_without_claiming_a_pass(self):
        r = run_dispatch(HEALTH_MODE=DEFERRED, HEALTH_REASON="measured cause")
        self.assertEqual(r.returncode, 0)
        self.assertIn("NOT VALIDATED IN CI: measured cause; runtime readiness required", r.stdout)
        self.assertNotIn("PASS", r.stdout.upper().replace("NOT VALIDATED", ""))

    def test_validated_mode_falls_through_to_the_real_probe(self):
        """Default mode must reach the container checks rather than short-circuit."""
        r = run_dispatch(HEALTH_MODE=VALIDATED)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_every_health_job_resolves_to_a_known_mode(self):
        config = ci_graph.load_config(ROOT)
        for job in sorted(health_jobs()):
            with self.subTest(job=job):
                self.assertIn(health_mode(config, job), {VALIDATED, RUNNING, DEFERRED})

    def test_running_mode_passes_the_dispatch_silently(self):
        r = run_dispatch(HEALTH_MODE=RUNNING)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))

    def test_the_running_set_is_the_measured_one_only(self):
        """running is for a worker that never listens; using it for a service that should
        listen would hide a failing probe, so each user is a recorded decision."""
        config = ci_graph.load_config(ROOT)
        running = {j.split(":")[0] for j in health_jobs() if health_mode(config, j) == RUNNING}
        self.assertEqual(running, set())

    def test_the_deferred_set_is_the_measured_one_only(self):
        """Deferring is a claim about a service, not a way past a failing probe. cart and
        product-catalog left it once a startup fixture made their probe real."""
        config = ci_graph.load_config(ROOT)
        deferred = {j.split(":")[0] for j in health_jobs() if health_mode(config, j) == DEFERRED}
        self.assertEqual(deferred, set())

    def test_every_built_service_declares_a_health_job(self):
        built = {job.split(":")[0] for job in jobs_extending(".image-build-template")}
        self.assertEqual({job.split(":")[0] for job in health_jobs()}, built)

    def test_no_health_job_carries_allow_failure(self):
        config = ci_graph.load_config(ROOT)
        for job in sorted(health_jobs()):
            with self.subTest(job=job):
                self.assertNotIn("allow_failure", ci_graph.resolve(config, job))

    def test_no_health_job_adds_a_gitlab_service(self):
        """The dind daemon is the only GitLab service: a fixture runs as a sibling inside it,
        because nested containers cannot resolve a services: entry."""
        config = ci_graph.load_config(ROOT)
        dind = ci_graph.resolve(config, ".docker-dind")["services"]
        for job in sorted(health_jobs()):
            with self.subTest(job=job):
                self.assertEqual(ci_graph.resolve(config, job)["services"], dind)

    def test_no_health_job_adds_a_local_script(self):
        """Upstream sources may hold gRPC health protos (currency does); only a service that
        names a fixture is checked for an added health file."""
        config = ci_graph.load_config(ROOT)
        template_script = ci_graph.resolve(config, HEALTH_TEMPLATE)["script"]
        for job in sorted(health_jobs()):
            svc = job.split(":")[0]
            with self.subTest(job=job):
                body = yaml.safe_load(open(os.path.join(ROOT, "services", svc, "ci.yml")))
                self.assertNotIn("script", body[job])
                self.assertEqual(ci_graph.resolve(config, job)["script"], template_script)
                if (ci_graph.resolve(config, job).get("variables") or {}).get("HEALTH_DEPENDENCY_IMAGE"):
                    self.assertEqual(glob.glob(os.path.join(ROOT, "services", svc, "**", "health*"),
                                               recursive=True), [])

    def test_every_publisher_validates_health_in_ci(self):
        """A deferral records that CI did not validate health, so it cannot sit in front of a
        publish; running is the check a non-listening worker can pass."""
        config = ci_graph.load_config(ROOT)
        for svc in sorted(publishers()):
            with self.subTest(service=svc):
                self.assertIn(health_mode(config, f"{svc}:health-test"), {VALIDATED, RUNNING})

    def test_every_dependency_fixture_is_pinned_and_declares_readiness(self):
        """A fixture is a claim that the service cannot listen without it, so the set of users
        is the measured one and adding another has to be a decision."""
        config = ci_graph.load_config(ROOT)
        users = set()
        for job in sorted(health_jobs()):
            variables = ci_graph.resolve(config, job).get("variables") or {}
            image = variables.get("HEALTH_DEPENDENCY_IMAGE", "")
            if not image:
                continue
            users.add(job.split(":")[0])
            with self.subTest(job=job):
                self.assertRegex(image, r"@sha256:[0-9a-f]{64}$")
                self.assertTrue(variables.get("HEALTH_DEPENDENCY_READY", "").strip())
        self.assertEqual(users, {"cart", "product-catalog"})

    def test_the_inventory_matches_each_health_mode(self):
        """Deferred health must read as deferred, and fixture-backed health must say what it
        ran against, so neither can be read as runtime readiness."""
        config = ci_graph.load_config(ROOT)
        text = open(os.path.join(ROOT, "SERVICE-INVENTORY.md")).read()
        for job in sorted(health_jobs()):
            svc = job.split(":")[0]
            variables = ci_graph.resolve(config, job).get("variables") or {}
            with self.subTest(service=svc):
                if health_mode(config, job) == DEFERRED:
                    self.assertRegex(text, rf"{svc}[^|]*\|[^|]*health: deferred to runtime")
                elif health_mode(config, job) == RUNNING:
                    self.assertRegex(text, rf"{svc}[^|]*\|[^|]*running in CI, not functional health")
                elif variables.get("HEALTH_DEPENDENCY_IMAGE"):
                    self.assertRegex(text, rf"{svc}[^|]*\|[^|]*validated in CI against an ephemeral fixture")


def fixture_step(config=None):
    """The template's own fixture step, so the controls below run what CI runs."""
    config = config or ci_graph.load_config(ROOT)
    steps = ci_graph.resolve(config, HEALTH_TEMPLATE)["script"]
    found = [s for s in steps if 'if [ -n "${HEALTH_DEPENDENCY_IMAGE}" ]' in s]
    return found


def run_fixture_step(step, docker_stub=False, **env):
    import subprocess, tempfile
    path = os.environ["PATH"]
    with tempfile.TemporaryDirectory() as tmp:
        if docker_stub:
            stub = os.path.join(tmp, "docker")
            with open(stub, "w") as handle:
                handle.write("#!/bin/sh\nexit 0\n")
            os.chmod(stub, 0o700)
            path = tmp + os.pathsep + path
        return subprocess.run(["sh", "-c", step], capture_output=True, text=True,
                              env={"PATH": path, **env})


def template_step(fragment):
    config = ci_graph.load_config(ROOT)
    found = [s for s in ci_graph.resolve(config, HEALTH_TEMPLATE)["script"] if fragment in s]
    assert len(found) == 1, (fragment, len(found))
    return found[0]


def run_with_stubs(step, docker, nc="exit 1", **env):
    """Run a template step with docker and nc replaced by shell stubs; the stub for docker
    receives its arguments, so it can answer inspect calls per container."""
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for name, body in (("docker", docker), ("nc", nc)):
            path = os.path.join(tmp, name)
            with open(path, "w") as handle:
                handle.write("#!/bin/sh\n" + body + "\n")
            os.chmod(path, 0o700)
        base = {"PATH": tmp + os.pathsep + os.environ["PATH"], "SERVICE_NAME": "svc",
                "CI_COMMIT_SHORT_SHA": "x", "HEALTH_PORT": "8080", "HEALTH_RUNNING_SECONDS": "0",
                "HEALTH_CONTROL_IMAGE": "img@sha256:" + "0" * 64}
        return subprocess.run(["sh", "-c", step], capture_output=True, text=True, env={**base, **env})


def inspect_stub(control, service):
    return ('case "$*" in\n'
            f'  *health-exit-control*) echo {control} ;;\n'
            f'  *"State.Running}}}} {{{{.RestartCount"*) echo "{service}" ;;\n'
            '  *) exit 0 ;;\n'
            'esac')


class RunningMode(unittest.TestCase):
    """A worker that never listens passes only by staying up, and only after the job has shown
    that an exited container reads as stopped."""

    STEP = 'if [ "${HEALTH_MODE}" = running ]; then'

    def test_a_worker_that_stays_up_passes_and_says_what_it_proved(self):
        r = run_with_stubs(template_step(self.STEP), inspect_stub("false", "true 0"), HEALTH_MODE=RUNNING)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("RUNNING, NOT FUNCTIONAL HEALTH", r.stdout)

    def test_a_worker_that_exited_or_restarted_fails(self):
        for state in ("false 0", "true 1", "false 1"):
            with self.subTest(state=state):
                r = run_with_stubs(template_step(self.STEP), inspect_stub("false", state), HEALTH_MODE=RUNNING)
                self.assertEqual(r.returncode, 1)
                self.assertIn("did not stay running", r.stdout)

    def test_a_control_that_still_reads_running_fails_the_job(self):
        r = run_with_stubs(template_step(self.STEP), inspect_stub("true", "true 0"), HEALTH_MODE=RUNNING)
        self.assertEqual(r.returncode, 1)
        self.assertIn("exited control still reads as running", r.stdout)

    def test_removing_the_exit_control_is_caught(self):
        """The negative control: without the check, a daemon that reports every container as
        running would let a crashed worker pass."""
        step = template_step(self.STEP)
        start = step.index('  if [ "$(docker inspect -f \'{{.State.Running}}\' health-exit-control)"')
        end = step.index("  fi", start) + len("  fi")
        mutant = step[:start] + step[end:]
        r = run_with_stubs(mutant, inspect_stub("true", "true 0"), HEALTH_MODE=RUNNING)
        self.assertEqual(r.returncode, 0)

    def test_other_modes_skip_it(self):
        r = run_with_stubs(template_step(self.STEP), 'echo "docker called"; exit 1', HEALTH_MODE=VALIDATED)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


class PortProbeControl(unittest.TestCase):
    """nc -z proves nothing where a proxy answers for published ports, so every port-health job
    first shows the probe reads a port nothing listens on as closed."""

    STEP = "docker run -d --name health-probe-control"

    def test_a_probe_that_reads_the_dead_port_as_closed_proceeds(self):
        r = run_with_stubs(template_step(self.STEP), "exit 0", nc="exit 1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_probe_that_reaches_the_dead_port_fails_the_job(self):
        r = run_with_stubs(template_step(self.STEP), "exit 0", nc="exit 0")
        self.assertEqual(r.returncode, 1)
        self.assertIn("cannot prove listening here", r.stdout)

    def test_the_control_runs_on_the_service_port_before_the_service(self):
        steps = ci_graph.resolve(ci_graph.load_config(ROOT), HEALTH_TEMPLATE)["script"]
        control = [i for i, s in enumerate(steps) if self.STEP in s]
        service = [i for i, s in enumerate(steps) if s.startswith('docker run -d --name "${SERVICE_NAME}-health"')]
        self.assertEqual(len(control), 1)
        self.assertLess(control[0], service[0])
        self.assertIn('-p "${HEALTH_PORT}:${HEALTH_PORT}"', steps[control[0]])

    def test_the_control_image_is_pinned(self):
        variables = ci_graph.resolve(ci_graph.load_config(ROOT), HEALTH_TEMPLATE)["variables"]
        self.assertRegex(variables["HEALTH_CONTROL_IMAGE"], r"@sha256:[0-9a-f]{64}$")


class DependencyFixture(unittest.TestCase):
    """The fixture step refuses anything that would make the fixture, not the image, the thing
    tested: a tag that can move, or no readiness to wait for."""

    def step(self):
        found = fixture_step()
        self.assertEqual(len(found), 1, "exactly one fixture step")
        return found[0]

    def test_no_fixture_is_a_no_op(self):
        r = run_fixture_step(self.step(), HEALTH_DEPENDENCY_IMAGE="")
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_a_tag_without_a_digest_fails(self):
        for image in ("valkey/valkey:9.0.1-alpine3.23", "postgres@sha256:abc", "postgres:17@sha256:" + "0" * 63):
            with self.subTest(image=image):
                r = run_fixture_step(self.step(), docker_stub=True, HEALTH_DEPENDENCY_IMAGE=image,
                                     HEALTH_DEPENDENCY_READY="true")
                self.assertEqual(r.returncode, 1)
                self.assertIn("must be pinned by digest", r.stdout)

    def test_a_missing_readiness_command_fails(self):
        r = run_fixture_step(self.step(), docker_stub=True,
                             HEALTH_DEPENDENCY_IMAGE="postgres:17.11@sha256:" + "0" * 64,
                             HEALTH_DEPENDENCY_READY="")
        self.assertEqual(r.returncode, 1)
        self.assertIn("requires HEALTH_DEPENDENCY_READY", r.stdout)

    def test_a_pinned_ready_fixture_proceeds(self):
        r = run_fixture_step(self.step(), docker_stub=True,
                             HEALTH_DEPENDENCY_IMAGE="postgres:17.11@sha256:" + "0" * 64,
                             HEALTH_DEPENDENCY_READY="true")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_removing_the_pin_check_is_caught(self):
        """The negative control: without the check, a moving tag proceeds as if pinned."""
        step = self.step()
        start = step.index("  if ! echo")
        end = step.index("  fi", start) + len("  fi")
        mutant = step[:start] + step[end:]
        self.assertNotEqual(mutant, step)
        r = run_fixture_step(mutant, docker_stub=True, HEALTH_DEPENDENCY_IMAGE="valkey/valkey:latest",
                             HEALTH_DEPENDENCY_READY="true")
        self.assertEqual(r.returncode, 0)

    def test_the_service_joins_the_fixture_network_only_with_a_fixture(self):
        config = ci_graph.load_config(ROOT)
        runs = [s for s in ci_graph.resolve(config, HEALTH_TEMPLATE)["script"]
                if s.startswith('docker run -d --name "${SERVICE_NAME}-health"')]
        self.assertEqual(len(runs), 1)
        self.assertIn("${HEALTH_DEPENDENCY_IMAGE:+--network health-net}", runs[0])

    def test_no_terminal_classification_mechanism_exists_to_assert_against(self):
        """Enforcement owed: nothing here decides FULL-CHAIN-VALIDATED, so a deferred
        component cannot yet be machine-blocked from it. Delete this when one lands and
        assert the block instead."""
        token = "FULL-CHAIN" + "-VALIDATED"
        skip = (os.path.join("ci", "tools", "tests"), ".git" + os.sep)
        hits = [p for p in glob.glob(os.path.join(ROOT, "**", "*"), recursive=True)
                if os.path.isfile(p) and not any(s in p for s in skip)
                and token in open(p, errors="ignore").read()]
        self.assertEqual(hits, [])


PUBLISH_TEMPLATE = ".ecr-publish-template"
MAIN = {"source": "push", "branch": "main", "open_mr": False,
        "new_branch_no_compare": False, "default_branch": "main"}


def publishers():
    return {job.split(":")[0] for job in jobs_extending(PUBLISH_TEMPLATE)}


def runnable(config, jobs, status, name):
    """GitLab's start condition, reduced to what this repository uses: a job with needs starts
    once every needed job in the pipeline has succeeded, one without needs once every job in an
    earlier stage has. A manual job becomes playable on the same condition."""
    body = ci_graph.resolve(config, name)
    present = {j["job"] for j in jobs}
    if "needs" in body:
        return all(status[n] == "success" for n, _ in ci_graph.needs_of(body) if n in present)
    order = yaml.safe_load(open(os.path.join(ROOT, ".gitlab-ci.yml")))["stages"]
    earlier = {j["job"] for j in jobs if order.index(j["stage"]) < order.index(body["stage"])}
    return all(status[n] == "success" for n in earlier)


class PublishHealthGate(unittest.TestCase):
    """An image whose own health test failed must never become publishable."""

    def service_job(self, svc, suffix):
        return yaml.safe_load(open(os.path.join(ROOT, "services", svc, "ci.yml")))[f"{svc}:{suffix}"]

    def test_every_publisher_needs_its_own_health_test(self):
        self.assertTrue(publishers())
        for svc in sorted(publishers()):
            with self.subTest(service=svc):
                needed = dict(ci_graph.needs_of(self.service_job(svc, "publish")))
                self.assertIn(f"{svc}:health-test", needed, "publish must need its health test")
                self.assertFalse(needed[f"{svc}:health-test"], "the health need must not be optional")

    def test_publisher_health_template_is_used_by_publishers_only(self):
        users = {job.split(":")[0] for job in jobs_extending(HEALTH_PUBLISHER_TEMPLATE)}
        self.assertEqual(users, publishers())

    def test_publisher_health_rules_add_only_the_publish_chain_on_main(self):
        cfg = ci_graph.load_config(ROOT)
        base = cfg[HEALTH_TEMPLATE]["rules"]
        own = cfg[HEALTH_PUBLISHER_TEMPLATE]["rules"]
        chain = cfg[PUBLISH_TEMPLATE]["rules"][0]["changes"]
        self.assertEqual(own[0], base[0], "outside main, publishers fan out like any service")
        self.assertEqual(own[1]["if"], cfg[PUBLISH_TEMPLATE]["rules"][0]["if"])
        self.assertEqual(set(own[0]["changes"]) | set(own[1]["changes"]), set(chain))
        self.assertEqual(len(own), 2)

    def test_publish_never_appears_without_its_health_test_in_any_changeset(self):
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
                        self.assertIn(f"{svc}:health-test", got,
                                      f"{paths} on {source}: {job} without its health test")

    def test_a_failed_health_test_leaves_publish_unplayable(self):
        paths = [f"services/{s}/ci.yml" for s in services()]
        _, config, jobs = evaluate(paths, source="push", branch="main")
        for svc in sorted(publishers()):
            with self.subTest(service=svc):
                status = {j["job"]: "success" for j in jobs}
                self.assertTrue(runnable(config, jobs, status, f"{svc}:publish"),
                                "with every prerequisite green, publish must be playable")
                status[f"{svc}:health-test"] = "failed"
                self.assertFalse(runnable(config, jobs, status, f"{svc}:publish"))

    def test_removing_the_health_need_is_caught(self):
        """The negative control: without the need, the same failed health test leaves publish
        playable, which is the gap the need closes."""
        config = ci_graph.load_config(ROOT)
        svc = sorted(publishers())[0]
        broken = copy.deepcopy(config)
        broken[f"{svc}:publish"]["needs"] = [n for n in broken[f"{svc}:publish"]["needs"]
                                             if n["job"] != f"{svc}:health-test"]
        jobs, _ = ci_graph.evaluate(broken, [f"services/{svc}/ci.yml"], MAIN)
        status = {j["job"]: "success" for j in jobs}
        status[f"{svc}:health-test"] = "failed"
        self.assertTrue(runnable(broken, jobs, status, f"{svc}:publish"))

    def test_dropping_the_main_health_rule_makes_the_graph_invalid(self):
        """The second negative control: if the health test stops following publish onto main,
        GitLab must refuse the pipeline rather than offer an untested publish."""
        config = ci_graph.load_config(ROOT)
        broken = copy.deepcopy(config)
        broken[HEALTH_PUBLISHER_TEMPLATE]["rules"] = copy.deepcopy(config[HEALTH_TEMPLATE]["rules"])
        jobs, _ = ci_graph.evaluate(broken, ["ci/templates/ecr-publish.yml"], MAIN)
        present = {j["job"] for j in jobs}
        self.assertTrue(any(j.endswith(":publish") for j in present), "probe must reach publish")
        self.assertFalse(any(j.endswith(":health-test") for j in present), "probe must drop health")
        errors = ci_graph.validate_needs(broken, jobs)
        self.assertTrue(any("health-test" in e for e in errors), errors)


SOURCE_DEPENDENCY_VALUES = {"declared", "none"}


def source_dependency_check(config=None):
    config = config or ci_graph.load_config(ROOT)
    steps = ci_graph.resolve(config, SOURCE_SCAN_TEMPLATE)["script"]
    return [i for i, s in enumerate(steps) if 'case "${SOURCE_DEPENDENCIES}"' in s], steps


def run_step(step, **env):
    import subprocess
    return subprocess.run(["sh", "-c", step], capture_output=True, text=True,
                          env={"PATH": os.environ["PATH"], **env})


class SourceDependencyValue(unittest.TestCase):
    """The coverage check acts only on declared, so any other value used to skip it quietly."""

    def step(self):
        found, steps = source_dependency_check()
        self.assertEqual(len(found), 1, "exactly one value check")
        return steps[found[0]]

    def test_the_value_is_checked_before_anything_is_scanned(self):
        found, _ = source_dependency_check()
        self.assertEqual(found, [0])

    def test_the_contract_values_pass(self):
        for value in sorted(SOURCE_DEPENDENCY_VALUES):
            with self.subTest(value=value):
                r = run_step(self.step(), SOURCE_DEPENDENCIES=value)
                self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_any_other_value_fails_closed(self):
        for value in ("", "Declared", "NONE", "declared ", " none", "true", "false", "yes",
                      "declared,none", "nonee", "*"):
            with self.subTest(value=value):
                r = run_step(self.step(), SOURCE_DEPENDENCIES=value)
                self.assertEqual(r.returncode, 1)
                self.assertIn("must be declared or none", r.stdout)

    def test_unset_fails_closed(self):
        r = run_step(self.step())
        self.assertEqual(r.returncode, 1)

    def test_every_source_scan_resolves_to_a_contract_value(self):
        """Unset in a service means the template's declared, which is a contract value."""
        config = ci_graph.load_config(ROOT)
        for job in sorted(jobs_extending(SOURCE_SCAN_TEMPLATE)):
            with self.subTest(job=job):
                value = ci_graph.resolve(config, job)["variables"].get("SOURCE_DEPENDENCIES")
                self.assertIn(value, SOURCE_DEPENDENCY_VALUES)

    def test_an_accepting_check_is_caught(self):
        """The negative control: a check that lets an unknown value through exits 0 here, so the
        fail-closed test above would fail on it."""
        mutant = self.step().replace("declared|none) ;;", "declared|none|*) ;;")
        self.assertNotEqual(mutant, self.step())
        self.assertEqual(run_step(mutant, SOURCE_DEPENDENCIES="nonee").returncode, 0)
        config = copy.deepcopy(ci_graph.load_config(ROOT))
        config[SOURCE_SCAN_TEMPLATE]["script"] = config[SOURCE_SCAN_TEMPLATE]["script"][1:]
        self.assertEqual(source_dependency_check(config)[0], [], "a removed check must be visible")


def retained_access_violations(config):
    """Every never-expiring artifact is retained evidence, so each must be Developer-only."""
    out = []
    for name in config:
        if name.startswith("__"):
            continue
        artifacts = ci_graph.resolve(config, name).get("artifacts") or {}
        if artifacts.get("expire_in") == "never" and (
                artifacts.get("access") != "developer" or "public" in artifacts):
            out.append(name)
    return sorted(out)


class RetainedEvidenceAccess(unittest.TestCase):
    """Retained scan, publish and evidence artifacts stay Developer-only through the UI and API,
    independent of the project's pipeline visibility setting."""

    def test_the_retained_set_is_the_evidence_chain(self):
        config = ci_graph.load_config(ROOT)
        retained = {name for name in config if name.startswith(".")
                    and (config[name].get("artifacts") or {}).get("expire_in") == "never"}
        self.assertEqual(retained, {".trivy-scan-template", SOURCE_SCAN_TEMPLATE,
                                    PUBLISH_TEMPLATE, ".evidence-retain-template"})

    def test_every_retained_artifact_is_developer_only(self):
        config = ci_graph.load_config(ROOT)
        self.assertEqual(retained_access_violations(config), [])

    def test_no_ci_file_uses_artifacts_public(self):
        """public is superseded by access, and GitLab rejects the two in one job."""
        for path in [".gitlab-ci.yml", *glob.glob(os.path.join(ROOT, "ci", "templates", "*.yml")),
                     *glob.glob(os.path.join(ROOT, "services", "*", "ci.yml"))]:
            doc = yaml.safe_load(open(os.path.join(ROOT, path))) or {}
            for key, body in doc.items():
                if isinstance(body, dict) and isinstance(body.get("artifacts"), dict):
                    with self.subTest(file=path, job=key):
                        self.assertNotIn("public", body["artifacts"])

    def test_removing_access_is_caught(self):
        """The negative control: dropping access from any one retained template is reported."""
        config = ci_graph.load_config(ROOT)
        for template in (".trivy-scan-template", SOURCE_SCAN_TEMPLATE, PUBLISH_TEMPLATE,
                         ".evidence-retain-template"):
            with self.subTest(template=template):
                broken = copy.deepcopy(config)
                del broken[template]["artifacts"]["access"]
                self.assertIn(template, retained_access_violations(broken))
