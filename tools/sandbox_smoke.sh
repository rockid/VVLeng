#!/bin/sh
# sandbox_smoke.sh — free, zero-key "does the pipeline still work" check.
#
# Wraps the project's --dry-run smoke test, which mocks BOTH external/paid calls
# (collector/apify_client.py + content/llm_client.py) and implies --no-persist,
# so it costs nothing and needs no API keys. The PYTHONUTF8/PYTHONIOENCODING
# exports are required on Windows or post text crashes default cp1252 stdout.
#
# Used by the `sandbox` stage gate in project_manifest.yaml. Run from repo root.
set -e

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

python run_pipeline.py --client Joinee --dry-run
