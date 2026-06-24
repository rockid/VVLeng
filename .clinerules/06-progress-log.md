# progress.md — Mandatory Session Log

`progress.md` is VV_Leng's project-specific cold-start anchor — stronger than the
generic `TODO.md` handoff in `02-session-end.md`. This file exists because earlier
sessions lost context and repeated or skipped work when the log wasn't kept
current; the rules below are deliberately strict for that reason, not boilerplate.

## Format

```
## YYYY-MM-DD HH:MM
Phase: <X> | Step: <name>
Status: DONE / BLOCKED / FAILED / SKIPPED
Files changed: <list — or 'none' if test/debug only>
Test result: PASS / FAIL / N/A
Notes: <what worked, what failed, what next session needs to know>
```

## When to update — non-negotiable triggers

- After every step completes (build, test, or any file change).
- After every test result (pass OR fail).
- After every debug/fix cycle — even if it took many attempts; log the final
  outcome of every fix attempt, not just the last one.
- Before outputting any session-end summary, and before stopping work for any
  reason.
- Do not start a new step until `progress.md` has been updated for the previous
  one.

## The 3-call budget

At most 3 consecutive tool calls (read/write/execute) without a `progress.md`
update. On the 3rd, update before a 4th. Reset the counter after each update.
A multi-edit in one call counts as 1; the call that updates `progress.md` itself
doesn't count against the budget.

## No silent gap > 2 minutes

If active tool use has gone 2 minutes without a `progress.md` update, stop and
state what just happened and what's next, then update the log before the next
tool call.

## Recovery after interruption (window reload / context loss)

If the environment resets or you detect lost context:

1. Read `progress.md` immediately — this is the anchor.
2. Run `git log --oneline -5` to cross-reference the last committed state.
3. State: last `progress.md` entry (timestamp + status), last git commit, and
   where you're resuming from.
4. Don't redo work `progress.md` already marks done — skip forward.
5. If the last entry is `BLOCKED` or `FAILED`, ask the user whether to retry or
   move on before proceeding.

## Read-back verification

After every write to `progress.md`, read the last ~500 chars back to confirm the
write actually landed (Windows-safe, avoids relying on `tail`):

```bash
python -c "print(open('progress.md','r',encoding='utf-8').read()[-500:])"
```

## Session-end summary

Only after the final `progress.md` entry is written and confirmed:

```
SESSION SUMMARY
Completed: <list of steps done this session>
Skipped/Blocked: <anything not done and why>
Next session should start at: <specific step name and phase>
progress.md last entry: <paste the timestamp and status line>
```

Never say "safe to close" if `progress.md` wasn't written this session, or if the
summary's "last entry" doesn't match what's actually in the file.

## In-flight markers

When a step has multiple valid approaches and you need the user's call, or you're
stuck, say so explicitly rather than guessing or retrying silently more than once:

```
[DECISION] <what needs deciding> — <option A> vs <option B>. Waiting for direction.
[STUCK] Attempting: <goal> | Blocker: <what's stopping progress> | Options: <next moves>
```
