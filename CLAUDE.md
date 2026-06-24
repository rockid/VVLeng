# CLAUDE.md

This file is intentionally thin. `.clinerules/` is the single source of truth for
project rules (session procedures, coding standards, GitHub workflow, secrets
handling) — it's read natively by Cline, and imported here via Claude Code's
`@path` syntax so the same files apply to both tools without duplication or drift.

**One real caveat, not just a formality**: `@imports` load fully into context at
session start — this does not reduce context usage versus writing the same content
directly in this file. The point of this structure is a single edited-once source
of truth, not context saving. If `.clinerules/` grows large enough that
full-context loading becomes a problem, that's a real tradeoff to revisit.

@.clinerules/00-project-overview.md
@.clinerules/01-session-start.md
@.clinerules/02-session-end.md
@.clinerules/03-coding-standards.md
@.clinerules/04-github-workflow.md
@.clinerules/05-secrets-and-safety.md
@.clinerules/06-progress-log.md

## Claude-Code-specific notes

- First-time `@import` of each file above triggers a one-time approval dialog —
  expected, not an error.
- Run `/memory` to confirm exactly which files are actually loaded.
- Editing a `.clinerules/*.md` file mid-session won't change behavior until the
  next session (imports load at launch, not on file change).

## Scope discipline

Architecture-level sessions handle: cross-module decisions, interface design, and
tasks touching >3 files or requiring whole-system reasoning.

Before starting any task, assess: could this be fully specified as a discrete,
bounded instruction to a junior developer? If yes, produce a task handoff file
(`.cline-tasks/TASK-{n}.md` — scope, acceptance criteria, files to touch,
constraints) instead of implementing it yourself.

## VV_Leng-specific notes

- This project previously used a standalone `CLINE.md` with its own heavy session
  discipline (progress.md zero-tolerance logging, phase gates, resumption
  protocol). That content has been folded into `.clinerules/` (mainly
  `01-session-start.md`, `02-session-end.md`, `03-coding-standards.md`, and the
  new `06-progress-log.md`) as part of org-framework adoption
  (2026-06-24) — `.clinerules/` is now the single source of truth; `CLINE.md` no
  longer exists.
- Smoke test: `PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python run_pipeline.py --client Joinee --skip-collect --skip-llm`.
