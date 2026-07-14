# Architecture Overview — VV_Leng

This is the **stage-pipeline entry artifact** (`architecture` stage in
`project_manifest.yaml`). It is a concise orientation; the authoritative design
lives in the deeper docs linked below.

## What VV_Leng is

A semi-automated LinkedIn engagement pipeline. It collects LinkedIn posts via
Apify, filters/scores/ranks them, generates candidate comments with an LLM, and
hands a human a ranked daily action plan (CSV + self-contained HTML operator UI).
**No action on LinkedIn itself (commenting, connecting, posting) is automated** —
that stays manual by design (ToS compliance). It is **in production for client
Joinee**.

## Pipeline shape

`run_pipeline.py` orchestrates, in order:

```
collect (Apify) -> tier-tag -> semantic filter -> content filters
  -> relevance gate (LLM judge) -> score + blended ranking
  -> comment generation (3 variants) -> comment ranking (LLM judge) -> outputs
```

Outputs: `comment_sheet_{date}.csv`, an HTML operator runner, and a JSON daily plan
under `data/{client}/` (gitignored, regenerable).

## Module map

| Dir | Responsibility |
|---|---|
| `collector/` | Apify actor runner, normaliser, incremental dedup |
| `processor/` | semantic filter, relevance gate, scoring, dedup |
| `content/` | LLM client, comment generation, `prompts/` (live prompt files) |
| `planner/` | daily plan, output writers, comment runner |
| `clients/` | per-client config (`Joinee.yaml` live, `vivendix.yaml`) |
| `db/`, `dashboard/`, `feedback/` | partial/optional (DB not yet wired; dashboard Daily Plan tab live; feedback sheet shipped) |

## The one rule that matters most

Every external/paid call (LLM, scraper, API) must work in both a real mode and a
free `dry_run` mock mode from the same call site. `--dry-run` mocks both
`collector/apify_client.py` and `content/llm_client.py` (no live call, no key) and
implies `--no-persist` — the zero-cost way to exercise the full pipeline.

## Deeper references

- `docs/pipeline_runbook.md` — the actually-implemented state (read first).
- `docs/VVLeng_architecture.md` + `docs/VVLeng_architecture_amendment_combined.md`
  — target design (the amendment supersedes the base on conflict).
- `docs/architecture_backlog.md` — read-only backlog (never implement without an
  explicit promotion instruction).
- `.clinerules/` — session procedures, coding standards, workflow, secrets policy.
