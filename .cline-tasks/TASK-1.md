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

**Naming decision — RESOLVED 2026-06-24:** option (a). `--dry-run` is repurposed to
match the umbrella convention: skip persistence *and* mock external (Apify/LLM)
calls. The current persistence-only behavior moves to a new `--no-persist` flag.
Rationale: matches every other project in this umbrella, and closes a cost footgun
— today `--dry-run` *looks* safe/free but still makes live paid calls. This is a
breaking change to `--dry-run`'s existing meaning; call it out in the PR/commit
body and update every doc reference (`00-project-overview.md`, `01-session-start.md`,
`02-session-end.md`, `05-secrets-and-safety.md`, `docs/pipeline_runbook.md`) since
they all currently describe `--dry-run` as "skip persistence only" / "does not stop
live calls."

Implementation, in order:
- Add `--no-persist` (store_true) to `run_pipeline.py`, wired to exactly the
  persistence-skip behavior `--dry-run` currently gates (the `if not args.dry_run`
  / `if args.dry_run` branches around shortlist CSV, comment sheet, and plan-file
  writes).
- Redefine `--dry-run` to set both the mock-external flag *and* imply
  `--no-persist` (dry-run should never write to disk either).
- Then:
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

- Full pipeline (`run_pipeline.py --dry-run`, no `--skip-collect`/`--skip-llm`) runs
  end-to-end with zero API keys set.
- `--no-persist` alone reproduces exactly today's `--dry-run` behavior (plan
  printed to stdout, no CSV/plan-file writes) with live calls still firing —
  i.e. the rename preserved the old behavior under the new name.
- Mock output is unmistakably fake (explicit marker), never a plausible stand-in
  for real data downstream.
- Existing tests (`tests/`) and the current smoke test still pass unchanged
  (the smoke test uses `--skip-collect --skip-llm`, not `--dry-run`, so it's
  unaffected by the rename).
- Real/live behavior is unchanged when neither flag is passed.
- Every doc reference to `--dry-run`'s old meaning is updated in the same PR.

## Constraints

- Don't touch the existing `--skip-collect`/`--skip-llm`/`--no-relevance-gate`
  flags' behavior — they're a separate, already-working mechanism.
- Don't fan out into live calls while testing this — build and verify the mock
  path itself for free; only do one live spot-check at the end, with the user's
  go-ahead.
