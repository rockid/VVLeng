# GitHub Management

## Branching

- The default branch always passes the smoke test (see session procedures).
- Branch per piece of work, prefixed by what it touches:
  - `fix/...` — bug fixes
  - `docs/...` — documentation-only
  - `infra/...` — tooling, CI, dependencies, framework adoption
  - `feat/<area>-...` — feature work, area = `collector`, `processor`, `content`,
    `planner`, `db`, or `dashboard` (match the repo-layout module it touches)
- Don't develop directly on the default branch except trivial one-line fixes
  (typo, comment) that can't break the smoke test.

## Commits

This project uses **Conventional Commits**: `type(scope): short imperative subject`.

| Type       | When to use                              |
|------------|-------------------------------------------|
| `feat`     | New feature or module                    |
| `fix`      | Bug fix                                  |
| `refactor` | Code restructuring, no behaviour change  |
| `test`     | Adding or updating tests                 |
| `docs`     | Documentation-only changes               |
| `chore`    | Config, dependencies, tooling            |
| `perf`     | Performance improvement                  |

Examples: `feat(collector): add incremental dedup`, `fix(config): resolve YAML
!string tag`, `docs(cline): add git discipline to CLINE.md`.

- One logical change per commit. A schema change and an unrelated docs fix are two
  commits even in the same session.
- Body (when the diff isn't self-explanatory): what changed and *why*, not a
  restatement of the diff. Record decisions: "chose X over Y because Z" — what a
  cold-start future session most needs.

## Pull requests

- Open a PR for anything beyond a trivial fix, even solo — a review checkpoint and
  a written record, which matters more here since sessions don't carry memory.
- PR description states: what area it touches, what was tested (the
  `--skip-collect --skip-llm` smoke test at minimum; live verification if
  applicable), and any open questions/follow-ups.
- Squash-merge to keep the default branch history readable.

## Tags

- No tags exist yet. When milestones are worth pinning, use `v0.1-phase{N}`
  matching the amendment's phase numbering (e.g. `v0.1-phase0`), so it's trivial to
  roll back to a last-known-good slice.

## `.gitignore` — already covers the framework baseline

`.env`, `__pycache__/`, `*.py[cod]`, `*.bak`, `.venv/`/`venv/`/`env/`, and the
whole `data/` tree (generated per-client output — regenerable, not committed).
The committed config file (`config.yaml`, `clients/*.yaml`) IS meant to be
committed — don't gitignore it. Only secrets (`.env`) and generated data stay out.

## Before every push

- [ ] `.env` is not staged.
- [ ] No real private/per-context config staged.
- [ ] Smoke test passes locally.
- [ ] Commit messages follow the convention above.
