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

_Nothing open yet._

<!-- Template entry:
- [ ] **<short title>** (<decision id / task ref>)
  **Why it's yours:** <e.g. needs your API key / costs money / account step>
  **What to do:** <concrete steps>
  **Unblocks:** <what proceeds once done>
-->

---

## ✅ Resolved

<!-- - [x] **<title>** (<date>): <what was decided/done>. -->
