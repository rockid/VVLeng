# LinkedIn Engagement System — Architecture & Developer Specification

**Version:** 1.0  
**Date:** 2026-06-10  
**Build mode:** Human + AI-assisted (Claude Code)  
**Deployment target:** Local-first, infrastructure-portable

---

## Table of Contents

1. [Purpose & Constraints](#1-purpose--constraints)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Phased Build Plan](#3-phased-build-plan)
4. [Backbone Infrastructure](#4-backbone-infrastructure)
5. [Module Specifications](#5-module-specifications)
6. [Data Layer](#6-data-layer)
7. [LLM Integration](#7-llm-integration)
8. [Apify Integration](#8-apify-integration)
9. [Daily Action Plan Format](#9-daily-action-plan-format)
10. [Dashboard (Streamlit)](#10-dashboard-streamlit)
11. [Project Structure](#11-project-structure)
12. [Environment & Configuration](#12-environment--configuration)
13. [Portability Notes](#13-portability-notes)
14. [Developer Handoff Checklist](#14-developer-handoff-checklist)

---

## 1. Purpose & Constraints

### What this system does

A **semi-automated LinkedIn brand-building tool**. Data collection and planning are fully automated. All actions on LinkedIn (comments, connection requests, post publishing) remain **manual** — the system generates the plan and the content; a human executes it.

### Hard constraints

| Constraint | Rationale |
|---|---|
| No automated posting, commenting, or connection sending | LinkedIn ToS compliance |
| All LinkedIn data collected via Apify (no direct LinkedIn API) | No LinkedIn developer account required |
| LLM provider: laozhang.ai, model configurable per run | Cost control, model flexibility |
| Phase 1 must work on a single developer laptop | Lowest viable startup cost |
| All infrastructure choices must be portable to cloud | Future scaling without rewrite |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  TRIGGER LAYER                                                      │
│  Phase 1: manual CLI   →   Phase 2: cron   →   Phase 3: Prefect    │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌────────────────┐    ┌─────────────────────┐   ┌───────────────────┐
│  COLLECTOR     │    │  PROCESSOR          │   │  CONTENT MODULE   │
│  (Apify)       │───▶│  scoring · graph    │──▶│  comment gen      │
│                │    │  dedup · trends     │   │  hooks · gaps     │
└────────────────┘    └─────────────────────┘   └────────┬──────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │  ACTION PLANNER         │
                    │  daily JSON + CSV       │
                    └────────────┬────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │  DASHBOARD (Streamlit)  │
                    │  human executes actions │
                    └────────────┬────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │  STORAGE LAYER          │
                    │  PostgreSQL · Redis      │
                    │  local JSON (Phase 1)   │
                    └─────────────────────────┘
```

### Data flow (end to end)

```
[seed keywords]
    → run_collector.py  (triggers Apify post search)
    → poll until complete
    → save raw JSON to data/raw/
    → run_processor.py  (filter, score, dedup, topic graph)
    → write results to PostgreSQL
    → run_content.py    (generate comments via laozhang.ai)
    → run_planner.py    (apply limits, prioritise, emit daily plan JSON)
    → dashboard reads JSON
    → human acts on LinkedIn
    → human marks actions done in dashboard
    → feedback stored in actions table
```

---

## 3. Phased Build Plan

### Phase 1 — Backbone (weeks 1–2)

Goal: one working end-to-end loop, manually triggered, minimal dependencies.

| Deliverable | Detail |
|---|---|
| `run_pipeline.py` | Single CLI entry point that runs all steps in sequence |
| Apify post search | Given ≤10 seed keywords, fetch top 20 posts (last 7 days) |
| Apify post scraper | For each post, collect up to 50 engager profile URLs |
| Apify profile scraper | Basic profile enrichment (name, headline, follower count) |
| Lead scoring v1 | Simple weighted score (relevance + recency + engagement) |
| Daily plan JSON | Hardcoded limits: 5 connections, 3 comments per run |
| Dashboard v1 | Streamlit table, checkboxes, "mark done" button |
| Storage | Flat JSON files + SQLite (no Postgres yet) |

Everything in this phase runs with: `python run_pipeline.py --keywords "AI recruitment" "HR tech"`

**Phase 1 is intentionally scrappy.** The goal is to validate the Apify actor outputs and the manual action loop — not to build production infrastructure.

---

### Phase 2 — Hardening (weeks 3–5)

| Deliverable | Detail |
|---|---|
| Replace SQLite with PostgreSQL | Docker Compose adds pg + redis services |
| Apify follower scraper | Influencer mapping (B4) |
| Topic graph (B3) | KeyBERT / YAKE on post text, trending topics |
| Comment generation | laozhang.ai integration, 2–3 variants per post |
| Content gap analysis | Compare user's own post history vs trending topics |
| Full dashboard | Feedback forms, acceptance rate analytics |
| Scheduled runs | cron job (`0 6,14 * * *`) replaces manual trigger |

---

### Phase 3 — Scale & Portability (weeks 6+)

| Deliverable | Detail |
|---|---|
| Prefect DAGs | Replace cron; proper retry, observability, backfill |
| pgvector | Semantic search on profiles and posts |
| Cloud deploy | Docker Compose on Hetzner CX31 or AWS t3.medium |
| Email digest | Sendgrid daily summary (optional) |
| Rate-limit manager | Redis-backed credit tracker per Apify actor |

---

## 4. Backbone Infrastructure

### 4.1 Runtime

- **Language:** Python 3.11
- **Phase 1 entry point:** `python run_pipeline.py` (no scheduler)
- **Phase 2:** cron via `crontab -e` — no new dependency
- **Phase 3:** Prefect 2.x

### 4.2 Storage

| Phase | Tech | Notes |
|---|---|---|
| 1 | SQLite + flat JSON | Zero setup, portable, good for dev |
| 2+ | PostgreSQL 15 + Redis 7.2 | Swap via `DATABASE_URL` env var |

SQLite and PostgreSQL use the same SQLAlchemy ORM models — the switch is a config change, not a code change. See §6 for schema.

### 4.3 Docker Compose (Phase 2+)

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: linkedin_engagement
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7.2-alpine
    ports: ["6379:6379"]

  dashboard:
    build: ./dashboard
    ports: ["8501:8501"]
    env_file: .env
    depends_on: [postgres, redis]

volumes:
  pgdata:
```

`run_pipeline.py` can run either inside Docker or directly on the host — both read from `.env`.

### 4.4 Scheduler progression

```
Phase 1:  python run_pipeline.py          # developer runs manually
Phase 2:  0 6,14 * * * /path/to/run.sh   # cron entry
Phase 3:  prefect deployment run          # Prefect Cloud or self-hosted
```

The pipeline code does not change between phases — only the trigger changes.

---

## 5. Module Specifications

### Module A — Collector (`collector/`)

**Responsibility:** All communication with Apify. Normalises raw actor output into internal Python objects.

#### A.1 Interface

```python
# collector/apify_client.py

def run_actor(actor_id: str, input_payload: dict) -> str:
    """Trigger actor, return dataset_id. Polls until complete."""

def download_dataset(dataset_id: str) -> list[dict]:
    """Download and return raw actor output as list of dicts."""
```

```python
# collector/normaliser.py

def normalise_posts(raw: list[dict]) -> list[Post]:
    """Map Apify post-search output to internal Post objects."""

def normalise_profiles(raw: list[dict]) -> list[Profile]:
    """Map Apify profile-scraper output to internal Profile objects."""
```

#### A.2 Actor routing

| Input type | Actor ID (configurable) | Default |
|---|---|---|
| Keyword search | `apify/linkedin-post-search` | see `.env` |
| Post detail + engagers | `apify/linkedin-post-scraper` | see `.env` |
| Profile enrichment | `apify/linkedin-profile-scraper` | see `.env` |
| Follower mining | `apify/linkedin-followers-scraper` | see `.env` |

Actor IDs are stored in `.env` as `APIFY_ACTOR_POST_SEARCH`, etc. — swap without code changes.

#### A.3 Incremental collection

Before triggering a post-search actor, query the DB for posts already scraped in the last 7 days for the same keyword. Skip those URLs.

```python
def get_unseen_keywords(keywords: list[str], since_days: int = 7) -> list[str]:
    """Return keywords not yet searched in the last N days."""
```

#### A.4 Rate limiting (Phase 2+)

Redis key: `apify:runs:YYYY-MM-DD` → integer count. Hard cap: 10 actor runs/hour. Configurable via `APIFY_MAX_RUNS_PER_HOUR` in `.env`.

#### A.5 Error handling

- Retry failed actors up to 3 times with 60s backoff.
- On persistent failure: write `{actor_id, error, timestamp}` to `data/errors/` and continue with remaining steps.
- Never abort the full pipeline for a single actor failure.

---

### Module B — Processor (`processor/`)

#### B.1 Lead Scoring

**Input:** list of `Profile` objects enriched with engagement data  
**Output:** same profiles with `relevance_score`, `influence_score`, `overall_score`, `tier` (A/B/C)

```python
def score_profiles(profiles: list[Profile], niche_keywords: list[str]) -> list[Profile]:
```

**Scoring formula (v1, Phase 1):**

```
relevance   = tfidf_similarity(profile.headline + profile.about, niche_keywords)  # 0–1
influence   = min(profile.follower_count / 10000, 1.0)                            # 0–1, cap at 10k
recency     = 1.0 if last_activity < 14 days else 0.5 if < 30 days else 0.1
engagement  = min(profile.comment_word_count / 20, 1.0)                           # long comments = higher

overall = (relevance * 0.4) + (influence * 0.25) + (recency * 0.2) + (engagement * 0.15)
```

**Tier thresholds:**

| Tier | Score | Action |
|---|---|---|
| A | ≥ 0.65 | Connect + comment on their posts |
| B | 0.40–0.64 | Warm up (like, visit profile) |
| C | < 0.40 | Monitor only |

Thresholds configurable via `SCORING_TIER_A_THRESHOLD` in `.env`.

#### B.2 Deduplication

```python
def dedup_profiles(profiles: list[Profile]) -> list[Profile]:
    """Merge profiles by linkedin_urn. If URN absent, match on (full_name, company). 
    Aggregate engagement history across all matched records."""
```

#### B.3 Topic Graph (Phase 2)

```python
def extract_topics(posts: list[Post]) -> TopicGraph:
    """Run KeyBERT on post texts. Build co-occurrence network (NetworkX).
    Return trending, emerging, declining topic lists."""
```

**Output shape:**
```python
@dataclass
class TopicGraph:
    trending:  list[tuple[str, float]]   # (topic, score), sorted desc
    emerging:  list[tuple[str, float]]   # high velocity, lower absolute count
    declining: list[tuple[str, float]]   # appeared 2+ weeks ago, dropping
```

#### B.4 Influencer Mapping (Phase 2)

```python
def map_influencers(profiles: list[Profile]) -> list[InfluencerNode]:
    """For profiles with follower_count > INFLUENCER_THRESHOLD (default 5000),
    fetch followers via Apify. Compute Jaccard similarity between follower sets.
    Identify bridge accounts (high betweenness centrality in NetworkX graph)."""
```

---

### Module C — Content (`content/`)

#### C.1 Comment Generation

**Input:** post text, post author headline, niche context string, number of variants  
**Output:** list of comment strings

```python
def generate_comments(
    post_text: str,
    author_headline: str,
    niche: str,
    model: str,          # e.g. "gpt-4o-mini" — read from config
    n_variants: int = 3
) -> list[str]:
```

**Prompt structure:**

```
System: You are a LinkedIn ghostwriter for a thought leader in {niche}.
        Write comments that add genuine value — a data point, a contrarian view, or 
        a clarifying question. Max 2 sentences. No emoji overload. No generic praise.
        Return only the comment text, one per line.

User:   Post: "{post_text[:500]}"
        Author: {author_headline}
        
        Write {n_variants} comment variants.
```

**Guardrails (applied post-generation):**
- Strip comments longer than 280 characters
- Flag (don't discard) comments containing words in `COMMENT_BLOCKLIST` (configurable)
- Return all variants ranked by estimated engagement (heuristic: specificity + question presence)

#### C.2 Content Gap Analysis (Phase 2)

```python
def find_content_gaps(
    trending_topics: list[tuple[str, float]],
    user_post_history: list[Post],
    lookback_days: int = 30
) -> list[ContentIdea]:
```

**Output:**
```python
@dataclass
class ContentIdea:
    topic: str
    hook: str              # LLM-generated opening line
    format: str            # "text_post" | "carousel" | "poll" | "list"
    predicted_engagement: int
    gap_score: float       # how underserved this topic is in user's history
```

#### C.3 Connection Request Hooks (Phase 2)

```python
def generate_connection_hook(profile: Profile, context: str) -> list[str]:
    """Generate 2–3 personalised connection message variants.
    Context: shared post URL, comment they made, or mutual influencer."""
```

---

### Module D — Action Planner (`planner/`)

#### D.1 Daily Limits

| Action type | Default daily cap | Config key |
|---|---|---|
| Connection requests | 15 | `LIMIT_CONNECTIONS_PER_DAY` |
| Comments | 8 | `LIMIT_COMMENTS_PER_DAY` |
| Profile visits | 25 | `LIMIT_VISITS_PER_DAY` |
| Own posts suggested | 1 | `LIMIT_POST_IDEAS_PER_DAY` |

#### D.2 Prioritisation logic

```python
def build_daily_plan(
    posts: list[Post],
    profiles: list[Profile],
    comments: dict[str, list[str]],   # post_id → comment variants
    existing_actions: list[Action],    # already executed today
) -> DailyPlan:
```

**Priority order:**
1. Posts under 12 hours old (visibility window still open)
2. Tier A profiles not yet contacted
3. Follow-up on previous comments that received a reply
4. Tier B profiles (warm-up actions)

#### D.3 Output

See §9 for the full daily plan JSON schema.

---

## 6. Data Layer

### 6.1 SQLAlchemy models (shared across SQLite and PostgreSQL)

```python
# db/models.py

class Profile(Base):
    __tablename__ = "profiles"
    id                = Column(UUID, primary_key=True, default=uuid4)
    linkedin_urn      = Column(String(100), unique=True, nullable=True)
    full_name         = Column(String(200))
    headline          = Column(Text)
    follower_count    = Column(Integer)
    connection_count  = Column(Integer)
    last_activity_date = Column(Date)
    relevance_score   = Column(Float)
    influence_score   = Column(Float)
    overall_score     = Column(Float)
    tier              = Column(String(1))    # A / B / C
    last_seen_at      = Column(DateTime)
    created_at        = Column(DateTime, default=datetime.utcnow)

class Post(Base):
    __tablename__ = "posts"
    id                = Column(UUID, primary_key=True, default=uuid4)
    url               = Column(Text, unique=True)
    author_profile_id = Column(UUID, ForeignKey("profiles.id"))
    text              = Column(Text)
    likes_count       = Column(Integer)
    comments_count    = Column(Integer)
    posted_at         = Column(DateTime)
    scraped_at        = Column(DateTime, default=datetime.utcnow)

class Action(Base):
    __tablename__ = "actions"
    id             = Column(UUID, primary_key=True, default=uuid4)
    action_type    = Column(String(20))   # comment | connection | visit | post
    target_url     = Column(Text)
    target_profile_id = Column(UUID, ForeignKey("profiles.id"), nullable=True)
    suggested_text = Column(Text, nullable=True)
    status         = Column(String(20), default="suggested")  # suggested | executed | skipped | failed
    plan_date      = Column(Date)
    executed_at    = Column(DateTime, nullable=True)
    feedback       = Column(JSON, nullable=True)   # {"reply_received": true, "connection_accepted": false}
    created_at     = Column(DateTime, default=datetime.utcnow)

class ContentIdea(Base):
    __tablename__ = "content_ideas"
    id                   = Column(UUID, primary_key=True, default=uuid4)
    topic                = Column(Text)
    hook                 = Column(Text)
    format               = Column(String(50))
    predicted_engagement = Column(Integer)
    generated_at         = Column(DateTime, default=datetime.utcnow)
    used_at              = Column(DateTime, nullable=True)
```

### 6.2 Phase 1 shortcut

In Phase 1 use SQLite. In `db/session.py`:

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/engagement.db")
engine = create_engine(DATABASE_URL)
```

Switching to Postgres in Phase 2 requires only changing `DATABASE_URL` in `.env`.

### 6.3 Raw data storage

```
data/
  raw/
    {run_date}/
      post_search_{keyword}_{timestamp}.json
      post_detail_{post_id}_{timestamp}.json
      profiles_{batch_id}_{timestamp}.json
  plans/
    {YYYY-MM-DD}_plan.json
  errors/
    {timestamp}_{actor_id}_error.json
```

No S3 in Phase 1. The same folder structure maps directly to S3 prefixes in Phase 3.

---

## 7. LLM Integration

### 7.1 Provider: laozhang.ai

laozhang.ai exposes an OpenAI-compatible API endpoint. All LLM calls use the `openai` Python SDK pointed at the laozhang.ai base URL.

```python
# content/llm_client.py

from openai import OpenAI

client = OpenAI(
    api_key=os.environ["LAOZHANG_API_KEY"],
    base_url=os.environ["LAOZHANG_BASE_URL"],  # e.g. https://api.laozhang.ai/v1
)

def complete(
    prompt: str,
    system: str,
    model: str | None = None,
    max_tokens: int = 500,
    temperature: float = 0.7,
) -> str:
    model = model or os.environ["LLM_DEFAULT_MODEL"]
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()
```

### 7.2 Model selection

Set model per run context in `.env` or override as a CLI flag:

```
LLM_DEFAULT_MODEL=gpt-4o-mini
LLM_COMMENT_MODEL=gpt-4o-mini
LLM_HOOK_MODEL=gpt-3.5-turbo
```

All content functions accept an optional `model: str` parameter. If not provided, they fall back to the relevant `LLM_*_MODEL` env var.

### 7.3 Prompt files

Store all prompts as `.txt` files in `content/prompts/`. Never hardcode prompts in Python. Load with:

```python
PROMPT_DIR = Path(__file__).parent / "prompts"

def load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.txt").read_text()
```

This makes prompt iteration possible without touching Python code.

---

## 8. Apify Integration

### 8.1 Client wrapper

```python
# collector/apify_client.py

APIFY_BASE = "https://api.apify.com/v2"

def run_actor(actor_id: str, input_payload: dict, timeout_secs: int = 300) -> list[dict]:
    """
    Trigger actor, poll until finished (or timeout), return dataset items.
    Raises ApifyError on failure after MAX_RETRIES attempts.
    """
```

### 8.2 Actor input schemas

**Post search:**
```json
{
  "keywords": ["AI recruitment", "HR tech trends"],
  "maxPosts": 50,
  "sortBy": "engagement",
  "timeRange": "week"
}
```

**Post scraper (engagers):**
```json
{
  "postUrls": ["https://www.linkedin.com/posts/..."],
  "maxComments": 50,
  "includeLikes": true
}
```

**Profile scraper:**
```json
{
  "profileUrls": ["https://www.linkedin.com/in/..."],
  "includeAbout": true
}
```

**Follower scraper:**
```json
{
  "profileUrl": "https://www.linkedin.com/in/...",
  "maxFollowers": 500
}
```

> **Note:** These input schemas are based on the spec and Apify documentation. Validate against actual actor output in a manual test run before integrating. Actor output fields may differ — the normaliser layer in `collector/normaliser.py` is where you absorb those differences.

### 8.3 Output normalisation (key mappings to verify)

| Internal field | Expected Apify field | Notes |
|---|---|---|
| `post.url` | `postUrl` or `url` | Verify per actor |
| `post.likes_count` | `likesCount` or `stats.likes` | Often nested |
| `profile.linkedin_urn` | `profileId` or `urn` | May be absent |
| `profile.follower_count` | `followers` or `followersCount` | — |
| `engager.profile_url` | `authorUrl` or `profileUrl` | Inside comments array |

Map these in `normaliser.py` — do not assume field names without testing.

---

## 9. Daily Action Plan Format

### JSON schema

```json
{
  "date": "2026-06-10",
  "niche": "AI recruitment",
  "capacity": {
    "connections_remaining": 12,
    "comments_remaining": 6,
    "visits_remaining": 20
  },
  "actions": [
    {
      "action_id": "act_001",
      "type": "comment",
      "priority": 1,
      "url": "https://www.linkedin.com/posts/...",
      "post_preview": "First 100 chars of post text...",
      "author_name": "Jane Smith",
      "author_tier": "A",
      "deadline": "14:00 UTC",
      "suggested_text": [
        "Variant 1: ...",
        "Variant 2: ...",
        "Variant 3: ..."
      ],
      "status": "suggested"
    },
    {
      "action_id": "act_002",
      "type": "connection",
      "priority": 2,
      "url": "https://www.linkedin.com/in/...",
      "person_name": "John Doe",
      "person_headline": "Head of Talent at Acme",
      "tier": "A",
      "reason": "Commented on 2 posts in your niche this week",
      "suggested_message": [
        "Variant 1: ...",
        "Variant 2: ..."
      ],
      "status": "suggested"
    }
  ],
  "content_ideas": [
    {
      "topic": "Why ATS systems fail diverse candidates",
      "hook": "93% of applicants are rejected before a human reads their CV. Here's what the data actually shows.",
      "format": "text_post",
      "predicted_engagement": 120
    }
  ],
  "follow_ups": [
    {
      "action_id": "act_003",
      "type": "reply",
      "url": "https://...",
      "context": "Your comment received a reply 6 hours ago",
      "their_reply": "Preview of their reply text...",
      "suggested_reply": "..."
    }
  ]
}
```

The dashboard reads this file directly. Status updates from the dashboard write back to the same file and to the `actions` DB table.

---

## 10. Dashboard (Streamlit)

### Views

**Daily Plan tab** — main working view:
- Table of actions sorted by priority
- Each row: action type badge, person name (linked), post preview, suggested text (expandable), deadline
- Checkbox per action: `[ ] Suggested  [ ] Done  [ ] Skipped`
- "Copy text" button for comments/messages
- "Submit feedback" expander: `connection_accepted`, `reply_received`, `notes`

**Analytics tab** (Phase 2):
- Acceptance rate (connections sent vs accepted, rolling 14-day)
- Comment reply rate
- Daily plan completion rate
- Top-performing comment types

**Leads tab**:
- Filterable table of all profiles: tier, score, status
- Click row to see full profile detail + all interactions

### State management

```python
# dashboard/state.py
# Load plan JSON on startup. 
# All checkbox/feedback changes call update_action_status() immediately — 
# write to both the JSON file and the DB in a single transaction.
```

The dashboard must be stateless between reloads — all state lives in the DB and plan JSON, never in `st.session_state` alone.

### Running

```bash
streamlit run dashboard/app.py
```

No authentication in Phase 1. Phase 2+: use Streamlit's built-in `secrets.toml` password or expose only on `localhost` behind an SSH tunnel.

---

## 11. Project Structure

```
linkedin-engagement/
│
├── run_pipeline.py          # Main entry point — runs all steps in sequence
├── .env.example             # All required environment variables with comments
├── .env                     # Actual secrets — never commit
├── docker-compose.yml       # Phase 2+: Postgres, Redis, Dashboard
├── requirements.txt
│
├── collector/
│   ├── __init__.py
│   ├── apify_client.py      # Actor trigger, poll, download
│   ├── normaliser.py        # Raw JSON → internal objects
│   └── incremental.py       # Skip already-seen posts/profiles
│
├── processor/
│   ├── __init__.py
│   ├── scorer.py            # Lead scoring formula
│   ├── dedup.py             # Profile deduplication + merge
│   ├── topic_graph.py       # KeyBERT / YAKE + NetworkX (Phase 2)
│   └── influencer_map.py    # Follower graph analysis (Phase 2)
│
├── content/
│   ├── __init__.py
│   ├── llm_client.py        # laozhang.ai via openai SDK
│   ├── comment_gen.py       # Comment generation + guardrails
│   ├── gap_analysis.py      # Content gap analysis (Phase 2)
│   ├── hook_gen.py          # Connection request hooks (Phase 2)
│   └── prompts/
│       ├── comment_system.txt
│       ├── comment_user.txt
│       ├── hook_system.txt
│       └── gap_analysis.txt
│
├── planner/
│   ├── __init__.py
│   ├── daily_plan.py        # Prioritisation + limit enforcement
│   └── output.py            # Emit plan JSON + CSV
│
├── db/
│   ├── __init__.py
│   ├── models.py            # SQLAlchemy ORM models
│   ├── session.py           # Engine + session factory
│   └── migrations/          # Alembic (Phase 2)
│
├── dashboard/
│   ├── app.py               # Streamlit main app
│   ├── views/
│   │   ├── daily_plan.py
│   │   ├── analytics.py
│   │   └── leads.py
│   └── state.py             # Action status updates
│
├── data/
│   ├── raw/                 # Raw Apify JSON by date
│   ├── plans/               # Daily plan JSON files
│   └── errors/              # Failed actor run logs
│
└── tests/
    ├── test_scorer.py
    ├── test_normaliser.py
    └── fixtures/
        ├── sample_post_search.json
        ├── sample_post_scraper.json
        └── sample_profile_scraper.json
```

---

## 12. Environment & Configuration

### `.env.example`

```bash
# ── Apify ────────────────────────────────────────────────────────────
APIFY_API_TOKEN=apify_api_xxxxx

# Actor IDs — verify these match your Apify account
APIFY_ACTOR_POST_SEARCH=apify/linkedin-post-search
APIFY_ACTOR_POST_SCRAPER=apify/linkedin-post-scraper
APIFY_ACTOR_PROFILE_SCRAPER=apify/linkedin-profile-scraper
APIFY_ACTOR_FOLLOWER_SCRAPER=apify/linkedin-followers-scraper

# Max actor runs per hour (rate limiting)
APIFY_MAX_RUNS_PER_HOUR=10

# ── LLM (laozhang.ai) ────────────────────────────────────────────────
LAOZHANG_API_KEY=sk-xxxxx
LAOZHANG_BASE_URL=https://api.laozhang.ai/v1

LLM_DEFAULT_MODEL=gpt-4o-mini
LLM_COMMENT_MODEL=gpt-4o-mini
LLM_HOOK_MODEL=gpt-3.5-turbo

# ── Database ─────────────────────────────────────────────────────────
# Phase 1: SQLite (default, no setup required)
DATABASE_URL=sqlite:///./data/engagement.db

# Phase 2+: swap to Postgres
# DATABASE_URL=postgresql://app:password@localhost:5432/linkedin_engagement

# ── Redis (Phase 2+) ─────────────────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Pipeline settings ────────────────────────────────────────────────
SEED_KEYWORDS=AI recruitment,HR tech,talent acquisition
MAX_POSTS_PER_KEYWORD=50
MIN_ENGAGEMENT_THRESHOLD=50
ENGAGERS_PER_POST=50

# ── Scoring thresholds ────────────────────────────────────────────────
SCORING_TIER_A_THRESHOLD=0.65
SCORING_TIER_B_THRESHOLD=0.40
INFLUENCER_THRESHOLD=5000

# ── Daily action limits ────────────────────────────────────────────────
LIMIT_CONNECTIONS_PER_DAY=15
LIMIT_COMMENTS_PER_DAY=8
LIMIT_VISITS_PER_DAY=25

# ── Niche context (fed to LLM prompts) ───────────────────────────────
NICHE_DESCRIPTION=B2B SaaS recruitment tools for enterprise HR teams

# ── Output ───────────────────────────────────────────────────────────
PLANS_DIR=./data/plans
RAW_DATA_DIR=./data/raw
```

---

## 13. Portability Notes

The system is designed to move from local to cloud without code changes. All environment-specific values are in `.env`. The migration path:

| Concern | Local (Phase 1) | Cloud (Phase 3) |
|---|---|---|
| DB | `sqlite:///./data/engagement.db` | `postgresql://...` on RDS or managed Postgres |
| Storage | `./data/raw/` on disk | S3 bucket, same folder structure as key prefix |
| Scheduler | Manual CLI | Prefect deployment on same VM or Prefect Cloud |
| Dashboard | `localhost:8501` | `0.0.0.0:8501` behind Traefik, basic auth or VPN |
| Secrets | `.env` file | Docker secrets, AWS SSM, or HashiCorp Vault |

The only file that changes between local and cloud is `.env`.

When moving to cloud, replace the local `data/` directory references in `.env` (`RAW_DATA_DIR`, `PLANS_DIR`) with S3 URIs, and update `db/session.py` to handle S3 paths via `boto3` — or keep local-style paths on a mounted volume.

---

## 14. Developer Handoff Checklist

Before first code session:

- [ ] Apify account created and funded ($50 minimum recommended)
- [ ] Run each actor manually in the Apify console with sample inputs. Export output JSON and save to `tests/fixtures/`. These become your normaliser test cases.
- [ ] Confirm laozhang.ai API key works: run a test `curl` against `LAOZHANG_BASE_URL`
- [ ] Decide and record 5–10 seed keywords (stored in `SEED_KEYWORDS` in `.env`)
- [ ] Agree daily action caps with the business owner (connections, comments, visits)
- [ ] Confirm which `LLM_COMMENT_MODEL` to start with
- [ ] Python 3.11 installed locally (`pyenv` recommended)
- [ ] Run `pip install -r requirements.txt` — verify no dependency conflicts
- [ ] Run `python run_pipeline.py --dry-run` — should print steps without calling APIs

**Phase 1 done when:**
- [ ] Full pipeline runs end-to-end on real Apify data
- [ ] Daily plan JSON is generated with ≥5 suggested actions
- [ ] Dashboard loads the plan and records a "done" action to the DB
- [ ] No hardcoded values — everything via `.env`

---

*End of specification.*
