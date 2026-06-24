# Project Overview

Orients any session at the start of a task. Keep it accurate as the project grows —
if it drifts from reality, every other rule file becomes less reliable.

## What this is

VV_Leng (a.k.a. "VVLeng") is a **semi-automated LinkedIn engagement pipeline**: it
collects LinkedIn posts via Apify, filters/scores/ranks them, generates candidate
comments with an LLM, and hands a human a ranked daily action plan (CSV sheet +
self-contained HTML operator UI). No action on LinkedIn itself (commenting,
connecting, posting) is automated — that stays manual by design (ToS compliance).
Part of the VV marketing-automation umbrella; its corpus/extraction layer is also
reused by the sibling `kgraph` project's "demand graph" work. Full design lives in
`docs/VVLeng_architecture.md` + `docs/VVLeng_architecture_amendment_combined.md`;
the actually-implemented state is in `docs/pipeline_runbook.md` — read the runbook
first, it reflects reality more closely than the original architecture doc.

## Current scope / status

| Area / Stage | Status | What it does |
|---|---|---|
| Collect (Apify) | ✅ built | `harvestapi/linkedin-post-search`, live-only — no mock mode (see "the one rule" below) |
| Tier tagging | ✅ built | Tags posts tier1/tier2 by which search keyword found them |
| Semantic filter | ✅ built | Batched MiniLM embedding filter, drops off-niche/blocked/too-short |
| Content filters | ✅ built | Max age, per-tier min engagement, duplicate text |
| Relevance gate (LLM judge) | ✅ built, on by default | Scores ICP fit / commentability / value |
| Scoring + blended ranking | ✅ built | Heuristic score blended 50/50 with gate score into `rank_score` |
| Comment generation + ranking | ✅ built | 3 variants per post, LLM judge orders best-first with confidence |
| Outputs | ✅ built | `comment_sheet_{date}.csv`, HTML operator runner, JSON daily plan |
| DB persistence | ❌ not wired | `db/models.py` exists but the pipeline doesn't read/write cross-run state through it yet |
| Dashboard (Streamlit) | 🚧 partial | Daily Plan tab built; Analytics and Leads tabs are stubs |
| Operator feedback loop | ❌ not built | Comment runner exports `commented_log_{date}.csv`; pipeline doesn't consume it yet |
| Route 1 (influencer watchlist) / Route 3 (follower graph) | ❌ not built / locked | Gated on actor validation (Route 1) or a stability window (Route 3) — see `docs/architecture_backlog.md` |

**Do not assume later-stage infrastructure exists just because a schema/config has
placeholder fields for it.** Treat placeholder-only features (DB persistence, the
feedback loop, Routes 1/3) as new code, not as an extension of something half-built.

## Repo layout

```
VV_Leng/
├── run_pipeline.py       # main orchestrator: collect -> tier-tag -> semantic filter
│                         #   -> content filters -> relevance gate -> score/rank
│                         #   -> comment gen -> comment rank -> outputs
├── config.yaml           # non-secret global config (active client, actor IDs, models, defaults)
├── config_loader.py      # merges config.yaml + clients/{client}.yaml + .env
├── clients/              # per-client overrides (active: Joinee.yaml); _template.yaml for new clients
├── collector/            # apify_client.py (actor runner), normaliser.py, incremental.py
├── processor/            # semantic_filter.py, relevance_gate.py, post_scorer.py, dedup.py
├── content/              # llm_client.py, comment_gen.py, prompts/
├── planner/              # daily_plan.py, output.py
├── db/                   # SQLAlchemy models + session (not yet wired into the pipeline)
├── dashboard/            # Streamlit app + views (Daily Plan tab live)
├── data/{client}/        # generated per-client output - gitignored, regenerable
├── docs/                 # architecture, runbook, backlog, test plans
├── scratch/              # working/exploratory scripts - not part of the maintained pipeline
└── tests/                # pytest unit tests
```

## Tech stack

- Python 3.x. Key libraries: `httpx` (Apify REST, no official SDK), `openai` SDK
  (pointed at the laozhang.ai OpenAI-compatible gateway), `sentence-transformers`
  (semantic filter), `scikit-learn`/`numpy` (scoring), `sqlalchemy`+`alembic` (DB,
  built but not wired), `streamlit` (dashboard), `pytest`.
- External services: **Apify** (LinkedIn post search/scrape — wired, live-only) and
  an **LLM gateway** via laozhang.ai (model configurable per call — wired, live-only).
  Both are real paid calls with no mock path today.

## The one rule that matters most

This umbrella's standing invariant is: **every external/paid call (LLM, scraper,
API, DB) must work in both a real mode and a free `dry_run` mock mode from the same
call site**, so the project is runnable and testable with zero keys and zero cost.
See `03-coding-standards.md` for the pattern.

**VV_Leng does not yet honor this for its two paid integrations.**
`collector/apify_client.py` and `content/llm_client.py` have no mock path — the
existing `--dry-run` CLI flag only suppresses persistence, it does not stop the
live calls. The actual zero-cost path today is `--skip-collect --skip-llm` (and
`--no-relevance-gate` to also skip the gate's LLM calls). Don't run the pipeline
without those flags unless you intend to spend money. This gap is tracked as
`.cline-tasks/TASK-1.md` rather than retrofitted as part of this adoption.
