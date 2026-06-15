# Cline Testing Instructions — LinkedIn Engagement System
# For use alongside pre_launch_test_plan.md

These instructions tell Cline what to do during each test step.
The test plan is for the human operator. This doc is for Cline.
Hand both documents to Cline at the start of a testing session.

---

## Your Role During Testing

You are a test executor and error fixer — not a feature builder.
During testing sessions:
- Run the test scripts as specified
- Report results clearly
- Fix errors in existing code only
- Do NOT add new features or refactor working code
- Do NOT proceed to the next step until the current step passes

---

## Step 1 — Dry Run

Run:
```bash
python run_pipeline.py --client joinee --dry-run
```

Report:
```
[STEP 1 RESULT]
Status: PASS / FAIL
Output: <paste terminal output>
Issues found: <list any errors>
```

If FAIL: fix import errors, missing config keys, or path errors.
Do NOT proceed to Step 2 until Step 1 passes.

---

## Step 2 — DB Initialization

Run:
```bash
python -c "from db.session import init_db; init_db()"
```

Then verify:
```bash
python -c "
import sqlite3
conn = sqlite3.connect('data/joinee/engagement.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print([t[0] for t in tables])
conn.close()
"
```

Report:
```
[STEP 2 RESULT]
Status: PASS / FAIL
Tables found: <list>
Missing tables: <list or 'none'>
```

Expected tables: `posts`, `profiles`, `actions`, `apify_usage`, `weekly_signal_briefs`
If schema is wrong: check `db/models.py` against architecture, fix and re-run.

---

## Step 3 — Normaliser Verification

**Do not call Apify.** Verify normaliser against the confirmed field mapping.

Create a test fixture if `tests/fixtures/sample_post_search.json` does not exist:
```bash
mkdir -p tests/fixtures
```

Then write this exact content to `tests/fixtures/sample_post_search.json`:
```json
{
  "type": "post",
  "id": "7471786833119698944",
  "linkedinUrl": "https://www.linkedin.com/posts/test-activity-7471786833119698944-THWa",
  "content": "Test post content about alumni network community management.",
  "author": {
    "id": "ACoAADSY2UwBiaPDbYN30mlLT4pzpwF8yEuSEnc",
    "universalName": null,
    "publicIdentifier": "test-profile",
    "type": "profile",
    "name": "Test Author",
    "linkedinUrl": "https://www.linkedin.com/in/test-profile",
    "info": "Community Manager at Test Co"
  },
  "postedAt": {
    "timestamp": 1781412800102,
    "date": "2026-06-14T04:53:20.102Z",
    "postedAgoShort": "6h"
  },
  "postImages": [],
  "engagement": {
    "id": "7471786831983042560",
    "likes": 42,
    "comments": 1,
    "shares": 1,
    "reactions": [{"type": "LIKE", "count": 39}]
  },
  "query": {
    "sortBy": "date",
    "page": 1,
    "search": "alumni network community management",
    "postedLimit": "week"
  }
}
```

Then run normaliser against it:
```python
# run inline
import json
from collector.normaliser import normalise_post

with open('tests/fixtures/sample_post_search.json') as f:
    raw = json.load(f)

post = normalise_post(raw)
print(f"post_id: {post.post_id}")
print(f"url: {post.url}")
print(f"content: {post.content[:50]}")
print(f"author_id: {post.author_id}")
print(f"author_name: {post.author_name}")
print(f"author_handle: {post.author_handle}")
print(f"author_headline: {post.author_headline}")
print(f"posted_at: {post.posted_at}")
print(f"likes: {post.likes}")
print(f"comments: {post.comments}")
print(f"shares: {post.shares}")
print(f"has_images: {post.has_images}")
print(f"source_query: {post.source_query}")
```

