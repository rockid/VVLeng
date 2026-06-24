# Session Initiation Procedure

Run through this at the start of every task, before editing anything. Assume no
memory of prior sessions beyond what's in the repo — treat every session as
picking up cold.

## 1. Orient

- [ ] Read `00-project-overview.md` if not already loaded.
- [ ] **Read `progress.md`** — this project's rolling session log (see
      `06-progress-log.md`). It is the primary cold-start anchor, ahead of
      conversation memory.
- [ ] `git log --oneline -10` and `git status` — see what actually happened last;
      don't assume from conversation context or from `progress.md` alone.
- [ ] If `git status` shows uncommitted changes from a prior session, surface them
      to the user before doing anything else. Don't silently build on, discard, or
      commit someone else's in-progress edit.
- [ ] If this session follows an interruption, reload, or any sign context was
      lost, treat this as a **recovery**, not a fresh start: state the last
      `progress.md` timestamp/status, the last git commit, and where you're
      resuming from, before touching any file. If the last `progress.md` entry is
      `BLOCKED` or `FAILED`, ask the user whether to retry or move on rather than
      re-attempting it silently.
- [ ] Confirm the active client (`config.yaml: active_client`, override with
      `--client`). Default is `Joinee` — data lives under `data/Joinee/`.
- [ ] For design-level work, read `docs/pipeline_runbook.md` first — it reflects
      what's actually implemented. `docs/VVLeng_architecture.md` +
      `docs/VVLeng_architecture_amendment_combined.md` (amendment supersedes the
      base doc on conflict) are the deeper target-design reference.
      `docs/architecture_backlog.md` is read-only awareness — never implement from
      it without an explicit instruction to promote an item out of the backlog.

## 2. Confirm mode before running anything

- [ ] There is **no project-wide dry-run default** — `collector/apify_client.py`
      and `content/llm_client.py` call out live with no mock path (tracked gap,
      `.cline-tasks/TASK-1.md`). The zero-cost equivalent is the flag combination
      `--skip-collect --skip-llm` (add `--no-relevance-gate` to also silence the
      gate's LLM calls). `--dry-run` alone only suppresses persistence — it does
      **not** stop live Apify/LLM calls.
- [ ] **Never run without `--skip-collect --skip-llm` (or omit them) without the
      user explicitly asking for a live/paid run.**

## 3. Re-derive state, don't assume it

- [ ] If picking up a partially-built feature, read the actual code to determine
      what's done — not a remembered summary. If the status table in
      `00-project-overview.md` doesn't match reality, flag it and fix the rule file
      as part of the task.
- [ ] Check for a handoff note (`TODO.md` at repo root, or a note atop the most
      recently touched file) in addition to `progress.md`. Read it before planning.

## 4. Plan before acting

- [ ] Use plan-mode reasoning for anything beyond a trivial single-file fix; state
      the plan back before executing.
- [ ] For ambiguous requests, ask before guessing — especially anything touching
      shared schema/shapes (`db/models.py`, the post/comment dict shapes passed
      between pipeline stages) or `.env.example` (changing a default affects
      everyone).

## 5. Sanity-check the baseline

- [ ] Before changing anything, run the project's smoke test to confirm you're
      starting from a working state:
      ```
      PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python run_pipeline.py --client Joinee --skip-collect --skip-llm
      ```
      (Windows: the `PYTHONUTF8`/`PYTHONIOENCODING` prefix is required — post text
      can contain characters that crash default cp1252 stdout otherwise.)
      If it fails on a clean pull, that's pre-existing — call it out rather than
      attributing later failures to your own changes.
