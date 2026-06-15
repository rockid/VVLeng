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
| `content/llm_client.py` | ✅ Done | Accepts `config` param for model/api_key/base_url |
| `content/comment_gen.py` | ✅ Done | Accepts `config` param, passes through to LLM |
| `content/prompts/` | ⬜ Done (pre-existing) | |
| `planner/daily_plan.py` | ✅ Done | Accepts `config` param for limits/niche |
| `planner/output.py` | ⬜ Done (pre-existing) | |
| `db/session.py` | ✅ Done | Accepts `config` param for DB URL |
| `db/models.py` | ⬜ Done (pre-existing) | |
| `.env` | ✅ Done | Secrets-only |
| `.env.example` | ✅ Done | Secrets-only template |
| `requirements.txt` | ⬜ Done (pre-existing) | |

## Next Milestones

- [ ] **Phase 1**: Acceptance test (`python run_pipeline.py --dry-run`)
- [ ] **Phase 2**: Dashboard integration + Redis state
- [ ] **Phase 3**: LinkedIn action executor (manual-in-browser mode)
- [ ] **Phase 4**: CI/CD, monitoring, multi-client orchestration

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
