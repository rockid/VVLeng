# Secrets and Safety

## Credentials

- All credentials (`APIFY_API_TOKEN`, `LLM_API_KEY`, `LLM_BASE_URL`) live in `.env`
  only, sourced via `config_loader.py`. Never inline in code, never in a commit,
  never pasted into a committed file (including a `progress.md`/`TODO.md` handoff
  "reminder"). Verified clean as of adoption — no hardcoded secrets found in
  `config_loader.py` or elsewhere.
- `.env.example` ships with placeholders only — verify this stays true whenever a
  new variable is added.
- If `git status`/`git diff` ever shows something resembling a real key about to be
  committed, stop and flag it.
- **Older projects in this umbrella may have hardcoded secrets** (e.g. keys in a
  `config.py`). If you find one, it's not a quick inline fix — flag it in
  `OWNER-ACTIONS.md` for real remediation (rotate the key, scrub git history).
  A secret already pushed is compromised; deleting it in a new commit is not enough.

## Cost discipline

- **There is no dry-run default in VV_Leng today** (see `00-project-overview.md` —
  tracked as `.cline-tasks/TASK-1.md`). The free-iteration path is the explicit
  flag combination `--skip-collect --skip-llm`, not a config default. Use it for
  routine development; only drop the flags to verify a specific change against the
  real Apify/LLM call, and only with the user's awareness it costs money.
- Live calls (LLM, scrapers, paid APIs) cost real money per call. Avoid test loops
  or retry logic that could fan out into many live calls without the user's
  awareness. `collector/apify_client.py` already retries up to `MAX_RETRIES=3` with
  a 60s backoff — don't wrap additional retry logic around it.

## Data sourcing — build vs. buy (umbrella-wide policy)

A real constraint shared across these projects, not just a cost note:

| Source | Policy | Why |
|---|---|---|
| Social platforms — LinkedIn | Buy (Apify) | Anti-bot defenses + restricted APIs; this is VV_Leng's only data source today |

The "buy" row is about paying someone else to carry legal exposure and the
maintenance treadmill for an adversarial, fast-changing target — not "this is hard
to build." If a task asks for a direct LinkedIn scraper bypassing Apify, flag the
mismatch before building it. (Other umbrella source categories — SERP data, review
sites, public crawls, client CRM data — don't apply here; VV_Leng is LinkedIn-only.)

## Third-party scraper/actor formats — verify before implementing (standing rule)

Community-maintained scrapers/actors (e.g. Apify) have input field names and output
shapes that are **not reliably documented and DO change**. Never write
orchestration against an assumed/researched format.

Before implementing any such integration, hand the user a manual verification task
first — inspect the real input form, run one cheap real test (with the user's
explicit go-ahead, since it costs money), and capture the actual input fields + a
sample output. Build only against the captured sample, never a guess. This applies
to every actor, every time — including new actors considered for Route 1
(`profile_scraper`) per `docs/architecture_backlog.md`, which is explicitly
unvalidated.

## API etiquette

- VV_Leng never scrapes LinkedIn directly — all calls go to Apify's own REST API
  (`collector/apify_client.py`) or the laozhang.ai LLM gateway
  (`content/llm_client.py`), both of which abstract the target-site etiquette
  question. No project-specific `User-Agent`/contact requirement is known; revisit
  if either provider's docs ask for one.
- Degrade gracefully on an external hiccup rather than taking down the whole run,
  where the design allows.
