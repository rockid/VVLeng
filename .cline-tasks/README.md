# Task handoffs

Discrete, bounded task specs for Cline (or any implementer) to execute one at a
time. Format per `CLAUDE.md` "Scope discipline" and `TASK-TEMPLATE.md`: scope,
files to touch, acceptance criteria, constraints.

These are *handoffs*, not a status tracker — the implementer's run reports + git
history record what actually got done. Delete a task file once its change is merged
(or move it to a `done/` subdir if you prefer a record).

## Current tasks

| Task | Title | Priority | Gating dependency |
|---|---|---|---|
| TASK-1 | Add a free dry-run/mock mode for Apify and LLM calls | 2 | — |

## Decisions — status

TASK-1 has an open naming decision (reuse `--dry-run` vs. a new flag) that must be
resolved with the user before implementation starts — see the task file.

## Open owner actions (manual)

Tasks needing *you*, not the agent, are tracked in **`OWNER-ACTIONS.md`** at repo
root — the single place for "what's waiting on me." Nothing open there as of this
adoption (2026-06-24).

## Suggested order

Just TASK-1 right now — unblocked, no owner action gating it.
