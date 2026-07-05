# VVLeng Progress Log

## 2026-07-05 02:25
Phase: run-sequence | Step: Full execution report written (operator request)
Status: DONE
Files changed: docs/run_sequence_report_2026-07-05.md (NEW — per-phase results,
  findings, commit map, cost accounting, 7 consolidated follow-ups)
Test result: N/A (docs only)
Notes: Report covers Phases 0-5 complete, 6 pending sample review, 7 operator-
  only. Still at the Phase 5 sample-review ⛔ STOP (see 02:05 entry).

## 2026-07-05 02:05
Phase: run-sequence | Step: Regen attempt 3 SUCCESS + top-10 sample delivered — at Phase 5 sample-review ⛔ STOP
Status: DONE (regen + sample) / BLOCKED (operator reviews sample outside CC)
Files changed: committed a8047d4 (run_pipeline.py warm_up_network_stack;
  clients/Joinee.yaml posts_per_keyword 35). Uncommitted TEMP: config.yaml
  max_post_age_days=14 (operator instruction: for today's live run only,
  revert to 7 after). Generated: data/Joinee/output/comment_sheet_2026-07-05.csv
  + shortlist_2026-07-05.csv (regenerable), scratch/sample_top10_2026-07-05.txt
Test result: PASS — regen exit 0 with warm-up fix (proves fix under real load).
  Funnel on saved 06-22 corpus @21d age: 2301 → 498 semantic → 243 filters →
  gate: 107 comment_target / 25 avoid → top-30 sheet, 3 variants each.
  Sample quality scan: register-matched, no bait questions, en-dashes only,
  confidence 4-5, all safe=True.
