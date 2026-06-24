# Session Closing Procedure

Run through this before ending a task or handing off. The next session (possibly a
different tool, possibly weeks later) only has the repo to go on — leave it
understandable cold.

## 0. Write progress.md first (mandatory, do this before anything else below)

- [ ] Append a final entry to `progress.md` covering everything done this session
      that isn't already logged, per `06-progress-log.md`'s format. Read the last
      ~500 chars back to confirm the write actually landed.
- [ ] Never output a session summary or say "safe to close" before this entry
      exists and is timestamped correctly.

## 1. Verify nothing is broken

- [ ] Re-run the smoke test (see `01-session-start.md` §5). Confirm it exits
      cleanly. Verifying with `--dry-run` (mocked, free) is preferred over a live
      run — confirm you didn't trigger an unintended paid Apify/LLM call while
      verifying (i.e. you didn't drop `--dry-run`/`--skip-collect --skip-llm`
      without meaning to).
- [ ] If you changed a shared schema/shape (`db/models.py`, the post/comment dict
      shapes passed between pipeline stages), confirm every consumer still
      validates against the new shape — schema changes are the highest-blast-radius
      edit.

## 2. Secrets check before any commit

- [ ] `git status` — confirm `.env` (and any real secret/config files) are **not**
      staged. Only placeholder templates (`.env.example`) belong in git.
- [ ] `git diff --staged` — scan for anything resembling a real key, token, or
      credential, even in a comment or fixture.
- [ ] If a secret was ever committed, don't just delete it in a new commit — flag
      it. It's in history and needs real remediation (rotate, scrub).

## 3. Commit logically

- [ ] Follow `04-github-workflow.md`. One logical change per commit; don't bundle
      unrelated changes (e.g. a schema change and a docs typo) into one.
- [ ] `git status --short` before committing — confirm only expected files are
      staged. Never stage `data/`, test fixtures, or anything not intentionally
      changed this session.

## 4. Keep docs honest

- [ ] If behavior changed (new flag, new env var, new output field), update the
      relevant docs in the **same** commit/PR as the code — not as a maybe-later
      follow-up.
- [ ] If `00-project-overview.md`'s status table is now stale, update it.

## 5. Leave a handoff note

- [ ] `progress.md` (step 0 above) is this project's primary handoff mechanism —
      a `TODO.md` at repo root is only needed for something `progress.md`'s format
      doesn't capture well (e.g. a multi-step plan spanning several future
      sessions).
- [ ] If the task is complete, it's fine for `TODO.md` not to exist — don't leave
      stale handoff notes lying around.

## 6. Don't leave the main branch broken

- [ ] The default branch should always pass the smoke test. For anything
      non-trivial, work on a branch (see `04-github-workflow.md`); don't merge with
      a failing smoke test, even temporarily.
