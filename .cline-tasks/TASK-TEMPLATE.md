# TASK-{n} — {short imperative title}

**Source:** {where this came from — an audit finding, a design note, a decision}
**Priority:** {1 / 2 / low — and whether it gates other work}
**Type:** {new code / fix / integration / verification / docs}
**Branch:** `{prefix}/{slug}`
**Depends on:** {prior tasks, or — ; note any ⏸ OWNER ACTION gate}

## Why this exists

{1–3 sentences. What problem this solves and why it's scoped the way it is. Enough
for a cold-start implementer to understand intent, not just mechanics.}

## Scope

{What to build/change, concretely. Reference the authoritative source (a captured
sample, a spec section) rather than restating it. If there are known quirks/gotchas
already discovered, list them here so the implementer doesn't rediscover them.}

## Files to touch

- `{path}` — {what changes}

## Acceptance criteria

- {Observable, checkable outcomes.}
- {Dry-run path works with no credentials; mock output obviously fake.}
- {Tests added/updated; smoke test still passes.}
- {Docs updated in the same change if behavior changed.}

## Constraints

- {What NOT to do. Scope boundaries. "Don't build ahead." Cost/live-call limits.}
- {Preserve the dry-run/live pattern; don't bypass the shared transport.}
