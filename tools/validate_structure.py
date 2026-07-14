#!/usr/bin/env python3
"""
validate_structure.py — deterministic gate #1.

Diffs actual repo state against project_manifest.yaml. No LLM involved.
Exit code 0 = clean, 1 = violations (printed as machine-readable JSON so the
orchestrator can bounce them straight back to Cline as a fix prompt).

Usage:
    python validate_structure.py /path/to/repo [--diff-only <base_ref>]

--diff-only limits placement/naming checks to files touched since <base_ref>
(cheap per-task check); omit it for a full-repo audit.
"""

import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


def load_manifest(repo: Path) -> dict:
    mf = repo / "project_manifest.yaml"
    if not mf.exists():
        fail([{"rule": "manifest", "detail": "project_manifest.yaml missing at repo root"}])
    return yaml.safe_load(mf.read_text())


def fail(violations: list[dict]):
    print(json.dumps({"status": "fail", "violations": violations}, indent=2))
    sys.exit(1)


def ok():
    print(json.dumps({"status": "pass", "violations": []}))
    sys.exit(0)


def git_changed_files(repo: Path, base_ref: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", base_ref, "HEAD"],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def all_repo_files(repo: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=repo, capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def check_required(repo: Path, structure: dict, violations: list):
    for d in structure.get("required_dirs", []):
        if not (repo / d).is_dir():
            violations.append({"rule": "required_dir", "detail": f"missing directory: {d}/"})
    for f in structure.get("required_files", []):
        if not (repo / f).is_file():
            violations.append({"rule": "required_file", "detail": f"missing file: {f}"})


def check_placement(files: list[str], structure: dict, violations: list):
    for rule in structure.get("placement_rules", []):
        pattern = rule["pattern"]
        allowed = rule["allowed_under"]
        if isinstance(allowed, str):
            allowed = [allowed]
        for f in files:
            name = Path(f).name
            if fnmatch.fnmatch(name, pattern):
                if not any(f.startswith(a) for a in allowed):
                    violations.append({
                        "rule": "placement",
                        "detail": f"{f} matches '{pattern}' but is outside {allowed}",
                        "fix": f"move to one of: {allowed}",
                    })


def check_naming(files: list[str], structure: dict, violations: list):
    for rule in structure.get("naming_rules", []):
        target_glob = rule["target"]
        rx = re.compile(rule["regex"])
        for f in files:
            if fnmatch.fnmatch(f, target_glob):
                if not rx.match(Path(f).name):
                    violations.append({
                        "rule": "naming",
                        "detail": f"{f} violates naming regex {rule['regex']}",
                    })


def check_protected(files: list[str], structure: dict, violations: list):
    for p in structure.get("protected_paths", []):
        for f in files:
            if f == p or f.startswith(p):
                violations.append({
                    "rule": "protected_path",
                    "detail": f"agent-modified protected path: {f}",
                    "fix": "revert this change; protected paths are human-only",
                })


def check_doc_sections(repo: Path, manifest: dict, files: list[str], violations: list):
    for name, tpl in manifest.get("doc_templates", {}).items():
        glob_pattern = tpl["path_pattern"].replace("{task_id}", "*")
        for f in files:
            if fnmatch.fnmatch(f, glob_pattern):
                text = (repo / f).read_text(errors="replace")
                for section in tpl["required_sections"]:
                    if section not in text:
                        violations.append({
                            "rule": "doc_sections",
                            "detail": f"{f} missing required section '{section}'",
                            "template": name,
                        })


def check_tests_exist(repo: Path, files: list[str], violations: list):
    """Every new/changed src module must have a corresponding tests/test_*.py."""
    src_changed = [f for f in files if f.startswith("src/") and f.endswith(".py")
                   and Path(f).name != "__init__.py"]
    for f in src_changed:
        stem = Path(f).stem
        expected = repo / "tests" / f"test_{stem}.py"
        if not expected.exists():
            violations.append({
                "rule": "tests_exist",
                "detail": f"{f} changed but tests/test_{stem}.py does not exist",
                "fix": f"create tests/test_{stem}.py",
            })


def main():
    if len(sys.argv) < 2:
        print("usage: validate_structure.py <repo_path> [--diff-only <base_ref>]")
        sys.exit(2)

    repo = Path(sys.argv[1]).resolve()
    manifest = load_manifest(repo)
    structure = manifest.get("structure", {})

    diff_only = "--diff-only" in sys.argv
    if diff_only:
        base_ref = sys.argv[sys.argv.index("--diff-only") + 1]
        files = git_changed_files(repo, base_ref)
    else:
        files = all_repo_files(repo)

    violations: list[dict] = []
    check_required(repo, structure, violations)      # always full-repo
    check_placement(files, structure, violations)
    check_naming(files, structure, violations)
    check_doc_sections(repo, manifest, files, violations)
    if diff_only:
        # protected paths: existing is fine, an agent *modifying* one is not
        check_protected(files, structure, violations)
        check_tests_exist(repo, files, violations)

    if violations:
        fail(violations)
    ok()


if __name__ == "__main__":
    main()
