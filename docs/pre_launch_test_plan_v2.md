# LinkedIn Engagement System — Pre-Launch Test Plan

**Purpose:** Validate each module before spending Apify credits or LLM tokens at scale.  
**Principle:** Free tests first, then cheap, then paid. Stop and fix before proceeding if any step fails.  
**Time estimate:** 2–3 hours total if nothing breaks.

---

## Before You Start — What You Need Ready

- [ ] Cline has completed Phase 0 and Phase 1 of the implementation sequence (build is stable, new config architecture in place)
- [ ] `.env` filled with real API keys (Apify + LLM)
- [ ] `clients/joinee.yaml` exists with keyword list populated
- [ ] Apify account funded (minimum $20 recommended for testing)
- [ ] Python environment active, `pip install -r requirements.txt` done

---

## Step 1 — Config & Environment (free, ~10 min)

**What you're testing:** Config loads correctly, client folder structure creates, no import errors.

```bash
python run_pipeline.py --client joinee --dry-run
```

**What to check:**
- Prints all pipeline steps without calling any API
- Creates `data/joinee/` with all subdirectories
- No import errors, no missing key errors
- Confirm it reads from `clients/joinee.yaml` (add a print statement in `config_loader.py` temporarily if unsure)

**Fix before continuing:** Any import error, missing config key, or path error.

---

## Step 2 — DB Initialization (free, ~5 min)

**What you're testing:** SQLAlchemy models create the DB schema correctly.

```bash
python -c "from db.session import init_db; init_db()"
```

Or if there's a dedicated init script:
```bash
python run_pipeline.py --client joinee --init-db-only
```

**What to check:**
- No errors
- `data/joinee/engagement.db` (or wherever `DATABASE_URL` points) exists
- Open it with any SQLite viewer (DB Browser for SQLite is free) and confirm all tables exist: `posts`, `profiles`, `actions`, `apify_usage`, `weekly_signal_briefs`
- Confirm new columns are present: `semantic_score`, `keyword_tier`, `relationship_status`, `post_score`, etc.

**Fix before continuing:** Any schema error or missing table.

---

## Step 3 — Apify Actor Validation (cheap, ~15 min, ~$0.10)

**This is the most important step.** Do it manually in the Apify console — not through code.

### 3a. Manual run in Apify console

**Actor already validated — confirmed working.** Use these exact input field names (wrong field names = 0 results):

1. Log into apify.com
2. Go to actor: `harvestapi/linkedin-post-search`
3. Enter this validated input:
   ```json
   {
     "searchQueries": ["alumni network community management"],
     "sortBy": "date",
     "postedLimit": "week",
     "maxPosts": 5,
     "scrapeReactions": false,
     "scrapeComments": false
   }
   ```
4. Run it. Wait for completion (usually 1–3 min).
5. Go to dataset output. Save one raw item as `tests/fixtures/sample_post_search.json`.

**What to check:**
- Posts are returned (actor confirmed working in pre-launch validation)
- Posts are recent — within the last week (confirms `postedLimit` working)
- If 0 results on a specific keyword → try broader keyword, do not switch actor

### 3b. Field mapping — already validated

Field mapping for `harvestapi/linkedin-post-search` was validated in pre-launch session.
**Do not re-derive — use the confirmed mapping below:**

```json
{
  "post_id":         "item.id",
  "url":             "item.linkedinUrl",
  "content":         "item.content",
  "author_id":       "item.author.id",
  "author_name":     "item.author.name",
  "author_handle":   "item.author.publicIdentifier",
  "author_url":      "item.author.linkedinUrl",
  "author_headline": "item.author.info",
  "posted_at":       "item.postedAt.date",
  "timestamp_ms":    "item.postedAt.timestamp",
  "likes":           "item.engagement.likes",
  "comments":        "item.engagement.comments",
  "shares":          "item.engagement.shares",
  "has_images":      "item.postImages.length > 0",
  "source_query":    "item.query.search"
}
```

**Critical warnings:**
- `author.universalName` is null in real output — use `author.publicIdentifier` instead
- `engagement` is nested — read `item.engagement.likes` not `item.likes`
- Use `item.postedAt.date` (ISO string) for DB storage, not `item.postedAt.timestamp`
- `has_images` must be derived from `postImages` array length — no direct boolean field

### 3c. Verify normaliser.py uses confirmed mapping

Give Cline this mapping and instruct it to verify `normaliser.py` matches exactly.
Do not let Cline re-derive field names from scratch.

**Profile posts actor (influencer watchlist — Route 1) is NOT yet validated.**
Do not build Route 1 normaliser until `harvestapi/linkedin-profile-posts` is tested
separately and field names confirmed.

---

## Step 4 — Collector Unit Test (cheap, ~$0.20)

**What you're testing:** The collector module calls Apify correctly and normaliser produces valid `Post` objects.

```bash
python run_pipeline.py --client joinee --stage collect --keywords "alumni network" --max-posts 5
```

