# Vivendix strategy notes (not pipeline-consumed)

Preserved from the original draft `clients/vivendix.yaml` (created 2026-07-07 in
a Claude chat unaware of this repo's actual client-config schema). That draft
failed to parse as YAML (unquoted `: "` inside a list item) and, independent of
that bug, used a schema (`persona`/`icp`/`routes`/`angles`/`constraints`/
`cadence`/`thresholds`) that doesn't match what `config_loader.py`'s
`ClientConfig` reads. `clients/vivendix.yaml` has been rewritten to the real
schema (see that file); the operational fields (niche, keywords, collection,
filter, scoring, action_limits, cost_limits) were remapped there.

This doc keeps the strategy content that has **no current wiring into the
pipeline** — there is no per-client prompt-injection mechanism today
(`content/llm_client.py`'s `load_prompt()` only reads fixed global files under
`content/prompts/`; a `persona.voice_ref` pointing at a per-client prompt file
is not something any code path loads). Treat this as reference material for a
human writing/reviewing comments, or as a spec for a future feature, not as
config.

## Persona

- Role: founder, algorithmic marketing agency
- Identity signal: "mathematician-algorithmist" (use sparingly, not in every comment)
- Language: en

## ICP

- Primary: online business founders, post-PMF, growth plateaued
- Team size: 20+
- Revenue: $2M+ annual
- Marketing state: no proper marketing dept; stuck between freelancers/low-level
  in-house and $5-10k+/mo agencies
- Seniority: founder, co-founder, ceo, owner
- Disqualifiers:
  - pre-PMF / idea-stage (marketing before PMF is harmful)
  - enterprise / has full marketing department
  - agencies themselves (unless watchlist creators)

**Note:** ICP defines who we want *noticing* the comments, not whose posts we
target — plateau founders mostly lurk (see Route 1 rationale below).

### Psychology (load-bearing — read before writing any comment for this client)

Proud, not defeated — built a real business on their own instincts and
contacts, and that's a legitimate achievement they hold onto. The plateau hit
once the original contact list ran dry, not because they are bad operators.
They know intellectually that they need marketing. They believe marketing is a
kind of expert magic they don't personally possess. Their skepticism toward
every channel (SEO, ads, cold email, social) is EARNED, not naive — they tried
things and watched them fail, usually because execution had too many
easy-to-miss details and no one kept it running daily. They've priced out every
option: DIY (no time, no results), junior in-house hire (expensive, months to
fail), real "magician" freelancers/experts (too costly or not interested in
SME), agencies (real capability, but $5-10k+/mo, annual lock-in, no confidence
without ad budget behind it). Conclusion: not stupid, not lazy, boxed in by
real constraints. Comments must never suggest they missed something obvious —
the correct move is to name the boxed-in feeling and reframe the cause as
bandwidth/discipline, not competence.

### Earned-skepticism note

Do not argue that their failed tactic would have worked. Confirm it genuinely
didn't, then relocate the cause: not the channel, but the lack of daily
disciplined execution and measurement no busy founder can sustain by hand.
Core mirror move for this client — see `by_hand` angle below.

## Routes

### Route 1 — influencer watchlist (audience proxies, not ICP accounts)

Creators plateau-founders READ. Curate 12-18 handles across these buckets
before first run (all currently empty placeholders):

- `bootstrapping_saas_growth` — 4-5 handles (indie/bootstrapped SaaS voices, MRR-transparent founders)
- `founder_led_sales` — 3-4 handles (founder-led sales / pipeline content)
- `agency_critique_marketing_ops` — 3-4 handles (people critiquing agency model, marketing systems thinkers)
- `sme_operators` — 2-3 handles (operators writing for $1-10M businesses)

Selection rule: audience must be founders of $1M+ online businesses, comment
sections active (20+ substantive comments/post), poster is NOT a direct
competitor pitching the same service.

### Route 2 — keyword search (high-intent moments)

`sortBy: relevance` — validated empirically on Joinee, keep. Keyword tiers and
NOT-block exclusions have been remapped into `clients/vivendix.yaml`'s
`keywords` block.

**Pending:** KGraph pass. "Tried everything, nothing worked" may be blaming
CHANNELS ("SEO is dead") in some posts and BANDWIDTH ("no time to do it
right") in others — different readers needing different angles
(`contrarian_channel_blame` vs `by_hand`). Once KGraph can classify which
dominates, split this tier1 entry into two and route to the matching angle.

### Route 3 — follow graph (actual prospects)

`enabled: true` in the original draft, seed: own_network + engagers_on_own_posts
+ invite_acceptors. **Not built** — per `00-project-overview.md`, Route 3
(follower graph) is locked pending a stability window. Don't treat the
draft's `enabled: true` as a real toggle; there's no code path reading it.

## Angle tagging (language-lab layer — no code consumes this today)

Every generated comment was meant to carry exactly one angle tag, flowing
through to the daily comment sheet and feedback CSV. This requires the
per-client prompt-injection feature that doesn't exist yet.

| Angle | Description |
|---|---|
| `mirror_relief` | normalise the struggle, offer relief not diagnosis |
| `comfort_as_fragility` | surface fragility via question, never argue for growth |
| `algorithm_vs_experience` | expert + algorithm > expert alone |
| `market_gap` | structural mismatch — nobody serves SME price point systematically |
| `bml_discipline` | plateau = discipline problem, loop never closed |
| `contrarian_seo` | SEO is a tactic inside Authority, not a strategy |
| `contrarian_content_volume` | 50 structured articles beat 200 unstructured |
| `contrarian_audits` | most audits paralyse — 47 red flags, no prioritisation |
| `contrarian_broadcasting` | posting without replies is broadcasting, not engagement |
| `contrarian_learning_curve` | the agency learning curve is a business model |
| `contrarian_data_pitch` | "we rely on data" — ask what data they have on YOUR business |
| `contrarian_organic_paid` | organic and paid are time horizons, not alternatives |
| `contrarian_domain_authority` | authority is earned, not manufactured |

### New angles (hero-copywriting session, July 2026)

These map to the hero-headline turn-word debate — treat comment performance as
a cheap, fast vote on which word wins, cheaper/faster than a site A/B test.

- **isolation_fallacy** (candidate turn word: "Alone.") — tactics aren't wrong,
  they just don't compound alone; SEO, ads, cold email each do one job, and
  treated as the whole strategy, each looks like it "doesn't work."
- **by_hand** (candidate turn word: "By hand.") — the real failure mode is
  execution: every channel demands expert-grade detail AND daily clockwork
  discipline. No busy founder — or marketer — can sustain that by hand
  indefinitely. Founder's own confession-as-pitch: "I can't either, that's why
  I build algorithms."
- **unmeasured** (candidate turn word: "Unmeasured.") — the channel wasn't the
  problem, the lack of a measure-learn-adjust loop was; one unmeasured attempt
  looks identical to a channel that "doesn't work."
- **not_magic_but_math** — reframes "marketing is magic done by magicians"
  directly; replace magician-dependency with algorithm-dependency,
  budget-friendly because formulas don't bill by the hour like magicians do.
- **earned_skepticism** — validate that past attempts genuinely failed before
  reframing cause; never argue the old tactic would have worked; agree, then
  relocate blame to process/bandwidth, not competence or channel choice.
- **proud_not_stuck** — lead with the legitimate win (built a real business on
  instinct and network) before naming the plateau; useful on posts where the
  founder is visibly proud of traction.

## Feedback CSV extra columns (requires feedback-loop feature, not built)

- `angle`
- `reply_received` (bool)
- `profile_view_delta` (manual, daily)
- `dm_started` (bool)
- `post_blame_type` (enum: channel | bandwidth | unclear) — cheapest manual
  version of the KGraph channel-blame-vs-bandwidth-blame split, start
  collecting by hand before KGraph can automate it.

## Hard constraints (mirror principle — enforce in judge prompt once a
per-client prompt mechanism exists)

**Never:**
- diagnose the poster's failure or imply they are broken/losing
- argue that a tactic the poster says failed would actually have worked
  (contradicts `earned_skepticism` — confirm the failure, then relocate the
  cause to process/bandwidth, never dispute the result)
- imply the poster missed something obvious or should have known better
- use motivational filler ("unleash", "level up", "game-changer")
- use "B2B" as descriptor (use "serious buyers", "businesses that sell online")
- pitch Vivendix or link anything
- praise openers ("Great post!")
- em-dash or double hyphen (n-dash with spaces only: " – ")

**Always:**
- under 70 words
- named concept or reframe not present in the original post
- peer-to-peer register (operator to operator, not vendor to prospect)
- when referencing a failed tactic, validate the failure was real before
  reframing the cause (`earned_skepticism` / `by_hand` angles)
