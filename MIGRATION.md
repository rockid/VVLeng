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

- [x] **Add `ruff`** — DONE. Added `ruff==0.6.9` + `ruff.toml` (E,F,I; E501 off;
      `__init__.py` F401-exempt; `scratch/` excluded), commit `006aa10`. Decision
      taken (operator delegated): **cleaned the debt first**, then wired the gate.
      `ruff check --fix` cleared all 27 findings (commit `09d31f2`, no behaviour
      change, 48 tests pass, smoke exit 0); dev-lint gate then wired to the real
      `ruff check ...` with `must_pass` against a clean baseline (commit `bb813d6`).
- [x] **Create `tools/sandbox_smoke.sh`** — DONE. Wraps the `--dry-run` smoke with
      the UTF-8 env; verified exit 0. Commit `0c87886`. Sandbox gate `<TODO>` swapped
      to `bash tools/sandbox_smoke.sh` (operator approved the manifest edit),
      commit `bb813d6`.

## Tier C — production-adjacent / needs a human decision (operator delegated these to CC)

- [~] **Prod deploy separation** (the load-bearing production-safety item). Decision
      taken: **`prod` branch** rail (chosen over tags for solo-operator simplicity).
      Manifest now declares `git.prod_branch: prod` + `prod_promotion: branch`
      (master = integration-only), commit `3e42fe6`. The pre-commit hook blocks
      direct commits to `prod`. **Remaining (human, post-merge):** actually cut the
      `prod` branch from the reviewed master and run production only from it — the
      exact commands are in `OWNER-ACTIONS.md`. Not done now because prod must be cut
      *after* this branch merges. Operator confirmed 2–3 day runway makes this safe.
- [x] **`tests_exist` gate decision.** Decision taken (operator delegated "you decide
      what's optimal"): **patched `check_tests_exist`** to read `structure.source_dirs`
      (the 4 core pipeline packages) and fire only on git-**added** modules missing
      `tests/test_<stem>.py` — forward TDD discipline without blocking edits to
      pre-existing untested modules. NOT the `src/` consolidation (high blast radius,
      rejected). Commit `bedfbaf`; verified (flags a new module, ignores `db/` +
      `__init__.py`, passes when the stem test exists).

## Tier D — the last step (deferred to the operator by design + auto-mode guard)

- [~] **Install the enforcement hook.** The committed `tools/pre-commit` was
      **improved** (commit — see below): it now runs **full-repo** validation (the
      original `--diff-only HEAD` was `git diff HEAD HEAD`, an empty no-op) and also
      blocks direct commits to `prod`. **NOT installed into `.git/hooks/`** — that
      persists execution beyond a session and the original instruction was "the last
      step"; an agent auto-mode guard also (correctly) blocked it, and the `prod`
      branch prerequisite doesn't exist yet. Install step + commands recorded in
      `OWNER-ACTIONS.md`, to run once merged. Also install into each orchestrator
      worktree (`.git/hooks/` is per-clone, not version-controlled).

### Extra (git management, operator delegated)
- [x] **`.gitattributes`** pinning `*.sh` + `tools/pre-commit` to LF so Windows
      autocrlf can't put `\r` in a shebang and break `sh`. Commit `5e4dfc0`.

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