**Confirmed field mapping to verify against:**
```
post_id        ← item.id
url            ← item.linkedinUrl
content        ← item.content
author_id      ← item.author.id
author_name    ← item.author.name
author_handle  ← item.author.publicIdentifier  (NOT universalName — it is null)
author_url     ← item.author.linkedinUrl
author_headline← item.author.info
posted_at      ← item.postedAt.date  (ISO string, NOT timestamp)
timestamp_ms   ← item.postedAt.timestamp
likes          ← item.engagement.likes  (NOT item.likes — engagement is nested)
comments       ← item.engagement.comments
shares         ← item.engagement.shares
has_images     ← len(item.postImages) > 0
source_query   ← item.query.search
```

Report:
```
[STEP 3 RESULT]
Status: PASS / FAIL
Null fields: <list any fields that are None when they shouldn't be>
Mapping errors: <list any fields reading from wrong path>
```

Fix any null fields by correcting the path in `normaliser.py`.

---

## Step 4 — Collector Unit Test

Run with real Apify (this costs ~$0.05):
```bash
python run_pipeline.py --client joinee --stage collect \
  --keywords "alumni network community management" --max-posts 5
```

If `--stage` flag doesn't exist, create and run `tests/test_collector.py`:
```python
from config_loader import load_config
from collector.route_keywords import collect_keyword_posts

config = load_config("joinee")
config.client.collection.posts_per_keyword = 5

posts = collect_keyword_posts(
    config,
    keywords=["alumni network community management"],
    tiers=["tier1"]
)
print(f"Collected: {len(posts)} posts")
for p in posts[:3]:
    print(f"  - {p.author_name}: {p.content[:80]}...")
    print(f"    likes={p.likes}, comments={p.comments}, tier={p.keyword_tier}")
    print(f"    url={p.url}")
    assert p.post_id is not None, "post_id is None"
    assert p.content is not None, "content is None"
    assert p.url is not None, "url is None"
print("All assertions passed")
```

Report:
```
[STEP 4 RESULT]
Status: PASS / FAIL
Posts returned: <count>
Null fields found: <list or 'none'>
Sample post (first result summary): <author, like count, first 50 chars of content>
Apify cost logged: <check apify_usage table>
```

---

## Step 5 — Semantic Filter Test

Run locally — no API calls:
```python
# tests/test_filter.py
from config_loader import load_config
from processor.semantic_filter import build_niche_embedding, passes_filter

config = load_config("joinee")
niche_text = config.build_niche_embedding_text()
niche_embedding = build_niche_embedding(niche_text)

tests = [
    ("RELEVANT", "Struggling with ghost members in our alumni network. 80% haven't logged in for 6 months. Anyone solved this with Circle or Hivebrite?", "tier1", True),
    ("IRRELEVANT", "Just closed our Series B! Excited to scale our fintech payments infrastructure.", "tier1", False),
    ("BLOCKED", "We are recruiting a senior community manager. Job opening in London.", "tier1", False),
]

all_pass = True
for label, text, tier, expected in tests:
    result, score = passes_filter(text, niche_embedding, config, tier=tier)
    status = "OK" if result == expected else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"[{status}] {label}: passed={result} (expected={expected}), score={score:.3f}")

print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
```

Report:
```
[STEP 5 RESULT]
Status: PASS / FAIL
Relevant post: passed=<>, score=<>
Irrelevant post: passed=<>, score=<>
Blocked post: passed=<>, score=<>
```

If relevant post fails (score too low): lower `min_semantic_similarity` to 0.25 in `clients/joinee.yaml`.
If irrelevant post passes: raise threshold to 0.40. Retest.

---

## Step 6 — Post Scorer Test

Run locally using posts from Step 4 raw output:
```python
# tests/test_scorer.py
from config_loader import load_config
from processor.post_scorer import score_post
from collector.normaliser import normalise_posts
import json, glob, os

config = load_config("joinee")

# Load most recent raw file
raw_files = glob.glob("data/joinee/raw/raw_*.json")
assert raw_files, "No raw files found — run Step 4 first"
latest = max(raw_files, key=os.path.getctime)

with open(latest) as f:
    raw_posts = json.load(f)

posts = normalise_posts(raw_posts)[:3]
all_pass = True

for post in posts:
    result = score_post(post, config)
    ok = 0.0 <= result.score <= 1.0 and result.post_type in ["comment_target", "repost_candidate", "avoid"]
    if not ok:
        all_pass = False
    print(f"Score: {result.score:.2f} | Type: {result.post_type} | {'OK' if ok else 'FAIL'}")
    print(f"  freshness={result.freshness:.2f} velocity={result.velocity:.2f} relevance={result.relevance:.2f}")

print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
```