Or if there's no stage flag yet, add a quick test script:

```python
# test_collector.py (run once, then delete)
from config_loader import load_config
from collector.route_keywords import collect_keyword_posts

config = load_config("joinee")
# Temporarily override to minimum
config.client.collection.posts_per_keyword = 5

posts = collect_keyword_posts(config, keywords=["alumni network"], tiers=["tier1"])
print(f"Collected: {len(posts)} posts")
for p in posts[:3]:
    print(f"  - {p.author_name}: {p.text[:80]}...")
    print(f"    likes={p.likes}, tier={p.keyword_tier}, url={p.url}")
```

**What to check:**
- At least 1 post returned
- `Post` objects have non-null `post_id`, `text`, `url`, `author_name`
- `keyword_tier` = "tier1"
- Text looks like real LinkedIn post content (not HTML, not empty)
- Posts written to `data/joinee/raw/raw_{date}.json`

**Fix before continuing:** Any None fields in critical columns, empty text, or actor errors.

---

## Step 5 — Semantic Filter Unit Test (free, ~5 min)

**What you're testing:** The local embedding model loads and filters posts correctly. No API calls.

```python
# test_filter.py (run once, then delete)
from config_loader import load_config
from processor.semantic_filter import build_niche_embedding, passes_filter
import json

config = load_config("joinee")

# Build embedding from niche definition
niche_text = config.build_niche_embedding_text()
niche_embedding = build_niche_embedding(niche_text)

# Test with obviously relevant post
relevant_post_text = "Struggling with ghost members in our university alumni network. 80% haven't logged in for 6 months. Anyone solved this with Circle or Hivebrite?"
result, score = passes_filter(relevant_post_text, niche_embedding, config, tier="tier1")
print(f"Relevant post: passed={result}, score={score:.3f}")

# Test with obviously irrelevant post  
irrelevant_post_text = "Just closed our Series B! Excited to scale our fintech payments infrastructure."
result, score = passes_filter(irrelevant_post_text, niche_embedding, config, tier="tier1")
print(f"Irrelevant post: passed={result}, score={score:.3f}")

# Test with blocked substring
blocked_post_text = "We are recruiting a senior community manager to join our team. Job opening in London."
result, score = passes_filter(blocked_post_text, niche_embedding, config, tier="tier1")
print(f"Blocked post: passed={result}, score={score:.3f}")
```

**What to check:**
- Relevant post: `passed=True`, score > 0.35
- Irrelevant post: `passed=False`, score < 0.30
- Blocked post: `passed=False`, score=0.0 (blocked before semantic scoring)
- First run will download the model (~80MB) — normal, cached after

**If relevant post fails:** Lower `min_semantic_similarity` to 0.25 in client YAML.  
**If irrelevant post passes:** Raise threshold to 0.40. Retest.

---

## Step 6 — Post Scorer Unit Test (free, ~5 min)

**What you're testing:** Post scoring logic works on real Post objects from Step 4.

```python
# test_scorer.py (run once, then delete)
from config_loader import load_config
from processor.post_scorer import score_post
import json

config = load_config("joinee")

# Load posts saved from Step 4
with open(f"data/joinee/raw/raw_{today}.json") as f:
    raw_posts = json.load(f)

# Score first 3 posts
from collector.normaliser import normalise_posts
posts = normalise_posts(raw_posts)

for post in posts[:3]:
    result = score_post(post, config)
    print(f"Score: {result.score:.2f} | Type: {result.post_type}")
    print(f"  freshness={result.freshness:.2f} velocity={result.velocity:.2f}")
    print(f"  relevance={result.relevance:.2f} opportunity={result.opportunity:.2f}")
    if result.avoid_reason:
        print(f"  avoid_reason: {result.avoid_reason}")
```

**What to check:**
- Scores in 0.0–1.0 range (not all zeros, not all ones)
- `post_type` values are one of `comment_target`, `repost_candidate`, `avoid`
- Freshness makes sense relative to post age
- No crashes on edge cases (0 likes, missing fields)

---

## Step 7 — LLM Connectivity Test (cheap, ~$0.01)

**What you're testing:** LLM API key works, model responds, JSON parsing works.

```python
# test_llm.py (run once, then delete)
from content.llm_client import call_llm

response = call_llm(
    system="You are a helpful assistant. Respond only with valid JSON.",
    user='Return this exact JSON: {"status": "ok", "message": "LLM connection working"}'
)
print(response)
```

**What to check:**
- Returns valid JSON (not an error message, not markdown-wrapped)
- No auth errors
- Latency feels reasonable (<5 seconds)

---

## Step 8 — Signal Extractor Unit Test (cheap LLM cost, ~$0.05)

**What you're testing:** Signal extraction prompt returns valid structured JSON on real posts.

