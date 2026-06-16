# VVLeng — Pipeline Progress

> Auto-generated during setup. Update this file as you go through CLINE.md milestones.

## Phase 0 — Foundation

| Module | Status | Notes |
|--------|--------|-------|
| `config.yaml` | ✅ Done | Three-layer config: defaults → client → env secrets |
| `config_loader.py` | ✅ Done | Dataclass-based loader with YAML + env merge |
| `clients/_template.yaml` | ✅ Done | Template with all client config fields |
| `clients/Joinee.yaml` | ✅ Done | First client config (recruitment SaaS niche) |
| `run_pipeline.py` | ✅ Done | Orchestrator with `--dry-run`, `--client`, `--skip-*` flags |
| `collector/apify_client.py` | ✅ Done | Accepts `config` param for token/raw_dir |
| `collector/normaliser.py` | ⬜ Done (pre-existing) | |
| `collector/incremental.py` | ⬜ Done (pre-existing) | |
| `processor/dedup.py` | ⬜ Done (pre-existing) | |
| `processor/scorer.py` | ✅ Done | Accepts `config` param for scoring thresholds |
| `processor/semantic_filter.py` | ✅ Done | sentence-transformers pre-filter, zero API cost |
| `processor/post_scorer.py` | ✅ Done | Heuristic post scoring — freshness/velocity/relevance/opportunity |
| `content/llm_client.py` | ✅ Done | Accepts `config` param for model/api_key/base_url |
| `content/comment_gen.py` | ✅ Done | Accepts `config` param, passes through to LLM |
| `content/prompts/` | ⬜ Done (pre-existing) | |
| `planner/daily_plan.py` | ✅ Done | Accepts `config` param for limits/niche |
| `planner/output.py` | ⬜ Done (pre-existing) | |
| `db/session.py` | ✅ Done | Accepts `config` param for DB URL |
| `db/models.py` | ⬜ Done (pre-existing) | |
| `.env` | ✅ Done | Secrets-only |
| `.env.example` | ✅ Done | Secrets-only template |
| `requirements.txt` | ⬜ Done (pre-existing) | +sentence-transformers added |

## Next Milestones

- [x] **Phase 1**: Acceptance test (`python run_pipeline.py --dry-run`)
- [x] **Phase 2**: Semantic filter + post scorer + tier-1/tier-2 pipeline
- [ ] **Phase 3**: Dashboard integration + Redis state
- [ ] **Phase 4**: LinkedIn action executor (manual-in-browser mode)
- [ ] **Phase 5**: CI/CD, monitoring, multi-client orchestration

---

## Session Log

