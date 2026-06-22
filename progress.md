# VVLeng Progress Log

## 2026-06-22 (SESSION END — docs + commit)
Phase: 3/4 | Step: Wrap-up — runbook doc, gitignore hardening, commit+push
Status: DONE
Files changed: docs/pipeline_runbook.md (NEW — current implemented pipeline, run commands, outputs, two-level ranking,
  open items), .gitignore (added data/, *.bak, *.log — protects the Apify token leaked into scratch/collect_run log)
Test result: N/A (docs/infra)
Notes: Session shipped: Apify relevance+50/kw; tier-tag bug fix; recruiting/announcement noise filter; batched semantic
  filter + semantic_score reuse; LLM relevance gate (on by default) + 50/50 blended ranking; comment prompt (hook/value/
  closer, no fabricated stats); LLM comment judge (best-first + confidence + safe_autopost); comment_sheet + self-contained
  comment_runner UI (feedback export); topic_ideas generator; kgraph demand-graph note. Committed to master. Today's
  deliverable = data/Joinee/output/comment_runner_2026-06-22.html (gitignored — regenerate via build_comment_ui.py).
  NOT committed: data/ (generated), scratch logs (token), *.bak. Next session: feedback loop → carry-over pool.

## 2026-06-22 (session, comment ranking — best-first + confidence)
Phase: 3/4 | Step: LLM judge ranks the 3 comment variants best-first with confidence; UI surfaces top pick
Status: DONE
Files changed: content/prompts/comment_rank_system.txt + comment_rank_user.txt (NEW judge prompt),
  content/comment_gen.py (rank_comment_variants() LLM judge; generate_comments(rank=True) reorders best-first +
  annotates top with confidence/top_reason/safe_to_autopost), run_pipeline.py write_comment_sheet (added
  top_confidence/top_reason/safe_autopost cols; comment_1 = top pick), scratch/rank_today.py (NEW, re-ranked today's 30),
  data/Joinee/output/comment_sheet_2026-06-22.csv (rewritten best-first + confidence),
  scratch/build_comment_ui.py + comment_runner_2026-06-22.html (top pick prominent + confidence badge + collapsible
  "show alternatives")
Test result: PASS — re-ranked 30: confidence 5 on 22 posts, 4 on 8, all safe=True. Judge usually picked the question-led
  variant (reply-driving). UI verified: posts in rank order 1..30, comment_1=top pick, alternatives collapsed.
Notes: BOTH levels now ranked best-first — posts by blended rank_score (gate×heuristic), comments by LLM judge.
  Assistant workflow: go top-down, grab comment_1, take top 15-20 posts; confidence (+safe_autopost) is the lever for
  eventual 99% auto-post (post conf=5 blindly, route lower to a human). Future runs get this automatically via
  generate_comments(rank=True).

## 2026-06-22 (session, topic ideation + comment runner UI)
Phase: 3/4 | Step: Quick content-topic generator + self-contained comment-runner UI + feedback capture
Status: DONE
Files changed: scratch/topic_ideas.py (NEW — engagement-rank corpus + 1 LLM ideation pass → 5 post topics),
  data/Joinee/output/topic_ideas_2026-06-22.json (5 topics w/ hook+angle, incl. "community ROI" whitespace play),
  scratch/build_comment_ui.py (NEW — generates self-contained HTML comment runner from comment sheet),
  data/Joinee/output/comment_runner_2026-06-22.html (NEW — 30 posts, copy buttons, mark done/skip, export feedback CSV),
  kgraph/docs/demand-graph-approach.md (NEW — captured demand-graph design for the parallel kgraph project)
Test result: PASS — topic_ideas produced 5 grounded topics (no fabricated stats); comment_runner embeds 30 posts,
  valid URLs, 3 comments each; export + copy JS present (execCommand copy works on file://, localStorage persists).
Notes: Operator workflow today = open comment_runner_2026-06-22.html → open post → copy variant (auto-marks used) →
  Done/Skip → Export feedback CSV (commented_log_2026-06-22.csv: rank,status,variant_used,used_text,url,author,ts).
  That CSV is the durable feedback artifact for the future carry-over/pool (operator-feedback prerequisite). Regenerate
  UI anytime: python scratch/build_comment_ui.py. kgraph note links back to VVLeng reuse (corpus, relevance_gate,
  semantic_filter embeddings, build_niche_prompt_context).

## 2026-06-22 (session, ban invented stats + regen sheet)
Phase: 3/4 | Step: Tighten comment prompt to ban fabricated stats; regenerate today's 30 comments
Status: DONE
Files changed: content/prompts/comment_system.txt (NEVER fabricate facts rule; redirect specificity to distinctions/
  mechanisms/hedged first-person anecdotes; Value step allows only real/verifiable numbers),
  data/Joinee/output/comment_sheet_2026-06-22.csv (regenerated in place, 30 rows), scratch/regen_comments.py (NEW)
Test result: PASS — regenerated 30 comments (no Apify, no semantic/gate rerun). Scan of 90 comments: 0 fabricated stats.
  The 5 numeric mentions are all legitimate: #8 echoes author's own "84/88 percent gross retention" (verified in post text),
  #18 cites the real 90-9-1 / 1-9-90 community rule. flagged_any = 0.
Notes: Deliverable comment_sheet_2026-06-22.csv is now safe-to-paste. plans/2026-06-22_plan.json still holds the OLD
  (pre-tighten) comments — operator works from the sheet, not the plan; tomorrow's E2E run regenerates everything
  consistently. Comment quality preserved (hook/value/closer + question closers, non-promotional).

## 2026-06-22 (session, clean finish run + comment sheet)
Phase: 3/4 | Step: Full remaining pipeline on saved posts (no Apify) → comment sheet for manual placement
Status: DONE
Files changed: run_pipeline.py (write_comment_sheet() — ranked targets + url + comment variants; stash rank_score/
  heuristic on post dicts; call after content gen), data/Joinee/output/comment_sheet_2026-06-22.csv (NEW, 30 rows),
  data/Joinee/output/shortlist_2026-06-22.csv (regenerated, gated+blended, 136 targets), data/Joinee/plans/2026-06-22_plan.json
Test result: PASS — `python run_pipeline.py --client Joinee --skip-collect` (gate ON, comments ON, no Apify).
  Funnel: 2301 reload → semantic 498 → content filters 241 → gate kept 136/241 → top 30 → 90 comment variants (3 flagged).
  Blend visible: Patience (CS/churn, gate 1.0, heur rank ~10) promoted to #1; Victor (heur 0.91) → #2.
Notes: Comment quality strong (hook/value/closer, non-promotional, question closers). CAVEAT: comments fabricate
  specific stats ("teams lose 30%", "3x better chance") — operator must own/verify any numbers, or tighten prompt to
  avoid invented hard data. Deliverable for manual placement = comment_sheet_2026-06-22.csv. Daily-pool/carry-over idea
  discussed (persistent post pool, ~72h comment-eligibility window, decouple collection cadence from commenting cadence,
  needs operator feedback loop) — not yet built; JSON-pool MVP proposed.

## 2026-06-22 (session, gate blend + on-by-default)
Phase: 3/4 | Step: Blend gate into ranking; gate on by default
Status: DONE
Files changed: run_pipeline.py (--no-relevance-gate replaces --relevance-gate; use_gate on by default, suppressed by
  --skip-llm; rank_score = 0.5*heuristic + 0.5*gate; gate-keep promotes below-threshold avoids to comment_target;
  print_ranked_shortlist + write_shortlist_csv sort by rank_score and show gate cols),
  processor/post_scorer.py (PostScore.rank_score field, defaulted to composite)
Test result: PASS — compile OK; blend reorders (stale high-ICP post overtakes fresh low-ICP); gate-kept below-threshold
  post promoted to comment_target (was vetoed by min_comment_target_score before fix).
Notes: Interaction bug caught + fixed: heuristic min_comment_target_score (0.45) was vetoing gate-approved posts to
  "avoid". Now when gate ran, a "below comment threshold" avoid is promoted to comment_target; mechanical/noise avoids
  (>100 comments, recruiting, empty) are left intact. CSV columns now: rank, rank_score, heuristic_score, gate_score,
  gate_reason, sub-scores, tier, semantic, author, url, text. Gate runs on full survivors (~242 → ~16 batches) on a real
  default run; not yet executed end-to-end live (logic verified via unit tests). Next optional: full default run to
  regenerate gated+blended shortlist and generate comments with new prompt.

## 2026-06-22 (session, LLM relevance gate + calibration)
Phase: 3/4 | Step: Build LLM relevance gate, integrate (opt-in), calibrate against today's 30
Status: DONE
Files changed: content/prompts/relevance_gate_system.txt + relevance_gate_user.txt (NEW; inject niche_prompt_context),
  processor/relevance_gate.py (NEW — batched LLM keep/score over survivors, fail-open, robust JSON parse),
  run_pipeline.py (--relevance-gate flag; gate step between content filters and scoring),
  scratch/calibrate_gate.py (NEW calibration harness)
Test result: PASS — compile OK; gate ran on 30 heuristic targets via scoring_model gpt-4.1-mini, all 30 parsed (0 fallbacks).
Notes: Calibration kept 19/30, dropped 11 — all 11 genuine residual noise (founder-retrospective "five years old today",
  LinkedIn-growth humblebrag, off-ICP career/recognition posts, promo broadcasts). Gate also RE-RANKS by ICP: Khaled Azar
  "B2B SaaS retention + community ROI" was heuristic #29 (0.47) but gate top (0.93); #2 heuristic top (0.91) → gate 0.40.
  keep rule icp_fit>=3 AND commentability>=3 separates cleanly (kept 0.60-0.93, dropped 0.20-0.47). Prompt judged done,
  no fix needed. Reuses build_niche_prompt_context() (was the unused Phase-1 function). OPEN: gate is keep/drop only —
  ranking still heuristic, so high-ICP posts survive but don't rise. Next: blend 0.5*heuristic + 0.5*gate into rank score.

## 2026-06-22 (session, run + quality fixes)
Phase: 0/3 | Step: Live collection run + tier-tag bug fix + recruiting/announcement noise filter + shortlist export
Status: DONE
Files changed: run_pipeline.py (tag_posts_by_keyword_tier now tags by source_query not broken text-match;
  skip-collect reload picks newest posts*.json by mtime; write_shortlist_csv() export to output/),
  processor/post_scorer.py (_RECRUITING_PATTERNS + _ANNOUNCEMENT_PATTERNS replace _CELEBRATORY; _noise_reason()),
  data/Joinee/raw/posts_20260622T180303Z.json (2301 raw posts collected), data/Joinee/output/shortlist_2026-06-22.csv
Test result: PASS
Notes: Live Apify run (harvestapi, sortBy=relevance, 50/kw, 48 kw, 1-week) → 2301 raw posts, run_id 4E0vwifaDW2HxSczm.
  BUG FOUND+FIXED: tag_posts_by_keyword_tier skipped every keyword containing " NOT " → ALL posts were tier2 (0 tier1).
  Now tags by source_query: 1000 tier1 / 1301 tier2. BUG2: shortlist was full of job ads + hire announcements (semantic
  filter can't tell "hiring a community manager" from "how to engage your community"). Added recruiting/announcement
  regex avoid-classifier. Funnel after fixes: 2301 → semantic 498 → engagement 298 → dedup 242 → 30 comment_targets.
  Top shortlist now genuine thought-leadership (community/founder/CS/churn), job-ad noise removed. Reprocess was free
  (--skip-collect --skip-llm, no API cost). NOTE: Apify token leaked into scratch/collect_run_2026-06-22.log via httpx
  URL logging — scratch/ is untracked; confirm gitignored before any commit.

## 2026-06-22 (session)
Phase: 0/1 | Step: Doc fixes + prompt/algorithm rigour + Apify relevance/50 config
Status: DONE
Files changed: CLINE.md (stale base-doc filename → VVLeng_architecture.md; active client joinee → Joinee),
  content/prompts/comment_system.txt + comment_user.txt (rewritten: voice/no-pitch/hook-value-closer, === delimiter),
  content/comment_gen.py (=== variant parsing, multi-line variants, max len 280→700, expanded blocklist),
  processor/semantic_filter.py (new evaluate_posts() batched encode + score reuse),
  run_pipeline.py (use batched evaluate_posts, attach semantic_score to kept posts),
  processor/post_scorer.py (relevance = tier×0.5 + semantic×0.5; min_comment_target_score gate),
  config_loader.py (ClientScoringConfig.min_comment_target_score; fix max_posts_per_keyword to honour collection.posts_per_keyword),
  config.yaml (defaults max_posts_per_keyword 30→50),
  clients/Joinee.yaml (collection.posts_per_keyword 50, scoring.min_comment_target_score 0.45),
  collector/apify_client.py (harvestapi sortBy date→relevance)
Test result: PASS — compile OK; load_config resolves 48 kw / 50 per kw / threshold 0.45; actor input sortBy=relevance maxPosts=50;
  score_post: fresh+relevant+engaged → comment_target (1.0); stale/weak → avoid (below threshold); === parser splits variants.
Notes: Audit finding — celebratory/blocked filters catch "graduation"/"graduated"/"after N years" which overlap Joinee's
  alumni vocabulary (false negatives possible). Flagged to user, not changed. Real Apify collection run (48 kw × 50 ≈ 2400 posts)
  exceeds config daily_apify_budget_usd 3.00 — awaiting user confirmation before spending.

## 2026-06-17 02:30
Phase: 0 | Step: CLINE.md — add Zero-Tolerance Enforcement for progress.md (8.7) + Read-Back (8.8) + fix Windows `tail` commands
Status: DONE
Files changed: CLINE.md (added sections 8.7, 8.8, replaced tail with python -c in verification + Section 12 Step A)
Test result: N/A
Notes: Section 8.7 adds: no tool call without checkpoint, 3-call budget, 2-min silence rule, session anchor on progress.md, violation consequences. Section 8.8 adds mandatory read-back after every progress.md write. All `tail -5` commands replaced with Windows-compatible python -c.

## 2026-06-17 02:22
Phase: 0 | Step: Pipeline Integration — scratch logic into run_pipeline.py
Status: DONE
Files changed: run_pipeline.py (rewritten with 5 new functions + restructured flow), progress.md (this entry)
Test result: PASS
Notes: Full end-to-end run verified with 1290 scratch posts. Filter funnel: 1290 → semantic (156 kept) → content filters (43 kept) → 39 comment targets. Dry-run exits clean. 

## 2026-06-17 02:16
Phase: 0 | Step: UTF-8 encoding fix for reloaded posts.json
Status: DONE
Files changed: run_pipeline.py (added encoding="utf-8" to json.load)
Test result: PASS
Notes: UnicodeDecodeError resolved when reading saved posts.json written with ensure_ascii=False.

## 2026-06-17 01:?? 
Phase: 0 | Step: Rewrite run_pipeline.py with scratch pipeline logic
Status: DONE
Files changed: run_pipeline.py
Test result: PASS
Notes: Added tag_posts_by_keyword_tier, apply_semantic_filter, apply_content_filters, print_filter_funnel, print_ranked_shortlist. Fixed numpy import scope. Fixed %d format string.