# VV_Leng

Semi-automated **LinkedIn engagement pipeline**. It collects LinkedIn posts via
Apify, filters/scores/ranks them, generates candidate comments with an LLM, and
hands a human a ranked daily action plan (CSV + self-contained HTML operator UI).
**No action on LinkedIn itself is automated** — commenting/connecting/posting stays
manual by design (ToS compliance). In production for client **Joinee**.

## Quick start

Install deps and exercise the full pipeline for **free** (mocked Apify + LLM, no
API keys needed):

```bash
pip install -r requirements.txt
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python run_pipeline.py --client Joinee --dry-run
```

`--dry-run` mocks both external calls and implies `--no-persist`. The Windows
`PYTHONUTF8`/`PYTHONIOENCODING` prefix is required — post text can otherwise crash
default cp1252 stdout.

### Smoke test

Reprocess already-collected data without touching the collect/LLM stages:

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python run_pipeline.py --client Joinee --skip-collect --skip-llm
```

Never run without `--dry-run` or `--skip-collect --skip-llm` unless you explicitly
intend a live, paid Apify/LLM run.

### Tests

```bash
python -m pytest tests/ -q
```

## Layout

`run_pipeline.py` orchestrates: collect (Apify) → tier-tag → semantic filter →
content filters → relevance gate → score/blended-rank → comment gen → comment rank
→ outputs. Code is organised by feature package: `collector/`, `processor/`,
`content/`, `planner/` (plus partial `db/`, `dashboard/`, `feedback/`). Per-client
config lives in `clients/`; generated output in `data/{client}/` (gitignored).

## Documentation

- `architecture/overview.md` — concise system entry point.
- `docs/pipeline_runbook.md` — the actually-implemented state (read first).
- `docs/VVLeng_architecture.md` + amendment — target design.
- `.clinerules/` — session procedures, coding standards, GitHub workflow, secrets.
- `project_manifest.yaml` — machine-enforceable structure/stage/gate conventions
  (see `MANIFEST_SUMMARY.md`, `MIGRATION.md`).

## Production runs & the `prod` branch

`master` is for integration; **production runs come from the `prod` branch**, which
only advances when you deliberately promote it. This keeps a half-finished `master`
from ever becoming what runs against the live client (Joinee).

**To do a real (paid) run against Joinee:**

```bash
git checkout prod                                   # switch to the reviewed production state
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python run_pipeline.py --client Joinee
git checkout master                                 # switch back to normal work
```

(Leaving off `--dry-run`/`--skip-collect --skip-llm` makes real, paid Apify/LLM
calls — only do this on `prod` when you mean to.)

**To move `prod` up to the latest reviewed `master`** (after PRs have merged):

```bash
bash tools/promote_to_prod.sh
```

That fast-forwards `prod` to `master` and pushes it — it refuses if `master` isn't a
clean fast-forward, so it can't do anything surprising.

## New clone / new machine setup (one time)

The commit-time rules (no structural violations, no direct commits to
`master`/`main`/`prod`) are enforced by a git hook. After cloning fresh, run once:

```bash
git config core.hooksPath tools
```

This points git at the version-controlled hook (`tools/pre-commit`), so it also
applies automatically to every worktree the orchestrator creates. Verify with a
throwaway attempt to `git commit` on `master` — it should be rejected.

## Config & secrets

Non-secret settings live in `config.yaml` + `clients/{client}.yaml`; secrets
(`APIFY_API_TOKEN`, `LLM_API_KEY`, `LLM_BASE_URL`) live only in `.env` (never
committed) — see `.env.example`. All access goes through `config_loader.py`.
