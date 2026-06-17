# VVLeng Progress Log

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