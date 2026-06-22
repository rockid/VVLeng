"""Quick content-topic generator: mine the existing VVLeng corpus for high-engagement
niche posts and synthesize original LinkedIn post topics for the operator to publish.

One local filter + one LLM ideation call. No Apify, no embeddings.
    python scratch/topic_ideas.py
"""
import glob, json, os, sys, io, re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from config_loader import load_config, build_niche_prompt_context
from collector.normaliser import normalise_posts
from processor.post_scorer import _noise_reason
from content.llm_client import complete

config = load_config(client_id_override="Joinee")

raw_path = max(glob.glob("data/Joinee/raw/posts_*.json"), key=os.path.getmtime)
posts = normalise_posts(json.load(open(raw_path, encoding="utf-8")))

# Filter to substantive, non-noise posts; rank by engagement (comments weighted up:
# discussion is a stronger "worth writing about" signal than passive likes).
clean = []
for p in posts:
    text = (p.get("text") or "").strip()
    if len(text) < 220:
        continue
    if _noise_reason(text):
        continue
    eng = (p.get("likes_count", 0) or 0) + 3 * (p.get("comments_count", 0) or 0)
    if eng < 20:
        continue
    p["_eng"] = eng
    clean.append(p)

clean.sort(key=lambda p: p["_eng"], reverse=True)
top = clean[:40]
print(f"Corpus {len(posts)} -> {len(clean)} substantive/on-niche -> top {len(top)} by engagement\n")

block = "\n\n".join(
    f"[{i}] ({p['_eng']} eng | {p.get('likes_count',0)}L {p.get('comments_count',0)}C) "
    f"{(p.get('author_headline') or p.get('author_name') or '')[:50]}\n{(p.get('text') or '')[:380]}"
    for i, p in enumerate(top, 1)
)

system = (
    "You are a sharp B2B LinkedIn content strategist for the company below.\n\n"
    + build_niche_prompt_context(config.client.niche)
    + "\n\nYou will see the highest-engagement LinkedIn posts from our niche this week, with "
    "like (L) and comment (C) counts. Identify the TOPICS driving engagement that would make "
    "strong ORIGINAL posts for US to publish.\n\n"
    "Pick exactly 5 DISTINCT topics (different themes, not variations of one). Favor topics that are:\n"
    "- currently resonating (point to evidence in the posts)\n"
    "- under-served by quality voices (white space), not generic/saturated\n"
    "- squarely relevant to our ICP and product POV\n"
    "- ones we can credibly own\n"
    "Do NOT invent statistics. Base 'why_now' on what is actually visible in the posts.\n\n"
    "Return ONLY a JSON array of 5 objects, no markdown, no preamble:\n"
    '{"topic": "...", "why_now": "<evidence from the posts>", '
    '"our_angle": "<our distinct POV tied to our product/ICP>", '
    '"hook": "<a scroll-stopping opening line we could literally post>", '
    '"format": "text_post|carousel|poll|story"}'
)

raw = complete(prompt="Posts:\n\n" + block, system=system,
               model=config.llm.comment_model, max_tokens=1600, temperature=0.5, config=config)

s = raw[raw.find("["): raw.rfind("]") + 1]
s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
s = s.replace('\\"', '"')             # model wrapped some values in escaped quotes
s = re.sub(r",\s*([}\]])", r"\1", s)  # drop trailing commas
try:
    ideas = json.loads(s)
except json.JSONDecodeError:
    # Per-object fallback: extract each {...} block individually
    ideas = []
    for m in re.findall(r"\{[^{}]*\}", s, re.S):
        try:
            ideas.append(json.loads(m))
        except json.JSONDecodeError:
            pass
    if not ideas:
        print("RAW MODEL OUTPUT (parse failed):\n", raw[:1500])
        sys.exit(1)

for i, t in enumerate(ideas, 1):
    print("=" * 92)
    print(f"TOPIC {i}: {t.get('topic','')}")
    print(f"  Why now : {t.get('why_now','')}")
    print(f"  Angle   : {t.get('our_angle','')}")
    print(f"  Hook    : {t.get('hook','')}")
    print(f"  Format  : {t.get('format','')}")

out = f"data/Joinee/output/topic_ideas_{__import__('datetime').date.today().isoformat()}.json"
json.dump(ideas, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\nSaved {len(ideas)} topics to {out}")
