# Coding Standards

> Written Python-first (most projects here are Python). If a project uses another
> language, adapt the mechanics but keep the principles.

## The dry-run / live pattern (preserve this for every external call)

Every external or paid call (LLM, scraper/API, DB, …) must support both real and
`dry_run` execution from the same call site:

```python
def some_call(...):
    if dry_run:
        return _mock_some_call(...)
    return _real_some_call(...)
```

- The `dry_run` flag comes from central config, not scattered literals.
- **Mock output must be obviously fake** — never mistakable for real data
  downstream. Use an explicit marker (e.g. a `"_mock": true` flag, implausible
  round numbers, a `[DRY_RUN stub]` string). Pick one convention per project and
  keep it consistent.
- New external integrations follow the *existing* shape in the project, not a new
  one. **There is currently no reference implementation of this pattern in
  VV_Leng** — `collector/apify_client.py` and `content/llm_client.py` are both
  live-only with no `dry_run` branch. Don't invent a one-off mock for a new
  integration while this gap is open; see `.cline-tasks/TASK-1.md`. New code
  should still route all settings through `config_loader.py` as everything else
  does.

## Phase discipline and conflict resolution

- Architecture work happens in phases (defined in
  `docs/VVLeng_architecture_amendment_combined.md`). Complete one phase before
  starting the next; don't begin later-phase work without the user confirming the
  current phase is done. State the current phase target at the start of a
  phase-scoped session.
- If the base architecture doc and the amendment conflict, **the amendment wins**
  — don't silently pick one, say which document you're following and why.
- If a user instruction in the session conflicts with either architecture
  document, follow the session instruction, but flag the departure rather than
  silently overriding the doc.

## Schema / shared-shape discipline

- Keep one source of truth for shapes shared across modules/stages. Don't define a
  parallel local copy of a shared model.
- Validate anything crossing a module boundary into a typed model (pydantic or
  equivalent); internal helpers can use plain dicts.
- When adding fields for a future stage, keep them consistent with the
  downstream/target schema so they map cleanly later — don't redesign casually.

## Config and secrets

- All external config (URLs, model names, keys, timeouts) goes through
  `config_loader.py` (merges `config.yaml` + `clients/{client}.yaml` + `.env`).
  Never hardcode a URL, model string, or key inline.
- If a new setting would be safe to commit to a public repo, it's config, not a
  secret. Keep `.env.example` in sync when adding a variable.
- Flag any new dependency before adding it to `requirements.txt` — name the
  package and why it's needed.

## Style

- Type hints on all function signatures.
- Prefer small, single-purpose functions over one large one; each module should
  read top-to-bottom in a predictable order.
- Don't add new top-level structure (new package dirs) preemptively. Flat is fine
  while small; restructure when a file actually outgrows itself, not in
  anticipation.

## Network / cost awareness

- Paid calls cost real money in live mode. Don't write loops or retries that can
  fan out into many live calls without a clear bound and the user's awareness.
- Respect rate limits and API etiquette (honest `User-Agent` with a real contact
  where requested). Degrade gracefully on a failed external call rather than
  crashing the whole run, where the design allows.
