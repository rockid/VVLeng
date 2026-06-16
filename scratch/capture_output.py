#!/usr/bin/env python3
"""Run run_tier1_tier2.py and capture its stdout to a file, handling Unicode properly."""
import subprocess
import sys
import os

script = os.path.join(os.path.dirname(__file__), "run_tier1_tier2.py")
out_path = os.path.join(os.path.dirname(__file__), "tier1_tier2_output_2026-06-17.txt")

result = subprocess.run(
    [sys.executable, script],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    env={**os.environ, "PYTHONIOENCODING": "utf-8"}
)

combined = result.stdout + result.stderr
with open(out_path, "w", encoding="utf-8") as f:
    f.write(combined)

print(f"Written {len(combined)} chars to {out_path}")
print(f"Return code: {result.returncode}")
# Print the last 20 lines as summary
lines = combined.splitlines()
for line in lines[-20:]:
    print(line)