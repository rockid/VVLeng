# Cline Working Rules — LinkedIn Intelligence System

## 1. Model & Context
- This is a Python-based LinkedIn engagement pipeline
- All architecture documents are in the `/docs` folder
- **Read these at session start, in this order:**
  1. `docs/linkedin_engagement_system_architecture.md` — v1.0 base
  2. `docs/VVLeng_architecture_amendment_combined.md` — supersedes all previous amendments
  3. `docs/architecture_backlog.md` — for awareness only, do NOT implement anything from here unless explicitly instructed
- Active client ID: `joinee`
- Re-read all three documents at the start of every session before touching any files

---

## 2. Session Start Protocol
Before writing a single line of code or touching any file, you must:

1. Read `progress.md` (if it exists) to understand what has already been completed
2. Output a numbered plan for this session's tasks — specific files to create/modify, in order
3. Wait for explicit confirmation before starting work

Example plan output format:
```
SESSION PLAN:
1. Create .env.example from amendment template
2. Create config.yaml with defaults (active_client: joinee)
3. Create clients/joinee.yaml skeleton
4. Update run_pipeline.py to load new config structure
5. Verify --dry-run executes without errors
Confirm to proceed? (yes / adjust plan first)
```

---

## 3. Status Reporting — Every Step

After every file created, modified, or deleted — immediately output:
```
[DONE] <filename> — <one line describing what changed>
```
After every [DONE], immediately update `progress.md` and — if applicable — commit to git (see [Section 9 — Git Discipline](#9-git-discipline)).

If you are about to make a decision that has multiple valid approaches, stop and output:
```
[DECISION] <what I need to decide> — <option A> vs <option B>
Waiting for direction.
```

If you have not written or modified any file in the last 2 minutes, stop and output:
```
[STUCK] Attempting: <what I'm trying to do>
Blocker: <what is preventing progress>
Options: <what I could try>
```

Do not silently retry more than once. Surface blockers immediately.

---

## 4. Phase Discipline

- The amendment defines 5 phases. **Complete one phase at a time.**
- Do not begin a new phase without explicit user confirmation
- At the end of each phase output:
```
[PHASE COMPLETE] Phase X — <name>
Files changed: <list>
Next phase: <name> — ready to proceed? (yes / not yet)
```
- Current phase target will be stated at the start of each session. Default assumption: **Phase 0** unless told otherwise.

---

## 5. Conflict Resolution

If instructions in the base architecture and the amendment conflict:
- **Amendment always wins**
- Do not silently pick one — output `[CONFLICT]` and state which document you are following and why

If a user instruction in the current session conflicts with the architecture documents:
- Follow the current session instruction
- Flag it: `[OVERRIDE] Departing from architecture: <what and why>`

---

## 6. File & Config Rules

- **Never hardcode API keys, client IDs, or paths** — always read from config
- **Never modify `.env`** — only create or update `.env.example`
- Config hierarchy: `.env` (secrets) → `config.yaml` (defaults) → `clients/{client_id}.yaml` (client overrides)
- Active client is set in `config.yaml` under `active_client: joinee`, overridable with `--client` CLI flag
- All client data goes under `data/joinee/` — create on first run, never hardcode path
- Before creating any new file, check if it already exists and read it first
- **Backlog items** (`docs/architecture_backlog.md`) are read-only reference — never implement anything from the backlog without explicit instruction

---

## 7. Testing Rules

- After any change to a module, run its unit test if one exists
- After Phase 0, the acceptance test is: `python run_pipeline.py --dry-run` exits clean with no exceptions
- Do not mark a phase complete if the dry-run is broken
- If a test fails, output `[TEST FAIL]` with the full error before attempting a fix

---

## 8. progress.md — Mandatory Log

`progress.md` is the single source of truth between sessions. Treat it as a hard requirement, not a courtesy.

### When to update — non-negotiable triggers:
- After every step completes (build, test, or any file change)
- After every test result (pass OR fail)
- After every debug/fix cycle — even if it took many attempts
- Before outputting any session-end summary
- Any time you are about to stop work for any reason
- Do not start a new step until `progress.md` has been updated for the previous one

### Update format:
```
## YYYY-MM-DD HH:MM
Phase: <X> | Step: <name>
Status: DONE / BLOCKED / FAILED / SKIPPED
Files changed: <list — or 'none' if test/debug only>
Test result: PASS / FAIL / N/A
Notes: <what worked, what failed, what next session needs to know>
```

### Hard rules:
- **Never confirm session complete without writing the final progress.md entry first**
- Debug and fix loops MUST be logged — the final outcome of every fix attempt must be recorded
- If you completed 3 things but only wrote 1 progress entry → you have 2 missing entries. Write them before continuing.
- Do not say "progress.md is up to date" without having actually written to it in this session
- The last entry in progress.md must match the last thing you actually did

### Verification step — mandatory before session end:
```bash
tail -5 progress.md
```
Confirm the timestamp is from this session and reflects the last action taken.
If the last entry is stale → update it now before outputting any session summary.

---

## 9. Git Discipline

Git is mandatory for continuity between sessions and for rollback safety.

### Commit triggers (non-negotiable):
- After every file creation, modification, or deletion that is part of a task step
- After every phase completion
- Before any `[DECISION]` or `[STUCK]` break that might end the session
- **Always** before session end — see [Session End Protocol](#11-session-end-protocol)

### Commit message convention:
```
<type>(<scope>): <short description>

<optional body — only if the short description is not enough>
```

| Type       | When to use                          |
|------------|--------------------------------------|
| `feat`     | New feature or module                |
| `fix`      | Bug fix                              |
| `refactor` | Code restructuring, no behaviour change |
| `test`     | Adding or updating tests             |
| `docs`     | Documentation-only changes           |
| `chore`    | Config, dependencies, tooling        |
| `perf`     | Performance improvement              |

Examples:
- `feat(collector): add incremental dedup`
- `fix(config): resolve YAML !string tag`
- `test(scorer): add edge case for empty posts`
- `docs(cline): add git discipline to CLINE.md`

### What NOT to commit:
- `.env` (secrets) — already in `.gitignore`
- `data/raw/` contents — API fetch artefacts, regenerated each run
- Test fixtures that are auto-generated
- Any file you did not intentionally create or modify

### Verification step — before every commit:
```bash
git status --short
```
Confirm only expected files are staged. If unexpected files appear, investigate before committing.

---

## 10. What NOT to Do

- Do not "think" for more than 2 minutes without producing a file change or a status output
- Do not start Phase 1+ work while Phase 0 is incomplete
- Do not guess at field names for external APIs — the Apify field mapping is documented and must be followed exactly (see session notes)
- Do not install new dependencies without flagging them first: `[DEPENDENCY] Need to add: <package> — reason: <why>`
- Do not refactor existing working code unless explicitly asked

---

## 11. Session End Protocol

Follow these steps in exact order. Do not skip or reorder.

**Step A — Write progress.md first (mandatory):**
Append a final entry to `progress.md` covering everything done this session that isn't already logged. Then run:
```bash
tail -5 progress.md
```
Confirm the entry is there and timestamped correctly.

**Step A2 — Commit all changes to git (mandatory):**
1. Run `git status --short` and verify only expected files are changed
2. `git add` relevant files — do NOT stage `.env`, `data/raw/`, or test fixtures (respect `.gitignore`)
3. `git commit` with a message matching the convention (see [Section 9 — Git Discipline](#9-git-discipline))
4. Run `git log --oneline -3` to confirm the commit landed

**Step B — Only then output the session summary:**
```
SESSION SUMMARY
Completed: <list of steps done this session>
Skipped/Blocked: <anything not done and why>
Next session should start at: <specific step name and phase>
Dry-run status: PASSING / FAILING / NOT YET RUN
progress.md last entry: <paste the timestamp and status line>
```

**Step C — Confirm safe to close:**
Only say "safe to close" after Step A, Step A2, and Step B are all done.
Never say "safe to close" if progress.md has not been written in this session.