Report:
```
[STEP 6 RESULT]
Status: PASS / FAIL
Score range: <min>–<max> (should be 0.0–1.0)
Post types seen: <list>
Any zeros across all dimensions: <yes/no — indicates broken scorer>
```

---

## Step 7 — LLM Connectivity Test

Run (costs ~$0.01):
```python
# tests/test_llm.py
from content.llm_client import call_llm
import json

response = call_llm(
    system="You are a helpful assistant. Respond only with valid JSON, no markdown.",
    user='Return this exact JSON: {"status": "ok", "message": "LLM connection working"}'
)
print(f"Raw response: {response}")
parsed = json.loads(response)
assert parsed["status"] == "ok", f"Unexpected response: {parsed}"
print("PASS — LLM connected and returning valid JSON")
```

Report:
```
[STEP 7 RESULT]
Status: PASS / FAIL
Model used: <which model responded>
Latency: <rough seconds>
JSON valid: yes/no
```

If JSON parse fails: LLM is wrapping output in markdown backticks.
Fix: add to `llm_client.py` response cleaning before return:
```python
response = response.strip().strip('`')
if response.startswith('json'):
    response = response[4:].strip()
```

---

## Step 8 — Signal Extractor Test

Run (costs ~$0.05):
```python
# tests/test_signal.py
from config_loader import load_config
from content.signal_extractor import extract_signal
from collector.normaliser import normalise_posts
import json, glob, os

config = load_config("joinee")

raw_files = glob.glob("data/joinee/raw/raw_*.json")
latest = max(raw_files, key=os.path.getctime)
with open(latest) as f:
    raw_posts = json.load(f)

posts = normalise_posts(raw_posts)[:3]
results = extract_signal(posts, config)

all_pass = True
for i, r in enumerate(results):
    has_tags = isinstance(r.get("topic_tags"), list) and len(r["topic_tags"]) > 0
    has_score = isinstance(r.get("signal_score"), (int, float)) and 1 <= r["signal_score"] <= 10
    ok = has_tags and has_score
    if not ok:
        all_pass = False
    print(f"Post {i+1}: {'OK' if ok else 'FAIL'}")
    print(f"  topic_tags: {r.get('topic_tags')}")
    print(f"  pain_points: {r.get('pain_points')}")
    print(f"  signal_score: {r.get('signal_score')}")

print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
```

Report:
```
[STEP 8 RESULT]
Status: PASS / FAIL
JSON parse errors: yes/no
topic_tags meaningful: yes/no (not generic like "LinkedIn" or "community")
signal_score in 1-10 range: yes/no
```

---

## Step 9 — End-to-End Mini Run

Run (costs ~$0.50–1.00):
```bash
python run_pipeline.py --client joinee \
  --keywords "alumni network community management" \
  --max-posts 10
```

Or temporarily set `posts_per_keyword: 10` in `clients/joinee.yaml` and run:
```bash
python run_pipeline.py --client joinee
```

After run, verify outputs exist:
```bash
ls data/joinee/raw/
ls data/joinee/output/
ls data/joinee/plans/
```

Report:
```
[STEP 9 RESULT]
Status: PASS / FAIL
raw/ files: <list>
output/ files: <list>
plans/ files: <list>
Daily plan actions count: <number>
apify_usage table has entries: yes/no
Pipeline completed without exception: yes/no
```

Wait for human to review plan quality before proceeding to Step 10.

---

## General Rules During Testing

- After each step: output `[STEP N RESULT]` block before doing anything else
- If a step fails: fix only what is needed to make that step pass — do not refactor
- Do not skip steps — even if you think a later step will work
- Do not run Step 10 (full run) without explicit human confirmation
- All test scripts go in `tests/` folder — clean up after confirmed passing
- Update `progress.md` after each step
