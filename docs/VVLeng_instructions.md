# VVLeng — Daily Usage Instructions

## Overview

VVLeng is a LinkedIn engagement pipeline. Each day it:

1. **Collects** LinkedIn posts matching your target keywords (via Apify)
2. **Generates** AI-written comment variants for each post (via LLM)
3. **Produces** a daily action plan — comments you can post manually on LinkedIn

Your job is to execute the plan: open each URL, review the suggested comments, and post them on LinkedIn.

---

## 1. Launch the Pipeline

Open a **terminal** (Command Prompt or PowerShell) and run:

```shell
cd d:\iFiles\DEV\VV\VV_Leng
python run_pipeline.py
```

This will:
- Search LinkedIn for posts matching your seed keywords
- Generate 3 comment variants per post
- Print the daily plan to the terminal and save it to `data\plans\`

---

## 2. Where to Find the Output

The plan is **printed directly to the terminal** as JSON.

It is also saved to a timestamped file:

```
data\plans\{date}_plan.json
```

Example: `data\plans\2026-06-14_plan.json`

You can open that file in any text editor to review the plan at your convenience.

---

## 3. Reading the Plan

The plan JSON has this structure:

```json
{
  "date": "2026-06-14",
  "niche": "Community Management Platform SaaS...",
  "capacity": {
    "connections_remaining": 15,
    "comments_remaining": 8,
    "visits_remaining": 25
  },
  "actions": [
    {
      "action_id": "act_001",
      "type": "comment",
      "priority": 2,
      "url": "https://www.linkedin.com/posts/...",
      "post_preview": "First ~80 chars of the post...",
      "author_name": "Author Name",
      "author_tier": "A",
      "deadline": "23:00 UTC",
      "suggested_text": [
        "Comment variant 1...",
        "Comment variant 2...",
        "Comment variant 3..."
      ],
      "status": "suggested"
    }
  ]
}
```

Key fields:

| Field | Meaning |
|-------|---------|
| `url` | Direct link to the LinkedIn post |
| `author_tier` | **A** = high-engagement target, **B** = medium, **C** = low |
| `priority` | **1** = do these first, **2** = do if you have capacity, **3** = optional |
| `suggested_text` | 3 AI-written comment variants — pick one (or write your own) |
| `capacity` | Your remaining daily budget for comments, connections, visits |

---

## 4. Your Daily Workflow (on LinkedIn)

For each action in the plan:

1. **Open the LinkedIn post** — copy the `url` and paste it into your browser
2. **Read the post** thoroughly so your comment feels natural in context
3. **Choose one** of the 3 suggested comments — or use them as inspiration to write your own
4. **Post the comment** on LinkedIn

**Tips:**
- Do **priority 1** actions first, then **priority 2**, then **priority 3**
- Stay within your daily comment limit (`capacity.comments_remaining`)
- The suggested comments are starting points — feel free to edit tone, length, or content
- Target **A-tier** authors first — they are most likely to engage back
- After posting, mentally decrement your remaining capacity for the day

---

## 5. Useful CLI Flags

| Flag | What it does |
|------|-------------|
| `--dry-run` | **Free test mode** — mocks Apify/LLM calls (no API keys needed, no cost) and prints the plan instead of saving |
| `--no-persist` | Print plan to terminal only — **do not save to file** (live Apify/LLM calls still happen, still costs money) |
| `--skip-collect` | **Skip Apify search** — reuse last fetched data. Saves API credits. |
| `--skip-llm` | **Skip LLM** — no comment generation. Just collect posts. |
| `--client <name>` | Run for a different client (e.g. `--client Joinee`) |
| `--keywords "term1,term2"` | Override search keywords for this run |

**Quick re-run** (reuses last data, just regenerates the plan, still costs LLM tokens):

```shell
python run_pipeline.py --skip-collect --no-persist
```

---

## 6. Track Your Daily Capacity

The plan header shows your remaining budget:

```json
"capacity": {
  "connections_remaining": 15,
  "comments_remaining": 8,
  "visits_remaining": 25
}
```

- After posting a comment, subtract 1 from `comments_remaining`
- The next daily run will reset all counters to full
- If you run the pipeline multiple times in one day, the capacity is **not** auto-adjusted — it always shows the configured daily max

---

## 7. Quick-Start Cheat Sheet

```
1. cd d:\iFiles\DEV\VV\VV_Leng
2. python run_pipeline.py
3. Copy the plan from terminal or open data\plans\{date}_plan.json
4. Open each URL on LinkedIn
5. Pick the best comment variant → paste → post
6. Repeat until you hit your daily comment limit
```

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `APIConnectionError` / LLM fails | API key missing or expired | Check `.env` has `LLM_API_KEY` set |
| `Actor run failed` / Apify error | API token missing or exhausted | Check `.env` has `APIFY_API_TOKEN` set |
| 0 posts collected | Keywords too narrow | Run with `--keywords "broader term"` |
| 0 actions planned | No high-scoring posts found | Try running again with fresh data |
| JSON parse errors in plan file | File corrupted | Delete the plan file and re-run |

---

*Last updated: 2026-06-14*