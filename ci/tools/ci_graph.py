"""Answer one question without paying for a pipeline: for a changed path set and a
pipeline source, which jobs would GitLab instantiate from this repository's CI configuration?

It resolves the root file's local includes, applies `extends` the way GitLab merges hashes,
expands job variables inside `rules:changes` paths, and evaluates `rules` with GitLab's glob
semantics. The `if` support is deliberately narrow: only the pipeline-source and branch
comparisons this repository uses. Anything else is reported rather than guessed.

Usage:
    python3 ci/tools/ci_graph.py --source merge_request_event services/cart/ci.yml
    python3 ci/tools/ci_graph.py --source push --branch main ci/templates/image.yml
"""

from __future__ import annotations

import argparse
import copy
import os
import re
import sys

import yaml

ROOT_FILE = ".gitlab-ci.yml"
RESERVED = {"stages", "include", "workflow", "variables", "default", "image", "services"}
_TOKEN = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")


def load_config(repo_root: str) -> dict:
    root = yaml.safe_load(open(os.path.join(repo_root, ROOT_FILE)))
    merged: dict = {}
    for inc in root.get("include", []):
        if "local" not in inc:
            continue
        doc = yaml.safe_load(open(os.path.join(repo_root, inc["local"]))) or {}
        for key, value in doc.items():
            if key in merged:
                raise ValueError(f"duplicate key across includes: {key}")
            merged[key] = value
    for key, value in root.items():
        if key not in RESERVED:
            merged[key] = value
    merged["__workflow__"] = root.get("workflow", {})
    return merged


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def resolve(config: dict, name: str, seen: tuple = ()) -> dict:
    job = config[name]
    if name in seen:
        raise ValueError(f"extends cycle at {name}")
    parents = job.get("extends", [])
    parents = [parents] if isinstance(parents, str) else parents
    resolved: dict = {}
    for parent in parents:
        resolved = _merge(resolved, resolve(config, parent, seen + (name,)))
    own = {k: v for k, v in job.items() if k != "extends"}
    return _merge(resolved, own)


def glob_to_regex(pattern: str) -> re.Pattern:
    """GitLab matches with File.fnmatch?(pattern, path, FNM_PATHNAME | FNM_DOTMATCH |
    FNM_EXTGLOB): `*` and `?` stop at `/`, `**/` spans directories, `{a,b}` alternates."""
    out, i = "", 0
    while i < len(pattern):
        ch = pattern[i]
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
            continue
        if pattern.startswith("**", i):
            out += "[^/]*"  # Ruby: only `**/` spans directories; a bare `**` is `*`
            i += 2
            continue
        if ch == "*":
            out += "[^/]*"
        elif ch == "?":
            out += "[^/]"
        elif ch == "{":
            j = pattern.index("}", i)
            alts = pattern[i + 1 : j].split(",")
            out += "(?:" + "|".join(re.escape(a) for a in alts) + ")"
            i = j
        else:
            out += re.escape(ch)
        i += 1
    return re.compile("^" + out + "$")


def expand(text: str, variables: dict) -> str:
    return _TOKEN.sub(lambda m: str(variables.get(m.group(1), "")), text)


def rule_matches(rule: dict, changed: list[str], variables: dict, ctx: dict) -> bool | None:
    cond = rule.get("if")
    if cond is not None:
        ok = eval_if(cond, ctx)
        if ok is None:
            return None
        if not ok:
            return False
    changes = rule.get("changes")
    if changes is not None:
        paths = changes["paths"] if isinstance(changes, dict) else changes
        if ctx.get("new_branch_no_compare"):
            return True  # documented: no previous commit to compare against
        patterns = [glob_to_regex(expand(p, variables)) for p in paths if expand(p, variables)]
        if not any(pat.match(path) for pat in patterns for path in changed):
            return False
    return True


