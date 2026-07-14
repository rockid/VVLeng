# MIGRATION — bringing VV_Leng into conformance with project_manifest.yaml

Every current deviation from the manifest, as a mechanical checklist ordered by
**risk** (pure additions first; anything imported by production code, or that
changes the human workflow, last; installing the enforcement hook is the final
step). Do not install `tools/pre-commit` until Tier A is complete — it hard-blocks
every commit while the 5 verified violations below still exist.

## Verified baseline

`python tools/validate_structure.py .` (full repo, against this manifest) reports
**exactly 5 violations, all intentional** — the framework dirs/files the mandated
stage pipeline needs but that don't exist yet. **Zero** placement, naming, or
doc-section violations: the repo already matches every descriptive rule. The list
below is that verified output plus the manifest's `<TODO>` gate items and noted
decisions.

---

## Tier A — zero-risk additions (clears all 5 validator violations; touches no code)

- [x] **Create `specs/`** — added `specs/.gitkeep` (a `.md` there would trip the
      `spec_*` naming rule). Cleared `required_dir: specs/`. Commit `7b299c8`.
- [x] **Create `dev_steps/`** — added `dev_steps/.gitkeep`. Cleared
      `required_dir: dev_steps/`. Commit `e87275d`.
- [x] **Create `architecture/` + `architecture/overview.md`** — concise entry doc
      linking to `docs/`. Cleared `required_dir: architecture/` +
      `required_file: architecture/overview.md`. Commit `6530c82`.
- [x] **Create `README.md`** at repo root. Cleared `required_file: README.md`.
      Commit `2584b47`.

**Tier A DONE** — `python tools/validate_structure.py .` prints `"status": "pass"`
(0 violations); 48 tests green after each item.

## Tier B — additive tooling (no production imports; each is self-contained)

- [~] **Add `ruff`** — DONE-PARTIAL. Added `ruff==0.6.9` to `requirements.txt` +
      `ruff.toml` (select E,F,I; E501 off; `scratch/` excluded). Commit `006aa10`.
      Report mode surfaced **27 pre-existing findings** (16 `I001` unsorted-imports,
      11 `F401` unused-import), all auto-fixable. **DEFERRED:** the manifest
      dev-stage lint gate `<TODO>` was NOT wired to a real `must_pass` command —
      doing so against 27 lines of pre-existing debt would leave a knowingly-failing
      gate, and MIGRATION says those fixes are separate commits. Needs a decision:
      clean the debt first (a `ruff check --fix` commit) then wire `must_pass`, or
      wire it now and accept dev-stage is blocked until debt clears.
- [x] **Create `tools/sandbox_smoke.sh`** — DONE. Wraps
      `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python run_pipeline.py --client Joinee --dry-run`;
      verified runs green (exit 0). Commit `0c87886`. **PENDING:** swapping the
      sandbox gate's `<TODO>` string to `bash tools/sandbox_smoke.sh` edits the
      approved+protected `project_manifest.yaml` — left for a human go-ahead (one line).

## Tier C — production-adjacent / needs a human decision (do NOT do mechanically)

- [ ] **Prod deploy separation** (the load-bearing production-safety item). Today
      `master` is the de-facto deploy source: "production" = the operator running
      `run_pipeline.py --client Joinee` from a local checkout, normally on `master`.
      The manifest now declares `git.prod_promotion: tag` and `master` as
      integration-only. Make that real: cut a `prod`/release tag (or a `prod`
      branch) that the operator advances deliberately, so an autonomous agent
      merge to `master` can never become "what runs against Joinee next." Record
      the chosen mechanism in `OWNER-ACTIONS.md`. **Prerequisite before enabling
      any autonomous merge near this repo.**
- [ ] **`tests_exist` gate decision.** `tools/validate_structure.py` hard-codes
      this check to `src/*.py`; this repo has no `src/`, so the gate is currently
      **inert** — it never fires for the real code in `collector/`, `processor/`,
      etc. Pick one: **(a)** patch `check_tests_exist` to scan the feature packages
      instead of `src/` (small tool change, no repo-wide move — recommended), or
      **(b)** consolidate code under `src/` (touches every import in the repo —
      high blast radius, contradicts descriptive-first; only if the team wants a
      single source tree). This is coupled to the executor-scope call (SUMMARY
      judgment #1/#4) — decide them together.

## Tier D — the last step, only after Tier A passes clean

- [ ] **Install the enforcement hook.** Copy `tools/pre-commit` →
      `.git/hooks/pre-commit` and mark it executable (`chmod +x`). The hook (1)
      blocks direct commits to `main`/`master` and (2) runs
      `validate_structure.py --diff-only HEAD` on every commit. Installing it
      before Tier A is done would block all commits on the 5 violations. Note it
      only runs in the repo it's installed into — also install it into each
      per-task worktree the orchestrator creates.

---

## Noted, not enforced (no action required; awareness only)

- **`docs/*.md` naming is inconsistent** (`VVLeng_architecture.md` CamelCase,
  `pipeline_runbook.md` snake_case, `CC_FINISH_UP_2026-07-05.md` / `FEEDBACK_SHEET.md`
  UPPER_CASE). No dominant pattern exists, so the manifest deliberately imposes no
  `docs/*.md` naming regex. Normalise later only if the team wants to; not a blocker.
- **`tests/test_noise_classifier.py` and `tests/test_feedback_sheet.py` don't map
  1:1 to a module stem** (`feedback_sheet` → `feedback/sheet_client.py`;
  `noise_classifier` has no dedicated module). Irrelevant while `tests_exist` is
  inert; revisit only if Tier C item (a)/(b) activates that gate with stem-matching.
- **`scratch/`** holds exploratory scripts (and one `.txt`) that are snake_case and
  violate nothing. They are explicitly "not part of the maintained pipeline"
  (`.clinerules/00`); left unconstrained by design.
