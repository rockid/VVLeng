#!/bin/sh
# promote_to_prod.sh — advance the `prod` branch to the reviewed `master` state.
#
# Production runs come from `prod`, and `prod` only moves when you deliberately run
# this — so an in-flight/unreviewed `master` can never become "what runs against
# the client next". Safe by construction: --ff-only REFUSES to move prod unless it
# is a clean fast-forward of the reviewed master (no surprise merges, no rewrites).
#
# Usage:  bash tools/promote_to_prod.sh
set -e

echo "Fetching latest reviewed master..."
git fetch origin

echo "Advancing prod -> origin/master (fast-forward only)..."
git checkout prod
git merge --ff-only origin/master
git push origin prod

echo ""
echo "Done. prod is now at $(git rev-parse --short prod) (= reviewed master)."
echo "Production runs from prod will use this state. Switch back to work with: git checkout master"
