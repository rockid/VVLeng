# MANIFEST_SUMMARY — plain-English review of project_manifest.yaml

**What it encodes (descriptive-first — rules match the repo as it is today):**
- **Structure:** requires the 4 production packages the smoke test exercises
  (`collector`, `processor`, `content`, `planner`) + `clients`, `tests`, `docs`,
  `tools`, and the 3 pipeline dirs to be created (`architecture`, `specs`, `dev_steps`).
- **Placement/naming (all already hold):** `test_*.py`/`conftest.py` under `tests/`,
  `TASK-*.md` under `.cline-tasks/`, snake_case for every `.py`, `NN-name.md` for
  `.clinerules/`. Future `spec_*.md`/`steps_*.md` conventions declared for the new dirs.
- **Protected (agent-untouchable):** `.env`, `.git/`, the manifest itself,
  `config.yaml`, both client YAMLs (`Joinee`, `vivendix`), and all of
  `content/prompts/` — every path that could alter live Joinee output.
- **Stages:** architecture → specs → dev_steps → dev → assembly → sandbox → prod.
  Real gates wired: `pytest` (installed). Two gates carry `<TODO>` because the repo
  can't run them yet: **ruff** (not a dependency) and **sandbox smoke** (wrapper
  script not written). Both are in MIGRATION.md.
- **Executors:** `cline` writes only `src/`+`tests/`+`dev_steps/` (dev); `claude_code`
  review is read-only (`Read` + `git diff` + `pytest`).

**Verification:** `validate_structure.py .` reports exactly 5 violations, all the
intended "create these framework dirs/files" gaps — zero placement/naming/doc
failures. See MIGRATION.md.

**The 5 most consequential judgment calls (approve these):**
1. **No `src/` in this repo, but I kept cline's write scope literal to `src/` as
   instructed.** Effect: autonomous agents write NEW code under `src/`; the existing
   production packages stay OUT of their write scope — conservative for a live
   system. Side effect: the `tests_exist` gate (hard-coded to `src/`) is inert.
   MIGRATION Tier C offers a small tool patch to fix that without moving code.
2. **No blanket `*.py` placement rule.** Code is organised by feature package plus
   root entry points (`run_pipeline.py`, `config_loader.py`); forcing `.py` into one
   tree would misrepresent the dominant pattern and falsely flag the entry points.
3. **`protected_paths` scope calls:** protected live config + client YAMLs + all
   runtime prompts; deliberately did **not** protect `.clinerules/` (existing
   workflow has sessions edit its status table) or `requirements.txt` (dependency
   changes are legitimate reviewed dev work).
4. **Widened the git branch/commit regexes** to match real history — human
   `feat|fix|docs|infra` branches (no project-id segment) alongside orchestrator
   `task/vvleng-*`, and optional commit scope incl. an `infra` type — rather than
   the template's narrow `task|fix|exp` + mandatory scope, which the actual log fails.
5. **Declared `master` integration-only + `prod_promotion: tag`.** The system is
   live for Joinee with no deploy pipeline (Phase 1, local); prod must be promoted
   by a deliberate tag/branch, never straight from `master` HEAD. Prerequisite for
   any autonomous merge — flagged to MIGRATION Tier C + OWNER-ACTIONS.
