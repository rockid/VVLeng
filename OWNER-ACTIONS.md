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

- [ ] **Decide when to enable autonomous orchestrator merges** (manifest-adoption)
  **Why it's yours:** a judgment call about letting agents commit/merge unattended.
  **What to do:** the `prod` rail now exists, so this is safe to consider — but do it
  only after you've watched a few `task/*` runs pass their gates by hand. Not required
  for the pipeline to work.
  **Unblocks:** hands-off orchestrator operation.

<!-- Template entry:
- [ ] **<short title>** (<decision id / task ref>)
  **Why it's yours:** <e.g. needs your API key / costs money / account step>
  **What to do:** <concrete steps>
  **Unblocks:** <what proceeds once done>
-->

---

## ✅ Resolved

- [x] **Cut the `prod` branch** (2026-07-14): created `prod` from reviewed master
  (7d0596e) and pushed to origin. Production runs come from `prod`; advance it with
  `bash tools/promote_to_prod.sh` (safe fast-forward). See README "Production runs".
- [x] **Enforce the hook across clones/worktrees** (2026-07-14): set
  `core.hooksPath = tools` so git uses the version-controlled `tools/pre-commit`
  directly — it applies to the main repo and to every orchestrator worktree
  automatically (verified). A fresh clone on a new machine needs one command once:
  `git config core.hooksPath tools` (documented in README "New clone setup").

<!-- - [x] **<title>** (<date>): <what was decided/done>. -->
