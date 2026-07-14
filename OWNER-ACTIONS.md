# Owner actions — what's waiting on you

The single place to look for manual steps only **you** can do — things the agent
(Claude Code or Cline) cannot or must not do on its own:

- live runs that cost money and need your explicit go-ahead,
- steps in external accounts (API dashboards, scraper consoles, DB provisioning),
- credential setup / rotation,
- judgment calls the agent shouldn't make for you.

**Convention:** whenever the agent hits a gate like this, it adds an item here and
flags the related task with `⏸ OWNER ACTION` so nothing silent slips through. Check
the box when done; move finished items to "Resolved". This file is committed, so it
survives across sessions and works for both Cline and Claude Code (both read the
repo cold each session).

---

## ⏸ Open — needs you

- [ ] **Cut the `prod` branch after this adoption merges to master** (manifest-adoption, Tier C)
  **Why it's yours:** it changes how you run production, and the branch should be
  cut from master *after* `infra/manifest-adoption` is merged, so prod includes the
  framework. An agent shouldn't establish your deploy ref for you.
  **What to do:** once `infra/manifest-adoption` is merged to master:
  ```
  git checkout master && git pull
  git branch prod master          # create prod at the reviewed master state
  git checkout prod               # keep prod checked out for real Joinee runs
  ```
  From then on, **run production only from the `prod` branch**, and promote
  deliberately after reviewing master:
  ```
  git checkout prod && git merge --ff-only master   # advance prod to reviewed master
  ```
  If `--ff-only` refuses, master has history prod doesn't — review before forcing.
  **Unblocks:** the manifest's production-safety rail (`git.prod_branch: prod`,
  `prod_promotion: branch`). Until then, master is de-facto prod — fine for the next
  2–3 days per your note, but don't enable autonomous orchestrator merges before this.

- [ ] **Decide when to enable autonomous orchestrator merges** (manifest-adoption)
  **Why it's yours:** a judgment call about letting agents commit/merge unattended.
  **What to do:** only after the `prod` branch rail above exists and you've watched
  a few task/* runs pass their gates by hand. Not required for the pipeline to work.
  **Unblocks:** hands-off orchestrator operation.

- [ ] **Install the pre-commit hook — the genuine last step** (manifest-adoption, Tier D)
  **Why it's yours:** installing into `.git/hooks/` persists code execution beyond an
  agent session; the original instruction was "don't install the hook yet — that's the
  last step." An agent auto-mode guard also (correctly) blocks it. Do it once the repo
  is on master and the `prod` branch exists, so the hook's clean-repo assumption and
  prod-block both hold.
  **What to do:** from the repo root, after this branch is merged:
  ```
  cp tools/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
  sh .git/hooks/pre-commit    # sanity: should print nothing and exit 0 on a clean repo
  ```
  Also install it into each orchestrator worktree (the hook is per-clone; `.git/hooks/`
  is not version-controlled). The committed `tools/pre-commit` is the source of truth —
  it blocks direct commits to master/main/prod and runs full-repo structure validation.
  **Unblocks:** commit-time enforcement of the manifest structure rules.

<!-- Template entry:
- [ ] **<short title>** (<decision id / task ref>)
  **Why it's yours:** <e.g. needs your API key / costs money / account step>
  **What to do:** <concrete steps>
  **Unblocks:** <what proceeds once done>
-->

---

## ✅ Resolved

<!-- - [x] **<title>** (<date>): <what was decided/done>. -->
