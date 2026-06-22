# VVLeng Pipeline — Runbook (current implemented state)

**As of 2026-06-22.** Describes what the pipeline *actually does today* and how to run it.
For the target design see `VVLeng_architecture.md` + `VVLeng_architecture_amendment_combined.md`.
Active client: **Joinee** (`clients/Joinee.yaml`, data under `data/Joinee/`).

## What it does (end to end)

```
collect (Apify) → tag tier → semantic filter → content filters → LLM relevance gate
   → blended ranking → LLM comment generation → comment ranking → outputs (sheet + UI + plan)
```

| Stage | Module | Notes |
|---|---|---|
| Collect | `collector/apify_client.py` | harvestapi/linkedin-post-search, `sortBy=relevance`, 50/keyword, 1-week window. 30-min poll timeout (avoids retry double-charge). |
| Tier tag | `run_pipeline.tag_posts_by_keyword_tier` | Tags by **source_query** (which keyword found the post), not text-match. tier1=direct, tier2=lateral. |
| Semantic filter | `processor/semantic_filter.evaluate_posts` | Batched `all-MiniLM-L6-v2`; drops off-niche + blocked substrings + too-short. Stores `semantic_score` on kept posts. |
| Content filters | `run_pipeline.apply_content_filters` | Max age, per-tier min engagement, duplicate text. |
| Relevance gate | `processor/relevance_gate.py` | **LLM judge, on by default.** Scores ICP fit / commentability / value; keeps the worth-it posts. Reuses `build_niche_prompt_context()`. |
| Scoring + blend | `processor/post_scorer.py` | Heuristic (freshness·velocity·relevance·opportunity) **blended 50/50 with the gate score** into `rank_score`. Gate-kept posts can't be vetoed by the heuristic threshold. |
| Comment gen | `content/comment_gen.py` | 3 variants, hook→value→closer, non-promotional, **no fabricated stats**. |
| Comment rank | `content/comment_gen.rank_comment_variants` | **LLM judge** orders the 3 best-first + tags top with `confidence` (1-5) and `safe_to_autopost`. |
| Outputs | `run_pipeline` + `scratch/build_comment_ui.py` | See below. |

## How to run

```bash
# Full daily run (collect + everything). Gate + comments ON by default.
python run_pipeline.py --client Joinee

# Reprocess already-collected posts (NO Apify spend). Gate runs (small LLM cost).
python run_pipeline.py --client Joinee --skip-collect

# Free reprocess, no LLM at all (no gate, no comments):
python run_pipeline.py --client Joinee --skip-collect --skip-llm --no-relevance-gate

# Build the operator comment UI from the latest comment sheet:
python scratch/build_comment_ui.py

# Generate 5 content-post topic ideas from the corpus:
python scratch/topic_ideas.py
```
> Windows: prefix with `PYTHONUTF8=1` (post text/emoji crash cp1252 stdout otherwise).

**Flags:** `--skip-collect` (reuse newest saved `data/{client}/raw/posts*.json`), `--skip-llm`
(no comments; also suppresses the gate), `--no-relevance-gate` (gate off), `--dry-run`,
`--keywords "a,b"`, `--client X`.

## Outputs (`data/Joinee/output/`)

| File | Purpose |
|---|---|
| `comment_sheet_{date}.csv` | **Primary.** Ranked targets + URL + post + 3 comments (best-first) + `top_confidence`/`top_reason`/`safe_autopost`. Posts sorted best-first by `rank_score`; `comment_1` = judge's top pick. |
| `comment_runner_{date}.html` | Self-contained operator UI: open post → copy top pick → Done/Skip → **Export feedback CSV**. Top pick shown, alternatives collapsed. No server. |
| `shortlist_{date}.csv` | Full ranked comment_targets (no comments). |
| `topic_ideas_{date}.json` | 5 original-post topic ideas (hook + angle), engagement-mined from the corpus. |
| `data/Joinee/plans/{date}_plan.json` | Structured daily plan. |

## Two-level ranking (the "grab #1 blindly" workflow)

- **Posts** sorted best-first by `rank_score` = 0.5·heuristic + 0.5·gate (ICP/intent).
- **Comments** within each post sorted best-first by the LLM judge; `comment_1` is the pick with a confidence (5 = post blindly, lower = human glance).

So: go top-down, grab `comment_1`, take the top N for the day. `confidence` + `safe_autopost`
are the levers for eventual near-full automation (auto-post conf-5/safe, route the rest to a human).

## Key config (`clients/Joinee.yaml` / `config.yaml`)

- `collection.posts_per_keyword: 50`, Apify `sortBy=relevance`, 1-week window.
- `filter.min_semantic_similarity: 0.35` (+ tier multipliers 1.0/1.2/0.85).
- `scoring.min_comment_target_score: 0.45` (shortlist strictness; gate can override).
- `action_limits.comments_per_day: 30`.

## Open items / next

- **Operator feedback loop** — the comment runner exports `commented_log_{date}.csv` (which post got
  which comment). Not yet consumed by the pipeline. Prerequisite for the carry-over pool.
- **Carry-over / persistent post pool** — let un-commented fresh candidates persist into the next day's
  shortlist (bounded to ~48-72h comment-eligibility), and decouple collection cadence from commenting
  cadence (collect every 2-3 days, comment daily). Needs persistence (JSON pool MVP, then DB).
- **Architecture gaps still open** — DB persistence not wired (no cross-run dedup/state), Route 1/3,
  signal extraction, weekly brief. See `progress.md` for full status.
- **Sibling project** — `kgraph/docs/demand-graph-approach.md` captures the content-topic "demand graph"
  design that reuses this corpus + extraction layer.
