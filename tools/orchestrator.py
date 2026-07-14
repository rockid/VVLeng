#!/usr/bin/env python3
"""
orchestrator.py — the org layer. Runs in any terminal (PowerShell fine).

Owns the stage state machine from project_manifest.yaml. For each task:
  1. Refuses to run a stage until the previous stage's gates passed (recorded
     in tasks/state.json — the pipeline position lives HERE, not in a doc).
  2. Dispatches work to the stage's executor (cline headless / claude -p),
     scoped to that stage's writable paths, inside a per-task git worktree.
  3. Runs gates in order: deterministic first (structure, tests, lint — free,
     instant), LLM review last (diff-only, cheap). Any deterministic failure
     bounces back to the executor with the JSON violations as the fix prompt —
     never reaches CC, never costs a Claude token.
  4. Bounded retries; on exhaustion, parks the task for human attention.

This is a skeleton: subprocess calls are real, prompts are minimal — extend
prompt templates and notification hooks to taste.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import yaml

STATE_FILE = "tasks/state.json"


# ---------------------------------------------------------------- state ----
def load_state(repo: Path) -> dict:
    p = repo / STATE_FILE
    if p.exists():
        return json.loads(p.read_text())
    return {"tasks": {}}


def save_state(repo: Path, state: dict):
    p = repo / STATE_FILE
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(state, indent=2))


# ------------------------------------------------------------- executors ----
def run(cmd: list[str] | str, cwd: Path, timeout=1800, shell=False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, shell=shell)


def dispatch_cline(prompt: str, workdir: Path) -> dict:
    """Headless Cline run. Cline is authenticated separately (LZ PAYG key in
    its own config) — the orchestrator never handles that credential."""
    r = run(["cline", "-y", "--json", prompt], cwd=workdir)
    try:
        return {"ok": r.returncode == 0, "raw": r.stdout, "json": json.loads(r.stdout)}
    except (json.JSONDecodeError, ValueError):
        return {"ok": r.returncode == 0, "raw": r.stdout + r.stderr, "json": None}


def dispatch_claude(prompt: str, workdir: Path, allowed_tools: str) -> dict:
    r = run(["claude", "-p", "--output-format", "json",
             "--allowedTools", allowed_tools, prompt], cwd=workdir)
    try:
        payload = json.loads(r.stdout)
        return {"ok": r.returncode == 0, "json": payload,
                "text": payload.get("result", "")}
    except (json.JSONDecodeError, ValueError):
        return {"ok": False, "json": None, "text": r.stdout + r.stderr}


# ----------------------------------------------------------------- gates ----
def gate_structure(repo: Path, worktree: Path, base_ref: str) -> tuple[bool, str]:
    r = run([sys.executable, str(repo / "tools" / "validate_structure.py"),
             str(worktree), "--diff-only", base_ref], cwd=worktree)
    return r.returncode == 0, r.stdout


def gate_command(worktree: Path, command: str) -> tuple[bool, str]:
    r = run(command, cwd=worktree, shell=True)
    return r.returncode == 0, (r.stdout + r.stderr)[-4000:]


def gate_llm_review(worktree: Path, base_ref: str, spec_path: str,
                    executors: dict, max_diff_lines: int) -> tuple[bool, str]:
    diff = run(["git", "diff", base_ref, "HEAD"], cwd=worktree).stdout
    if len(diff.splitlines()) > max_diff_lines:
        return False, json.dumps({"verdict": "fail",
                                  "feedback": f"diff exceeds {max_diff_lines} lines; split the chunk"})
    spec_text = (worktree / spec_path).read_text() if (worktree / spec_path).exists() else "(no spec file)"
    prompt = (
        "You are a strict code reviewer. Structural checks already passed; "
        "judge ONLY logic, spec compliance, and edge cases.\n\n"
        f"SPEC:\n{spec_text}\n\nDIFF:\n{diff}\n\n"
        'Respond with ONLY JSON: {"verdict": "pass"|"fail", "feedback": "<specific, actionable>"}'
    )
    res = dispatch_claude(prompt, worktree,
                          executors["claude_code"]["review_allowed_tools"])
    try:
        verdict = json.loads(res["text"].strip().removeprefix("```json").removesuffix("```").strip())
        return verdict.get("verdict") == "pass", verdict.get("feedback", "")
    except (json.JSONDecodeError, ValueError, AttributeError):
        return False, f"unparseable review response: {res['text'][:500]}"


def run_gates(stage: dict, repo: Path, worktree: Path, base_ref: str,
              task: dict, manifest: dict) -> tuple[bool, str]:
    """Deterministic gates first; llm_review is forced last regardless of
    manifest order, so CC only ever sees structurally clean diffs."""
    gates = sorted(stage.get("gates", []), key=lambda g: g["type"] == "llm_review")
    for g in gates:
        t = g["type"]
        if t == "structure_valid":
            passed, out = gate_structure(repo, worktree, base_ref)
        elif t == "command":
            passed, out = gate_command(worktree, g["run"])
        elif t == "file_exists":
            passed = (worktree / g["path"]).exists()
            out = "" if passed else f"missing: {g['path']}"
        elif t == "doc_sections":
            passed, out = gate_structure(repo, worktree, base_ref)  # validator covers sections
        elif t == "tests_exist":
            passed, out = gate_structure(repo, worktree, base_ref)  # validator covers this too
        elif t == "llm_review":
            spec = f"specs/spec_{task['id']}.md"
            passed, out = gate_llm_review(worktree, base_ref, spec,
                                          manifest["executors"],
                                          g.get("max_diff_lines", 800))
        elif t == "human_approval":
            print(f"\n*** HUMAN GATE: task {task['id']} awaiting approval at stage "
                  f"{stage['name']}. Approve with: orchestrator.py approve {task['id']} ***")
            return False, "awaiting_human"
        else:
            return False, f"unknown gate type: {t}"
        if not passed:
            return False, f"[gate:{t}] {out}"
    return True, "all gates passed"


# ------------------------------------------------------------- main loop ----
def process_task(repo: Path, manifest: dict, state: dict, task_id: str):
    task = state["tasks"][task_id]
    stages = {s["name"]: s for s in manifest["stages"]}
    stage = stages[task["stage"]]
    executors = manifest["executors"]

    # per-task worktree
    wt = repo.parent / f"wt-{manifest['project']['id']}-{task_id}"
    branch = f"task/{manifest['project']['id']}-{task_id}"
    if not wt.exists():
        run(["git", "worktree", "add", "-B", branch, str(wt)], cwd=repo)
    base_ref = task.get("base_ref") or run(
        ["git", "rev-parse", "HEAD"], cwd=wt).stdout.strip()
    task["base_ref"] = base_ref

    executor_name = stage.get("executor")
    retries = 0
    max_retries = stage.get("max_retries", 2)
    feedback = ""

    while retries <= max_retries:
        if executor_name:
            prompt = build_stage_prompt(stage, task, feedback)
            if executor_name == "cline":
                res = dispatch_cline(prompt, wt)
            else:
                res = dispatch_claude(prompt, wt,
                                      executors["claude_code"]["write_allowed_tools"])
            if not res["ok"]:
                feedback = f"executor error: {str(res.get('raw', ''))[:1000]}"
                retries += 1
                continue
            run(["git", "add", "-A"], cwd=wt)
            run(["git", "commit", "-m",
                 f"chore({task_id}): {stage['name']} attempt {retries + 1}"], cwd=wt)

        passed, gate_out = run_gates(stage, repo, wt, base_ref, task, manifest)
        if gate_out == "awaiting_human":
            task["status"] = "awaiting_human"
            return
        if passed:
            task["stage"] = stage.get("next", task["stage"])
            task["status"] = "done" if stage.get("terminal") else "pending"
            task["base_ref"] = None
            log(repo, task_id, f"{stage['name']} PASSED -> {task['stage']}")
            return
        feedback = gate_out
        log(repo, task_id, f"{stage['name']} attempt {retries + 1} failed: {gate_out[:300]}")
        retries += 1

    task["status"] = "parked"
    log(repo, task_id, f"{stage['name']} PARKED after {max_retries + 1} attempts")


def build_stage_prompt(stage: dict, task: dict, feedback: str) -> str:
    base = (f"Task {task['id']}: {task['description']}\n"
            f"Stage: {stage['name']}. "
            f"Read specs/spec_{task['id']}.md and dev_steps/steps_{task['id']}.md if present. "
            f"Only modify files under your permitted paths for this stage.")
    if feedback:
        base += f"\n\nPREVIOUS ATTEMPT FAILED GATES. Fix exactly these issues:\n{feedback}"
    return base


def log(repo: Path, task_id: str, msg: str):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{task_id}] {msg}\n"
    (repo / "tasks" / "progress.md").parent.mkdir(exist_ok=True)
    with open(repo / "tasks" / "progress.md", "a") as f:
        f.write(line)
    print(line, end="")


def main():
    if len(sys.argv) < 2:
        print("usage: orchestrator.py <repo> [run|add <id> <desc...>|approve <id>|status]")
        sys.exit(2)
    repo = Path(sys.argv[1]).resolve()
    manifest = yaml.safe_load((repo / "project_manifest.yaml").read_text())
    state = load_state(repo)
    cmd = sys.argv[2] if len(sys.argv) > 2 else "run"

    if cmd == "add":
        tid, desc = sys.argv[3], " ".join(sys.argv[4:])
        state["tasks"][tid] = {"id": tid, "description": desc,
                               "stage": manifest["stages"][0]["name"],
                               "status": "pending", "base_ref": None}
    elif cmd == "approve":
        state["tasks"][sys.argv[3]]["status"] = "pending"
        # human gate satisfied -> advance
        t = state["tasks"][sys.argv[3]]
        stages = {s["name"]: s for s in manifest["stages"]}
        t["stage"] = stages[t["stage"]].get("next", t["stage"])
    elif cmd == "status":
        print(json.dumps(state, indent=2))
    else:  # run
        for tid, t in state["tasks"].items():
            if t["status"] == "pending":
                process_task(repo, manifest, state, tid)

    save_state(repo, state)


if __name__ == "__main__":
    main()