### 2026-06-14 17:57
Phase: 0 | Step: Testing & Bugfixing
Status: DONE
Files changed: clients/Joinee.yaml, config_loader.py, .env, content/prompts/comment_user.txt, docs/VVLeng_instructions.md
Test result: PASS — 16 unit tests + full E2E pipeline (30 posts → 90 comments → 8 actions)
Notes:
- Fixed YAML `!string` tag parsing error in Joinee.yaml
- Fixed DB URL to be client-aware in config_loader.py
- Removed hardcoded DATABASE_URL from .env
- Fixed Apify actor URL from slash to tilde (harvestapi/linkedin-post-search)
- Rewrote normaliser to match harvestapi field mapping
- Added build_actor_input() for harvestapi keyword schema
- Fixed download_dataset() token propagation
- Removed broken profile/follower actors (404 errors)
- Fixed LLM prompt bug: `{post_text[:500]}` → `{post_text}` (Python .format() doesn't support slice syntax)
- Verified normaliser with fixture — all fields match
- Real collector test: 30 posts fetched and normalised ✅
- LLM connectivity test: "Hello! It's great to meet you." ✅
- Full E2E pipeline (production run): python run_pipeline.py --dry-run — 30 posts collected, 90 comments generated, 8 actions planned ✅
- Created docs/VVLeng_instructions.md — daily usage manual

Next session: Run **production (non-dry-run)** to save first plan file to `data/plans/`, then begin Phase 1 (profile extraction, author scoring, engagement tracking).

### 2026-06-15 10:10
Phase: 0 | Step: CLINE.md — Add Git Discipline + strengthen progress.md enforcement
Status: DONE
Files changed: CLINE.md
Test result: N/A
Notes:
- Added Section 9 (Git Discipline): commit triggers, conventional commit format, what NOT to commit, pre-commit verification
- Updated Section 3 (Status Reporting): after every [DONE], update progress.md and commit if applicable
- Updated Section 8 (progress.md): widened trigger from "phase step" to "every step"; added "do not start new step until logged"
- Renumbered old Section 9 → 10 (What NOT to Do), old Section 10 → 11 (Session End Protocol)
- Inserted Step A2 in Section 11: git commit between progress.md write and session summary

### 2026-06-17 00:53
Phase: 2 | Step: Semantic filter + post scorer + tier-1/tier-2 scratch pipeline
Status: DONE
Files changed: processor/semantic_filter.py (new), processor/post_scorer.py (new), scratch/run_tier1_tier2.py (new), clients/Joinee.yaml (enhanced keywords), config.yaml (semantic filter thresholds), requirements.txt (added sentence-transformers)
Test result: PASS — `python scratch/run_tier1_tier2.py` — 1290 raw items → 586+704 normalised → 342 after semantic filter → 220 after age/engagement/dedup → 30 comment actions planned in ranked shortlist. sentence-transformers model (all-MiniLM-L6-v2) downloaded and cached successfully.
Notes:
- Created `processor/semantic_filter.py` — sentence-transformers pre-filter with blocked substrings, min length, and cosine similarity with tier multiplier (1.0/1.2/0.85)
- Created `processor/post_scorer.py` — heuristic post scoring with 4 dimensions: freshness (6h→12h→24h→48h), velocity (soft-cap at 10/hr), relevance (keyword tier), opportunity (5–30 comments sweet spot)
- Created `scratch/run_tier1_tier2.py` — offline test pipeline that loads pre-collected run-4.json (tier-1) and run-5.json (tier-2), applies full filter stack + scoring + planning, skips LLM to inspect funnel
- Enhanced `clients/Joinee.yaml` keywords: added NOT-block queries to stay under LinkedIn 300-char limit, refined tier1/tier2/tier3 keywords
- Updated `config.yaml` with semantic filter thresholds (min_semantic_similarity: 0.25, blocked_substrings)
- Added `sentence-transformers>=2.7.0` to requirements.txt
- Model download ~80 MB on first run, cached thereafter
- Filter funnel results: 1290 raw → 586 tier-1 + 704 tier-2 normalised → 342 survived semantic → 220 survived full filter → 30 comment actions planned
- Session had to be restored mid-way due to Cline window freeze; script ran successfully on restoration

Next session: Integrate semantic filter + post scorer into main `run_pipeline.py` pipeline, or proceed to Phase 3 (dashboard integration).

### 2026-06-17 01:13
Phase: 2 | Step: CLINE.md — Add Session Resumption Protocol + Pre-Tool-Call Verification Gate + Recovery After Interruption
Status: DONE
Files changed: CLINE.md, progress.md
Test result: N/A
Notes:
- Added **Section 2.5 — Session Resumption Protocol**: mandatory [RESTORE] output on window reload, prohibits re-executing logged steps, cross-references progress.md + git log to confirm state
- Strengthened **Section 3 — Status Reporting**: added enforced gate — progress.md update must be the very next tool call after every [DONE], no exceptions
- Added **Section 8.5 — Pre-Tool-Call Verification Gate**: before every file-touching tool call, pause and verify progress.md is current; abort and update if stale
- Added **Section 8.6 — Recovery After Interruption**: environment reset detection with [RECOVERY] output, git log cross-reference, skip-forward rule
- Renumbered Sections 9→10, 10→11, 11→12; fixed all internal cross-references to match
- All changes enforce the rule: **progress.md must be updated before any subsequent tool call, and checked before any file operation** — closing the deferral loophole that caused lost entries in previous sessions
- This entry is itself a demonstration of the rule: written before the session summary, matching the last action taken

Next session: Integrate semantic filter + post scorer into main `run_pipeline.py` pipeline, or proceed to Phase 3 (dashboard integration).
