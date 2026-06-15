# LinkedIn Intelligence System — Architecture Backlog
Last updated: 2026-06-14 (evening session)

This file is a parking lot for future features, open decisions, and deprioritized items.
It is NOT a build instruction document — nothing here should be handed to Cline until
explicitly promoted to an amendment. Items are grouped by category and annotated with
the earliest phase they become relevant.

---

## 1. Apify Actor Status & Backlog

### Current config variables and their status:

| Config key | Actor | Status | Notes |
|---|---|---|---|
| `post_search` | `harvestapi/linkedin-post-search` | ✅ Validated & in use | Field mapping documented. Covers keyword search (Route 2) and author-filtered search (Route 1 with `authorPublicIdentifiers`) |
| `post_scraper` | TBD | ⚠️ Likely redundant | Post search actor covers both routes. Only needed if profile-specific scraping without keywords proves to need a different actor. Validate before filling in. |
| `profile_scraper` | TBD (harvestapi equivalent) | ❌ Not validated | Needed for Route 1 influencer watchlist — scraping all posts from specific profiles without keyword query. **Must validate before Cline builds Route 1 normaliser.** Run same test as post_search: 1-2 profile URLs, 5 posts, paste raw output for field mapping. |
| `follower_scraper` | TBD | 🔒 Locked — do not build | Route 3 (follow graph traversal). Disabled by design until 2+ weeks of stable pipeline running. Revisit in Phase 5. |

### Action before Phase 1:
- Test `harvestapi/linkedin-profile-posts` (or equivalent) with 1-2 influencer profile URLs
- Paste raw output for field mapping validation
- Fill in `profile_scraper` config value only after validation
- Decide whether `post_scraper` is needed or can be removed from config

---

## 2. Comment Scraping

### Current decision:
`scrapeComments: false` is the correct default. `engagement.comments` count is already
returned in the standard post response — sufficient for post scoring and ranking (need #1).

### Backlog items:

**Phase 4-5: Comment content scraping for signal extraction**
- Scrape comment text on posts that score above engagement threshold
- Extract pain points, vocabulary, questions from comment threads
- Feed into knowledge base / weekly brief
- Implementation: second-pass enrichment run, not part of initial collection
- Charged per comment by Apify — must be gated behind score threshold to control cost

**Out of scope (no timeline):** Monitoring reactions/replies to own comments
- Requires polling specific comment threads over time
- Apify not well-suited for this — would need a different approach
- Revisit only after core pipeline is stable and proven

---

## 3. Content Signal Sources

### Channel stack — ranked by expected signal quality for alumni network / community management SaaS niche:

| Channel | Signal Quality | Cadence | Status |
|---|---|---|---|
| LinkedIn post discovery pipeline | High | Daily | Building now |
| G2 / Capterra reviews | High | Monthly | **Next after LinkedIn pipeline stable** — highest value next source. Structured practitioner pain points, exact vocabulary, competitor comparisons. |
| Newsletters / thought leader scraping | Medium | Weekly | Backlog — after G2/Capterra |
| Reddit | Low (this niche) | — | Parked — wrong channel for B2B professional audience. Revisit for other client niches. See Reddit architectural finding below. |
| CMX Hub / Community Club Slack | Very high | Manual only | No automation path — monitor manually |

### Reddit architectural finding (for future niches):
If Reddit is revisited, the correct subreddit discovery approach is:
1. Run global keyword search first
2. Collect which subreddits relevant posts come from
3. Rank subreddits by signal density
4. Only then add to subreddit browse list
Do NOT manually guess subreddit names.

---

## 4. Route 3 — Follow Graph Traversal

- Disabled by default in config
- Do not enable until pipeline has been running stably for 2+ weeks
- Phase 5 feature
- Requires its own validation pass before building

---

## 5. Knowledge Graph Vision

A longer-term vision exists for a multi-dimensional quantified knowledge graph covering:
- Market intelligence
- Content strategy
- Competitive positioning
- Audience understanding

The LinkedIn post discovery pipeline and future Reddit listener are Phase 1 data
collectors feeding this vision. Additional brainstorm material exists in separate
Claude chat sessions — flag for a future consolidation session before any build work.

---

## 6. Relationship State Machine — Edge Cases

Current design: `new → contacted → warm → converted / cold`

Open questions not yet resolved:
- What is the exact trigger for `warm` vs `contacted`? (number of interactions? response received?)
- What reactivates a `cold` profile? (time-based? manual only?)
- How is `converted` defined for this client? (booked a call? signed up for trial?)

These need client-specific definition before the state machine is fully implemented.
Park until first live run produces real data to reason from.

---

## 7. Repost Strategy

- `repost` action type is in the amendment — LLM-generated commentary, weekly cap enforced
- Open question: what is the weekly cap number? (suggested: 1-2 reposts/week max)
- Open question: does a repost replace an original post slot, or is it additive?
- Decision needed before Cline builds the planner module

---

## 8. Dashboard & Reporting

- Basic dashboard is in Phase 0 scope (E2E test)
- Longer term: what metrics matter most for client reporting?
  - Engagement rate on comments
  - Profile visits generated
  - Connection requests accepted
  - Warm leads generated
- No build work until core pipeline is validated

---

## 9. Multi-Client Expansion

- Current build is single-client (alumni_saas)
- Config architecture already supports multiple clients via `clients/{client_id}.yaml`
- No multi-client testing until alumni_saas pipeline is stable
- When expanding: each new niche needs its own Apify actor validation pass
  (field names may differ, signal sources may differ)

---

## 10. Confirmed Technical Decisions (this session)

### LLM model strategy (final for now)
- `default_model: gpt-4o-mini` — added to config.yaml, used when no task-specific model passed
- Task models (`comment`, `hook`, `signal`, `scoring`) all on `gpt-4.1-mini` via LZ
- Models live in `config.yaml` under `llm:` — NOT in `.env`
- `.env` contains only `LLM_API_KEY` and `LLM_BASE_URL`
- **Backlog:** swap `default_model` to `gemini-3.1-flash-lite` for classification/scoring after Phase 2 stable — confirm LZ availability first

### Apify actor ID format
- API calls must use `~` not `/` as separator: `harvestapi~linkedin-post-search`
- Slash format causes 404 — apply to all actors in `apify_client.py`

### llm_client.py model resolution order (fixed)
- explicit arg → `config.llm.default_model` → `os.getenv("LLM_DEFAULT_MODEL")` → `"gpt-4o-mini"`
- `comment_model` is task-specific — callers must pass it explicitly, it is not a fallback default