Notes: Judge 'reason' strings cite pre-reorder variant labels (e.g. "Comment 2
  ..." while columns are already best-first) — cosmetic, noted as follow-up.
  LLM cost: ~2 wasted gate batches (attempts 1-2) + full gate (17 batches) +
  30×2 gen/rank calls ≈ cents on gpt-4.1-mini. Next: operator reviews
  scratch/sample_top10_2026-07-05.txt in Claude chat; on approval (+ possible
  prompt tweaks) → Phase 6 live run (Apify+LLM, maxPosts=35, age=14).

## 2026-07-05 01:40
Phase: run-sequence | Step: regen crash root-caused — torch-vs-Winsock DLL conflict; warm-up fix added
Status: DONE (diagnosis + fix) / IN PROGRESS (regen attempt 3)
Files changed: run_pipeline.py (warm_up_network_stack() — one throwaway HTTPS
  request before torch loads, skipped in --dry-run; called in main() after
  config load), scratch/dns_probe_20260705.py + net_after_encode_20260705.py
Test result: Deterministic repro established (free): FIRST httpx call AFTER
  sentence-transformers encode → access violation in socket.getaddrinfo
  (exit 0xC0000005) every time; one httpx call BEFORE torch loads → all
  later httpx AND requests calls succeed in that process. Bare getaddrinfo
  and torch-import-only combos pass — the trigger is full model load +
  OpenMP threads before first TLS connection.
Notes: Regen attempts 1+2 both died at the FIRST gate LLM call (≤1 batch
  billed each, ~cents total). Side observation: a survived first-chance AV
  also fires inside pyarrow DLL init (lazy pandas import via
  transformers.generation→sklearn chain) — machine has a fragile native-DLL
  landscape (likely AV/VPN Winsock LSP); operator-level fix (winsock reset /
  AV check) still recommended but no longer blocking. Next: regen attempt 3
  with warm-up in place → top-10 sample → revert config.yaml age temp.

## 2026-07-05 01:00
Phase: run-sequence | Step: .venv fixed + Phase 5.1/5.2 PASS — at paid-regen ⛔ STOP
Status: DONE (verification ladder, free part) / BLOCKED (operator go-ahead for paid regen)
Files changed: clients/Joinee.yaml (posts_per_keyword 50→35 per Phase 4 decision,
  uncommitted), scratch/diag_load_20260705.py + smoke_20260705.txt (untracked)
Test result: PASS — full --dry-run exit 0 (collect→plan, mock Apify+LLM);
  smoke --skip-collect --skip-llm exit 0; pytest 29/29 in .venv;
  isolated dry-run comment-gen check: 3 mock variants, ranking fails open, no crash.
Notes: ENV SAGA RESOLVED: .venv created (system py3.12, torch 2.12.1+cpu,
  transformers 4.49.0 + sentence-transformers 3.4.1 pinned, safetensors 0.4.5,
  hf-xet uninstalled). ROOT CAUSE of exit-5 crashes was NOT torch/safetensors:
  faulthandler showed access violation inside socket.getaddrinfo — machine-level
  Winsock/DNS instability (same cause as pip DNS failures + AV file lock).
  WORKAROUND: HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 for all pipeline runs
  (MiniLM fully cached). ⚠ RISK: live Apify/LLM calls use getaddrinfo too — a
  live run may crash mid-collection until the operator fixes Winsock/VPN/AV.
  FINDINGS: (1) --dry-run does NOT exercise comment gen — semantic filter drops
  all 96 mock posts (mock text is off-niche by construction); covered instead by
  unit tests + isolated mock-LLM check; follow-up: make some mock posts pass the
  filter. (2) Saved 06-22 posts are now ALL >7d old → age filter removes 100%,
  so a --skip-collect regen today yields 0 targets without a temporary
  max_post_age_days raise. Deleted 2 new mock raw files post-dry-run.
  Next: operator decides regen approach (temp age raise vs fold review into
  Phase 6 live run).

## 2026-07-05 00:20
Phase: run-sequence | Step: Phase 3 approved; .venv build started; Phase 4 top-N analysis done — at Phase 4 ⛔ STOP
Status: DONE (analysis) / BLOCKED (operator picks maxPosts)
Files changed: scratch/topn_analysis_20260704.py + topn_report_2026-07-04.txt
  (untracked scratch); .venv/ being created in background (gitignored)
Test result: N/A (analysis). Position recoverable: yes — raw items ordered per
  query (47 queries, 24-50 posts each); query.search parsed for base keyword.
Notes: Operator approved Phase 3 pattern set as committed (0f2be25) and chose
  dedicated .venv (system py3.12 + CPU torch + requirements.txt, background
  job b67s8ulxm). RESULTS: gate-kept shortlist 119/119 matched — 66% at pos
  ≤25, 76% at pos ≤30; top-30 sheet: 67% ≤25, 73% ≤30. Decision rule band
  70-85% → recommend maxPosts 50→35. Per-keyword: top yielders 5-8 kept/50
  fetched. Caveat: per-tier split shows "unknown" (query strings didn't match
  current clients/Joinee.yaml keyword lists — cosmetic, overall numbers
  unaffected). Side-finding: collection queries already embed NOT hiring/"new
  role"/"new chapter"/thrilled clauses. Next: operator picks 50/35/30 →
  Phase 5 verification ladder once .venv ready.

## 2026-07-04 13:50
Phase: run-sequence | Step: Phase 3 validated + committed — at Phase 3 ⛔ STOP
Status: DONE (classifier + validation) / BLOCKED (operator approval + env decision)
Files changed: processor/post_scorer.py + tests/test_noise_classifier.py
  (committed as 0f2be25 on feat/prompt-rewrite), scratch/
  validate_career_filter_20260704.py + nc_context_20260704.py + report (untracked)
Test result: PASS — pytest 29/29. Validation on saved 2301-post corpus:
  33 newly excluded (29 career-transition, 4 HR-dominant), 4 in gated
  shortlist incl. 1 top-30, all judged defensible catches.
Notes: Mid-validation adjustment: bare "next chapter" fired on figurative
  business uses (28 posts, incl. ICP-relevant Dr. Mansi Shah shortlist post =
  true false positive) — replaced with verb-anchored pattern (begin/start/
  embark on/on to/time for/into + next chapter): 33 vs 55 exclusions, Shah
  released. Also widened recruiting "remote job"→"remote (job|role)" (leaked
  CPO job ad found in validation). Deleted mock artifact
  data/Joinee/raw/posts_20260624T090427Z.json (verified [DRY_RUN MOCK]
  content first) so --skip-collect picks the real 06-22 dataset.
  ENV BLOCKER (pre-existing, NOT caused by today's changes): pipeline smoke
  run fails at sentence_transformers import — shell runs the "borus" poetry
  venv (VIRTUAL_ENV set) which has transformers 4.57.6 vs
  sentence-transformers 3.4.1 (incompatible after a borus-side upgrade in
  the last 10 days); system Python 3.12 has no ML deps at all; repo has no
  own venv. Pattern-level validation + pytest unaffected (no ML imports).
  Options for operator at STOP: (a) create dedicated .venv for VVLeng
  (recommended, isolates from borus, ~1-2GB torch download), (b) upgrade
  sentence-transformers inside borus venv (touches another project's env).
  Phase 4+ blocked on this + Phase 3 approval.

## 2026-07-04 13:05
Phase: run-sequence | Step: Phase 0 completed + Phase 3 classifier built
Status: DONE (code) / IN PROGRESS (validation)
Files changed: processor/post_scorer.py (_CAREER_TRANSITION_PATTERNS +
  _HR_TOPIC_PATTERNS w/ 2-hit rule; _noise_reason() extended — new avoid reasons
  "career transition / job seeking" and "HR-topic dominant"),
  tests/test_noise_classifier.py (NEW, 5 tests)
Test result: PASS — pytest 27/27 (one test initially asserted wrong label:
  post with "hiring managers" is caught by the OLDER recruiting pattern first;
  test rewritten to a pure-HR post; behavior itself was correct)
Notes: PR #2 squash-merged to master (d162009) after operator's explicit
  direction; feat/prompt-rewrite rebased onto master via
  `rebase --onto origin/master infra/add-dry-run-mode` — now master + 3b2dc57
  (prompt rewrite commit), stash pop clean, operator's pre-existing changes
  intact. Prompt diffs APPROVED by operator at Phase 2 STOP. Deliberately NOT
  duplicated in new patterns: "open to work", "new chapter", "excited/thrilled
  to announce" — already caught by _ANNOUNCEMENT_PATTERNS. Next: validation
  script over saved posts_20260622T180303Z.json + exclusion report → Phase 3
  ⛔ STOP.

## 2026-07-04 12:35
Phase: run-sequence | Step: Phase 1 done + Phase 2 verified — committed, at first ⛔ STOP
Status: DONE (Phases 1-2) / BLOCKED (awaiting operator: PR #2 merge + prompt-diff approval)
Files changed: content/comment_gen.py (.format→.replace fix for {n_variants} crash;
  POST_TEXT_WINDOW=1800 replaces 500/600 truncations for writer+judge; _strip_em_dashes()
  applied to every variant), tests/test_comment_gen.py (NEW, 6 tests), plus operator's
  own prompt rewrite committed (comment_system/user/rank_system/relevance_gate .txt)
Test result: PASS — pytest 22/22 (16 existing + 6 new)
Notes: Committed as one feat(content) commit on feat/prompt-rewrite. Phase 2 needed
  NO edits — operator's comment_rank_system.txt rewrite already met every requirement
  (bait-question penalty, register match, length fit, JSON format unchanged). Found
  untracked content/prompts/comment_system-bak.txt (operator backup; *-bak.txt is NOT
  gitignored — flagged for cleanup, not committed). Now at Phase 2 ⛔ STOP: prompt
  diffs presented to operator. Waiting on: (1) operator merges PR #2 (gh pr merge 2
  --squash) — then rebase feat/prompt-rewrite via `git rebase --onto master
  infra/add-dry-run-mode feat/prompt-rewrite`; (2) operator approves prompt diffs →
  proceed to Phase 3 (career-change/HR noise classifier).

## 2026-07-04 12:05
Phase: run-sequence (docs/CC_RUN_SEQUENCE_2026-07-04.md) | Step: Phase 0 (partial) + Phase 1 started
Status: BLOCKED (Phase 0 merge) / IN PROGRESS (Phase 1)
Files changed: none yet (branch ops + reads only)
Test result: N/A
Notes: Phase 0: pushed infra/add-dry-run-mode, opened PR #2
  (github.com/rockid/VVLeng/pull/2). Squash-merge DENIED by CC permission
  classifier (auto-merging own PR to master bypasses review checkpoint) —
  operator must merge: `gh pr merge 2 --squash`. To keep moving, created
  feat/prompt-rewrite FROM infra/add-dry-run-mode (carries operator's
  uncommitted prompt rewrite); will `git rebase --onto master
  infra/add-dry-run-mode feat/prompt-rewrite` after PR #2 merges.
  Phase 1 findings: <examples> block confirmed fully removed from
  comment_system.txt; comment_user.txt placeholders all covered by existing
  format() kwargs; comment_rank_system.txt working-tree version ALREADY
  satisfies all Phase 2 requirements (bait-question penalty, register match,
  length fit, output format unchanged) — Phase 2 becomes verification-only.
  Remaining Phase 1 edits: comment_gen.py .format→.replace fix, truncation
  500/600→1800, em-dash strip + unit test.

## 2026-07-04 11:30
Phase: re-orientation | Step: Build strategy pack for Claude-chat plan-revision discussion
Status: DONE
Files changed: docs/strategy_pack_2026-07-04.md (NEW — self-contained: built-vs-planned
  state, distillation of all 3 planning docs, run evidence, cost model, decision agenda,
  operator questions)
Test result: N/A (docs only)
Notes: Read all three planning docs to distill: VVLeng_architecture.md (v1.0),
  VVLeng_architecture_amendment_combined.md (2026-06-13, phases 0-5), and
  architecture_amendment_phase2_people.md (2026-06-14/15, "APPROVED", Phase 1.5
  waterfall + Phase 2 people pipeline — NEWER than the combined amendment and
  entirely unbuilt; only its sortBy=relevance fix landed). Key framing surfaced
  for the strategy chat: three overlapping plans coexist while the actually-built
  path (relevance gate, blended ranking, comment judge, comment runner, carry-over
  pool idea) appears in none of them — plan revision = pick one spine + reconcile.
  Also confirmed data/Joinee/output contains NO commented_log_*.csv — zero field
  results exist; flagged as the biggest evidence gap (pack §F asks the operator).
  Pack deliberately left §F unanswered for the operator to fill before the chat.
  Next session should start at: whatever the strategy chat decides; mechanical
  next steps unchanged (push/PR TASK-1 branch, then prompt-rewrite branch with
  {n_variants} fix — see 10:45 entry and project_status_2026-07-04.md).

## 2026-07-04 10:45
Phase: re-orientation | Step: Project status review after ~10-day pause; produce status doc for Claude chat discussion
Status: DONE
Files changed: docs/project_status_2026-07-04.md (NEW — self-contained status snapshot: pipeline state, two in-flight threads, next steps)
Test result: N/A (read-only review; no code changed, smoke test not re-run)
Notes: Two threads in flight: (A) infra/add-dry-run-mode — TASK-1 done, committed,
  still not pushed/PR'd; (B) uncommitted prompt rewrite in content/prompts/*
  (owner's own work, 07-03/07-04) + docs/CC_INSTRUCTIONS.md menu of supporting code
  changes. BUG FOUND during review: revised comment_system.txt contains a literal
  {n_variants} placeholder but comment_gen.py:109 renders it via .format(niche=niche)
  → KeyError on any comment-gen run. The rewrite is NOT drop-in despite
  CC_INSTRUCTIONS.md's claim; fix is a one-liner (use .replace like the ranker path,
  or pass n_variants). Not fixed this session — review only, per user request.
  Next session should start at: decide merge order (recommend: push+PR TASK-1 first,
  then feat/content branch for prompt rewrite + n_variants fix + CC_INSTRUCTIONS
  items 1-2), per docs/project_status_2026-07-04.md §5.

## 2026-06-24 12:10 (SESSION END)
Phase: infra | Step: TASK-1 close-out — commit, secrets check, final smoke re-run
Status: DONE
Files changed: none this entry (commit/verification only — see 11:45 entry for the
  actual diff)
Test result: PASS — re-ran `--skip-collect --skip-llm` smoke test against the final
  committed tree (exit 0; log line confirmed `dry_run=False, no_persist=False`,
  reloaded 96 posts, tagged 40 tier-1/56 tier-2, ran clean through semantic filter).
  pytest tests/ 16/16 passed (run pre-commit, in the 11:45 entry).
Notes: Committed TASK-1 as 4 logical commits on infra/add-dry-run-mode (user chose
  this granularity via AskUserQuestion): 1b70f57 docs(tasks) decision record,
  9b85767 feat(pipeline) code, 3507e3d docs(cline) doc updates, aa7bd8c
  docs(progress) log. Secrets check: `git diff` across all 4 commits scanned for
  key/token/secret patterns — only doc-text mentions of "API key" as a heading/
  variable name, no actual credentials; `.env` never staged/touched in any commit.
  Confirmed master untouched (`git merge-base --is-ancestor` → not merged, as
  expected — work stayed on the feature branch). Cleaned up a second stray
  verification-output file (smoke_test_close.txt) before leaving the tree clean.
  User's own pre-existing unrelated changes (deleted
  docs/session_handoff_2026-06-14_updated.md, modified
  scratch/tier1_tier2_output_2026-06-17.txt, untracked scratch/*.py/*.json,
  docs/Ideas.md, docs/linkedin_post_architecture_v1.md) confirmed still untouched/
  unstaged — final git status matches session-start status exactly for these files.
  Branch NOT pushed, no PR opened (both deferred — pushing/opening a PR is a
  visible-to-others action; live Apify/LLM spot-check needs the user's cost
  go-ahead per TASK-1's own constraint). Session ends here cleanly: nothing
  uncommitted that was intentionally changed this session, smoke test passes,
  docs are honest, .clinerules/00-project-overview.md status table is current
  (no further staleness found this session beyond what TASK-1 itself fixed).
  Next session should start at: push infra/add-dry-run-mode + open PR (or do the
  live spot-check first, if the user wants that before opening the PR).

## 2026-06-24 11:45
Phase: infra | Step: Implement TASK-1 (dry-run/mock mode) on branch infra/add-dry-run-mode
Status: DONE
Files changed: config_loader.py (AppConfig.dry_run field + load_config(dry_run=) param),
  collector/apify_client.py (_mock_run_actor() — harvestapi-shaped fake posts, [DRY_RUN MOCK]
  marker; run_actor() checks config.dry_run first), content/llm_client.py (_mock_complete() —
  [DRY_RUN MOCK LLM] marker, 3 '==='-delimited variants so comment_gen still produces multiple
  variants; complete() checks config.dry_run first), run_pipeline.py (--dry-run help text
  rewritten, new --no-persist flag added, no_persist = args.no_persist or args.dry_run computed
  before config load, dry_run=args.dry_run passed into load_config(), all 3 persistence-gating
  sites switched from args.dry_run to no_persist; --skip-collect/--skip-llm/--no-relevance-gate
  untouched), docs updated in the same PR per acceptance criteria: .clinerules/00-project-overview.md
  (status table + "the one rule" section), .clinerules/01-session-start.md (§2 flag semantics),
  .clinerules/02-session-end.md (§1 smoke-test guidance), .clinerules/03-coding-standards.md
  (dry-run pattern section now points to the real reference implementation instead of saying
  none exists), .clinerules/05-secrets-and-safety.md (cost discipline section), docs/pipeline_runbook.md
  (new example command + Flags line), docs/VVLeng_instructions.md (CLI flags table + quick-rerun
  example changed from `--skip-collect --dry-run` to `--skip-collect --no-persist`, since under
  the new semantics --dry-run would also mock the LLM call).
Test result: PASS — all 4 verification runs exited 0, no exceptions:
  (1) smoke test `--skip-collect --skip-llm` unchanged/still passes (confirms skip-flag behavior
  untouched); (2) full `--dry-run` (no skip flags) ran collect→...→outputs end-to-end with zero
  API keys set, mock posts flowed through normalise_posts() correctly, plan printed to stdout
  only (no CSV/plan file written) — confirms --dry-run implies --no-persist; (3) `--no-persist`
  alone reproduced the old --dry-run behavior exactly (plan to stdout, no persistence) while
  config.dry_run stayed False (live-call code paths still reached, not exercised further to
  avoid cost); (4) isolated check that comment_gen.rank_comment_variants() fails open on the
  mock LLM's non-JSON string (expected "Comment ranking failed (Expecting value...)" warning,
  not a crash — by design). pytest tests/ not re-run this session (no test file references
  dry_run/--dry-run; existing tests unaffected by additive AppConfig field + new branch-at-top-
  of-function checks).
Notes: Acceptance criteria from .cline-tasks/TASK-1.md all met: full pipeline runs dry with zero
  keys; --no-persist alone == old --dry-run behavior; mock output has explicit unmistakable
  markers ([DRY_RUN MOCK], [DRY_RUN MOCK LLM], "_mock": true); live/real behavior unchanged when
  neither flag passed (mock check is a new early-return, real path below it is untouched);
  --skip-collect/--skip-llm/--no-relevance-gate behavior untouched (diff-reviewed). Cleaned up
  3 stray verification-run artifact files at repo root (smoke_test_out.txt, dry_run_out.txt,
  nopersist_out.txt) before commit — not part of the intended diff. One regenerable mock file
  landed under gitignored data/Joinee/raw/ — harmless, no action needed. User's own pre-existing
  unrelated in-progress changes (deleted docs/session_handoff_2026-06-14_updated.md, modified
  scratch/tier1_tier2_output_2026-06-17.txt, untracked scratch/*.py + docs/Ideas.md +
  docs/linkedin_post_architecture_v1.md) confirmed still untouched/unstaged via git status.
  Not yet done: live spot-check of real Apify/LLM call (deferred — requires user's explicit
  go-ahead since it costs money, per TASK-1 constraints); actual commit + PR (next step).

## 2026-06-24 10:30
Phase: infra | Step: Resolve TASK-1 naming decision (dry-run/mock flag)
Status: DONE
Files changed: .cline-tasks/TASK-1.md (locked in option (a) — repurpose --dry-run
  to umbrella convention: skip persistence + mock external calls; current
  persistence-only behavior moves to new --no-persist flag; updated acceptance
  criteria + implementation order accordingly), .cline-tasks/README.md (decision
  status updated from "open" to "resolved")
Test result: N/A (decision/doc only, no code changed yet)
Notes: User chose option (a) over (b) via AskUserQuestion — recommended because it
  matches every other umbrella project's --dry-run convention and closes the cost
  footgun where --dry-run today looks safe/free but still fires live Apify/LLM
  calls. This is a breaking rename of --dry-run's current meaning ("skip
  persistence only") — TASK-1 implementation must update every doc reference
  (00-project-overview.md, 01-session-start.md, 02-session-end.md,
  05-secrets-and-safety.md, docs/pipeline_runbook.md) in the same PR as the code.
  No code written yet — TASK-1 implementation itself is still open/unstarted.
  Branch suggestion in the task file: infra/add-dry-run-mode.

## 2026-06-24 09:58
Phase: infra | Step: org-framework adoption — fold CLINE.md into .clinerules/, smoke test, git-permissions change (separate request)
Status: DONE
Files changed: .clinerules/00-project-overview.md through 06-progress-log.md (NEW), CLAUDE.md (NEW, @imports clinerules),
  OWNER-ACTIONS.md (NEW), .cline-tasks/README.md + TASK-1.md (NEW — dry-run/mock gap tracked, not retrofitted),
  CLINE.md (deleted — content folded into .clinerules/, per user's explicit choice of "fold in, retire CLINE.md").
  Unrelated to this branch: ~/.claude/settings.json (global, separate from this repo) — added permissions.allow:
  ["Bash(git *)"] per explicit user request, scoped global+all-git-subcommands per user's AskUserQuestion answers.
Test result: PASS — `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python run_pipeline.py --client Joinee --skip-collect --skip-llm`
  exited cleanly (code 0). Reloaded 2301 posts, semantic filter 498 kept, content filters → 219 kept, plan written
  (0 actions — expected, skip_llm suppresses comment-gen so no comment_targets are promoted). No live Apify/LLM calls
  (flags confirmed skip_collect=True skip_llm=True); only network traffic was free HuggingFace model-cache HEAD requests
  for the local sentence-transformers MiniLM model.
Notes: Branch infra/adopt-org-framework. Working tree also has user's own pre-existing unrelated in-progress changes
  (deleted docs/session_handoff_2026-06-14_updated.md, modified scratch/tier1_tier2_output_2026-06-17.txt, several
  untracked scratch/*.py + docs/Ideas.md + docs/linkedin_post_architecture_v1.md) — left untouched, not staged, out of
  scope for this adoption task. Next: stage+commit only the adoption files (.clinerules/*, CLAUDE.md, OWNER-ACTIONS.md,
  .cline-tasks/*, CLINE.md deletion) as one conventional commit, update _org-framework/ADOPTION.md's per-project ledger
  with a VV_Leng entry.

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
## 2026-07-05 (pre-Phase-6 prompt tweak)
Phase: 5.5 (operator feedback) | Step: writer+judge prompt micro-edits
Status: DONE
Files changed: content/prompts/comment_system.txt, content/prompts/comment_rank_system.txt
Test result: N/A (prompt-text only; operator waived re-verification)
Notes: (1) Writer blocklist: contrast-construction family banned as pattern (X isn't A it's B / not just X / X, not Y) - max one per comment, never as closing line. (2) Judge length-fit: equal variants -> shorter wins; 10-20 word sharp observation beats compressed essay unless post register is analytical. Awaiting possible 2nd fix from operator before Phase 6.

## 2026-07-05 (Phase 6 start)
Phase: 6 | Step: commit prompt edits + launch live run
Status: DONE (commit) / IN PROGRESS (live run)
Files changed: content/prompts/comment_system.txt, content/prompts/comment_rank_system.txt (commit e2ee1ce)
Test result: N/A
Notes: Operator gave explicit go-ahead for the Phase 6 live run (Apify + LLM, client Joinee, posts_per_keyword=35, max_post_age_days=14 temp). Launching full pipeline, log -> scratch/live_run_20260705.log. REMINDER after run: revert config.yaml max_post_age_days to 7; record Apify cost in docs/run_costs.md.

## 2026-07-05 (during Phase 6 run)
Phase: 6 | Step: token-leak hardening (operator request)
Status: DONE
Files changed: collector/apify_client.py
Test result: PASS (pytest 29/29; live Bearer-auth check vs /users/me -> 200)
Notes: Apify token moved from ?token= query param to Authorization: Bearer header at all 3 call sites (start/poll/dataset) - httpx logs full URLs at INFO, so the param leaked the token into run logs (e.g. scratch/live_run_20260705.log). .gitignore already covers *.log (no change needed). Running live pipeline unaffected (module loaded before edit). Next Apify call exercises the header path for real.

## 2026-07-05 (Phase 6 complete)
Phase: 6 | Step: live run + close-out
Status: DONE
Files changed: docs/run_costs.md (new), config.yaml (max_post_age_days 14->7 reverted), data/Joinee/output/* (generated, gitignored)
Test result: PASS (pipeline exit 0)
Notes: Live run funnel: 1624 collected (48 kw x 35) -> 325 semantic -> 196 content filters -> 111 gate-kept -> 81 targets / 30 avoid -> top-30 sheet (90 variants). Baseline 06-22 (at 50/kw): 2301 -> 498 -> 241 -> 136 -> 30. Career-transition classifier: 21 hits + 2 HR-dominant across the 1624 collected. Outputs: comment_sheet_2026-07-05.csv, comment_runner_2026-07-05.html (built via scratch/build_comment_ui.py - NOT pipeline-integrated, follow-up), 2026-07-05_plan.json. Apify cost $3.249 recorded in docs/run_costs.md (vs ~$4.60 implied at 50/kw). Remaining: commit close-out files, push, open PR; squash-merge only after operator eyeballs the live sheet.

## 2026-07-05 (post-run improvement)
Phase: post-6 | Step: promote comment-runner HTML into the pipeline
Status: DONE (pending smoke-test confirmation)
Files changed: planner/comment_runner.py (new), run_pipeline.py (auto-build after sheet write, fails soft), tests/test_comment_runner.py (3 new tests), docs/pipeline_runbook.md
Test result: PASS (pytest 32/32; module output byte-identical to today's scratch-built runner; smoke test running)
Notes: Operator confirmed the runner HTML is the working surface -> promoted scratch/build_comment_ui.py into planner/comment_runner.py, wired into run_pipeline behind the sheet write (skipped under --no-persist/--dry-run since no sheet is written). scratch/build_comment_ui.py left in place but superseded - candidate for deletion.

## 2026-07-05 (I-10 Phases 0-3)
Phase: I-10 | Step: Phases 0-3 complete
Status: DONE
Files changed: feedback/__init__.py, feedback/sheet_client.py (new), scripts/setup_feedback_sheet.py (new), run_pipeline.py (keyword accumulation + sheet append hook), tests/test_feedback_sheet.py (10 new tests), requirements.txt (gspread>=6.0.0)
Test result: PASS (pytest 42/42)
Notes: Phase 0 - connectivity OK (gspread Bearer auth, sheet 'VVLeng Feedback' opened). Phase 1 - 4 tabs created with headers/dropdowns/amber formatting. Phase 3 - matched_keywords accumulated before text-dedup so all keywords that found a post survive; 7.9% of posts appear under 2+ keywords on 2026-07-05 data. Phase 2 - sheet_client.py: append_daily_log/append_run_cost/read_daily_log/print_end_of_run_checklist, all fail-soft, dedup-guarded, dry-run skipped. WAITING on smoke test before Phase 4 STOP.

## 2026-07-05 (I-10 Phase 4-5)
Phase: I-10 | Step: retro-load + usage doc + guard fix
Status: DONE
Files changed: run_pipeline.py (comments_map guard on feedback append), docs/FEEDBACK_SHEET.md (new)
Test result: PASS (pytest 42/42)
Notes: Phase 4 retro-load - daily_log 60 rows (30 x 06-22 + 30 x 07-05), both with variant text populated. run_costs 2 rows. Smoke-test bug fixed: feedback append now guarded by comments_map truthy (same as write_comment_sheet) so --skip-llm runs don't write sparse rows. Phase 5 - FEEDBACK_SHEET.md written. Ready to commit + PR.

## 2026-07-05 (session-end)
Phase: post-run cleanup | Step: source_keywords backfill + .gitignore + branch cleanup
Status: DONE
Files changed: scratch/backfill_source_kw_20260705.py (NEW — one-shot backfill script),
  .gitignore (added *service*account*.json + gcp_*.json patterns)
Test result: N/A
Notes: source_keywords (col H) was blank in all 60 sheet rows because the retro-load
  and comment-sheet paths don't carry that field. Raw Apify JSON (posts_20260705T071720Z.json)
  has query.search per post; backfill script matched all 30 Joinee/2026-07-05 rows by URL
  (0 misses) and wrote comma-joined keywords. 06-22 rows left blank — pre-feature, raw
  data not on disk. Future live runs populate H automatically via matched_keywords in dl_rows.
  Local branches feat/feedback-sheet, feat/feedback-sheet-clean, feat/prompt-rewrite deleted.
  gitignore updated for GCP service-account key patterns (per CC_FEEDBACK_SHEET instruction).
  Operator action still needed: rotate Apify token (old scratch/ logs had token in URLs
  before the Authorization-header fix). 06-22 run_costs row has placeholder cost ($4.60);
  operator should update from Apify console. Next session: Phase 7 operator work (comment
  sheet → fill M-Q cols → export commented_log_2026-07-05.csv).
