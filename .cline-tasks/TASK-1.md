# TASK-1 — Add a free dry-run/mock mode for Apify and LLM calls

**Source:** org-framework adoption audit, 2026-06-24 (ADOPTION.md Step 4)
**Priority:** 2 — doesn't block other work, but is the umbrella's "one rule that
matters most" and is currently unmet
**Type:** new code (integration)
**Branch:** `infra/add-dry-run-mode`
**Depends on:** — (no owner action needed; no account/cost decision required to
write the mock paths themselves)

## Why this exists

`collector/apify_client.py` and `content/llm_client.py` are both live-only — every
pipeline run that doesn't pass `--skip-collect --skip-llm` spends real money, and
there's no way to exercise the full collect→comment-gen flow with zero keys. Every
other project in this umbrella supports a free `dry_run` mock path from the same
call site (see `.clinerules/03-coding-standards.md`); VV_Leng doesn't yet.

## Scope

**Decide the flag naming first, before writing code** — `--dry-run` already exists
in `run_pipeline.py` and means "compute the plan but skip persistence" (it does
*not* stop live calls today). This task must not silently redefine that. Pick one
and confirm with the user/architecture session before implementing:
- (a) Repurpose `--dry-run` to match the umbrella convention (skip persistence
  *and* mock external calls) and rename the current persistence-only behavior to
  something like `--no-persist`, or
- (b) Add a distinctly-named flag/config (`--mock`, or `mock_external: true` in
  `config.yaml`) and leave the existing `--dry-run` meaning untouched.

Then:
- Add a `dry_run`/`mock` branch to `collector/apify_client.py`'s `run_actor()` (or
  `_run_actor_once()`) that returns fake post dicts shaped like real output —
  `tests/fixtures/sample_post_search.json` already captures the real
  `harvestapi/linkedin-post-search` shape, use it as the mock source rather than
  inventing a new shape.
- Add the same branch to `content/llm_client.py`'s `complete()`, returning an
  obviously-fake string (e.g. prefixed `[MOCK LLM]`).
- Route the flag through central config (`config_loader.py`), not a scattered
  literal — `run_pipeline.py` should pass it down, not check it ad hoc per stage.

## Files to touch

- `collector/apify_client.py` — mock branch in the actor-run path
- `content/llm_client.py` — mock branch in `complete()`
- `config_loader.py` / `config.yaml` — the flag itself
- `run_pipeline.py` — wire the flag through the pipeline stages
- `docs/pipeline_runbook.md`, `.clinerules/00-project-overview.md` — update once
  built; the "one rule" gap note there should be removed/updated

## Acceptance criteria

- Full pipeline (`run_pipeline.py` with no `--skip-collect`/`--skip-llm`) runs
  end-to-end with zero API keys set, when mock mode is on.
- Mock output is unmistakably fake (explicit marker), never a plausible stand-in
  for real data downstream.
- Existing tests (`tests/`) and the current smoke test still pass unchanged.
- Real/live behavior is unchanged when the flag is off.

## Constraints

- Don't touch the existing `--skip-collect`/`--skip-llm`/`--no-relevance-gate`
  flags' behavior — they're a separate, already-working mechanism.
- Don't fan out into live calls while testing this — build and verify the mock
  path itself for free; only do one live spot-check at the end, with the user's
  go-ahead.