```python
# test_signal.py (run once, then delete)
from config_loader import load_config
from content.signal_extractor import extract_signal
import json

config = load_config("joinee")

# Use 3 posts from Step 4 raw output
with open(f"data/joinee/raw/raw_{today}.json") as f:
    raw_posts = json.load(f)

from collector.normaliser import normalise_posts
posts = normalise_posts(raw_posts)[:3]

results = extract_signal(posts, config)
for r in results:
    print(json.dumps(r, indent=2))
```

**What to check:**
- Returns valid JSON array, one object per post
- `topic_tags` are meaningful (not generic like "LinkedIn" or "post")
- `pain_points` are empty list `[]` or real specific pains — not hallucinated
- `signal_score` is 1–10
- No JSON parse errors (if there are: check the LLM is not wrapping output in markdown backticks — add a strip step in `signal_extractor.py`)

---

## Step 9 — End-to-End Mini Run (low cost, ~$0.50–1.00 total)

**What you're testing:** All modules working together as a pipeline on minimal data.

```bash
python run_pipeline.py --client joinee \
  --keywords "alumni network" "community management platform" \
  --max-posts 10
```

Or if keywords come from config, temporarily set `posts_per_keyword: 10` in client YAML for this test run.

**What to check:**
- No crashes end-to-end
- `data/joinee/raw/` — raw JSON written
- `data/joinee/output/` — `signal_{date}.csv` written
- `data/joinee/plans/` — daily plan JSON written
- Open daily plan JSON: does it contain at least 1 action? Does the suggested comment text make sense for the post?
- Open `signal_{date}.csv`: do topic_tags and pain_points look like real market intelligence?
- Check `apify_usage` table: is cost tracking recording correctly?

**Manual review criteria for the daily plan:**
Read the first 3 suggested comments. Ask yourself:
1. Is this comment relevant to the post it's responding to?
2. Would I be comfortable posting this on behalf of the client?
3. Does it sound like a human, not a bot?

If answer to any is "no" → the comment generation prompt needs tuning before going to full scale.

---

## Step 10 — First Real Run (normal cost, ~$2–5)

Only proceed here once Steps 1–9 all pass.

1. Reset `posts_per_keyword` in client YAML to `30` (or your intended operating value)
2. Populate `influencer_watchlist` in `clients/joinee.yaml` with 10–15 real LinkedIn profile URLs
   - **Note:** Route 1 (influencer watchlist) uses `harvestapi/linkedin-profile-posts` actor
   - This actor is NOT yet validated — do not enable Route 1 until profile scraper is tested
   - For Step 10, run keyword search only (Route 2): set `routes.watchlist.enabled: false` in client YAML
3. Run the full pipeline (keyword route only):
   ```bash
   python run_pipeline.py --client joinee
   ```
4. Review outputs:
   - How many posts collected total?
   - What was the semantic filter drop rate? (check logs)
   - How many posts survived to LLM scoring?
   - Is the daily plan actionable?

**Calibration decisions after first real run:**
- Drop rate >90% in semantic filter → lower `min_semantic_similarity` to 0.25
- Too many irrelevant posts surviving → raise threshold to 0.40
- Daily plan has <5 actions → check keyword engagement thresholds, may be too high for niche volume
- Daily plan has >20 actions → action limits in client YAML are working; check quality not just quantity

**After Step 10 passes — next validation (separate session):**
- Test `harvestapi/linkedin-profile-posts` actor manually in Apify console
- Paste raw output to Claude for field mapping
- Only then enable Route 1 in config

---

## Quick Reference — Cost Per Step

| Step | API calls | Estimated cost |
|---|---|---|
| 1–2 | None | Free |
| 3 | Apify: 1 keyword, 5 posts | ~$0.05 |
| 4 | Apify: 1 keyword, 5 posts | ~$0.05 |
| 5–6 | None (local) | Free |
| 7 | 1 LLM call | ~$0.01 |
| 8 | 1 LLM call, 3 posts | ~$0.05 |
| 9 | Apify: 2 keywords, 10 posts + LLM | ~$0.50 |
| 10 | Full run | ~$2–5 |
| **Total to Step 9** | | **~$0.70** |

---

## If Something Breaks

| Symptom | Most likely cause | Fix |
|---|---|---|
| Normaliser returns None fields | Actor field names don't match mapping | Check confirmed field mapping in Step 3b of this doc — paste raw JSON to Claude to re-verify |
| Semantic filter drops everything | Threshold too high, or niche embedding text too narrow | Lower `min_semantic_similarity` to 0.25; check `build_niche_embedding_text()` output |
| LLM returns non-JSON | Model wrapping output in markdown | Add `.strip().strip('`').replace('json\n','')` before `json.loads()` in signal_extractor and comment_gen |
| 0 posts from Apify | Actor broken or wrong input format | Try fallback actor `apimaestro/...`; check Apify run logs for error |
| Daily plan empty | All posts scored as `avoid` | Check `post_scorer.py` avoid conditions — may be too aggressive |
| DB errors on startup | Schema out of sync with models | Delete `engagement.db` and re-run `init_db()` (dev only — never in prod) |