def eval_if(cond: str, ctx: dict) -> bool | None:
    """Only the forms this repository uses; anything else returns None (unknown)."""
    cond = cond.strip()
    m = re.fullmatch(r'\$CI_PIPELINE_SOURCE\s*==\s*"([^"]+)"', cond)
    if m:
        return ctx["source"] == m.group(1)
    m = re.fullmatch(r'\$CI_COMMIT_BRANCH\s*==\s*"([^"]+)"', cond)
    if m:
        return ctx.get("branch") == m.group(1) and ctx["source"] != "merge_request_event"
    if cond == "$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH":
        return ctx.get("branch") == ctx.get("default_branch", "main") and ctx["source"] != "merge_request_event"
    if cond == "$CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS":
        return ctx["source"] != "merge_request_event" and bool(ctx.get("open_mr"))
    if cond == "$CI_COMMIT_BRANCH":
        return ctx["source"] != "merge_request_event"
    return None


def pipeline_created(config: dict, ctx: dict) -> bool | None:
    rules = (config.get("__workflow__") or {}).get("rules")
    if not rules:
        return True
    for rule in rules:
        ok = eval_if(rule.get("if", ""), ctx) if "if" in rule else True
        if ok is None:
            return None
        if ok:
            return rule.get("when", "always") != "never"
    return False


def needs_of(job: dict) -> list[tuple[str, bool]]:
    """(needed job name, optional) pairs. GitLab defaults optional to false."""
    out = []
    for entry in job.get("needs") or []:
        if isinstance(entry, str):
            out.append((entry, False))
        else:
            out.append((entry["job"], bool(entry.get("optional", False))))
    return out


def validate_needs(config: dict, jobs: list[dict]) -> list[str]:
    """GitLab refuses to create a pipeline whose job needs one that is not in it, unless the
    need is marked optional. That refusal is what makes a missing prerequisite fail closed
    rather than silently produce a job with nothing in front of it."""
    present = {j["job"] for j in jobs}
    errors = []
    for name in sorted(present):
        for needed, optional in needs_of(resolve(config, name)):
            if optional or needed in present:
                continue
            errors.append(f"{name} needs {needed}, but {needed} is not in the pipeline")
    return errors


def evaluate(config: dict, changed: list[str], ctx: dict) -> tuple[list[dict], list[str]]:
    jobs, unknown = [], []
    if pipeline_created(config, ctx) is False:
        return jobs, unknown
    for name in config:
        if name.startswith(".") or name.startswith("__"):
            continue
        job = resolve(config, name)
        variables = job.get("variables") or {}
        rules = job.get("rules")
        if rules is None:
            jobs.append({"job": name, "stage": job.get("stage"), "when": "always"})
            continue
        for rule in rules:
            match = rule_matches(rule, changed, variables, ctx)
            if match is None:
                unknown.append(f"{name}: cannot evaluate rule {rule}")
                break
            if match:
                when = rule.get("when", "on_success")
                if when != "never":
                    jobs.append({"job": name, "stage": job.get("stage"), "when": when})
                break
    return jobs, unknown


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="changed paths")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--source", default="merge_request_event", choices=["merge_request_event", "push"])
    ap.add_argument("--branch", default=None, help="branch name for push pipelines")
    ap.add_argument("--open-mr", action="store_true", help="a merge request is open for the branch")
    ap.add_argument("--new-branch", action="store_true", help="first push of a branch: no commit to compare")
    args = ap.parse_args()
    ctx = {"source": args.source, "branch": args.branch, "open_mr": args.open_mr,
           "new_branch_no_compare": args.new_branch, "default_branch": "main"}
    config = load_config(args.repo)
    jobs, unknown = evaluate(config, args.paths, ctx)
    for job in sorted(jobs, key=lambda j: (str(j["stage"]), j["job"])):
        print(f"{job['stage']:<12} {job['job']:<36} {job['when']}")
    print(f"-- {len(jobs)} jobs")
    for line in unknown:
        print(f"UNKNOWN {line}", file=sys.stderr)
    errors = validate_needs(config, jobs)
    for line in errors:
        print(f"INVALID {line}", file=sys.stderr)
    if errors:
        return 3
    return 2 if unknown else 0


if __name__ == "__main__":
    sys.exit(main())
