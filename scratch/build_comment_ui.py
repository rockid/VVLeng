"""Generate a single self-contained HTML 'comment runner' from the comment sheet.
No server, no install — double-click the .html to use. Captures which comment you
used per post and exports a feedback CSV.

    python scratch/build_comment_ui.py
"""
import csv, json, os, sys, io
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

today = date.today().isoformat()
src = f"data/Joinee/output/comment_sheet_{today}.csv"
if not os.path.exists(src):
    # fall back to most recent comment sheet
    import glob
    cands = sorted(glob.glob("data/Joinee/output/comment_sheet_*.csv"))
    src = cands[-1] if cands else src
out = src.replace("comment_sheet_", "comment_runner_").replace(".csv", ".html")

rows = list(csv.DictReader(open(src, encoding="utf-8")))
data = [{
    "rank": r.get("rank", ""),
    "author": r.get("author", ""),
    "tier": r.get("tier", ""),
    "rank_score": r.get("rank_score", ""),
    "gate_reason": r.get("gate_reason", ""),
    "url": r.get("post_url", ""),
    "post": r.get("post_text", ""),
    "confidence": r.get("top_confidence", ""),
    "top_reason": r.get("top_reason", ""),
    "comments": [r.get("comment_1", ""), r.get("comment_2", ""), r.get("comment_3", "")],
} for r in rows]

data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Comment Runner — __TITLE__</title>
<style>
  :root { --bg:#0f1115; --card:#1a1d24; --mut:#8b93a7; --acc:#4f8cff; --ok:#2ecc71; --skip:#e67e22; }
  * { box-sizing:border-box; }
  body { margin:0; font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif; background:var(--bg); color:#e6e9ef; }
  header { position:sticky; top:0; background:#11141b; padding:12px 18px; border-bottom:1px solid #262a33;
           display:flex; gap:16px; align-items:center; z-index:5; }
  header h1 { font-size:16px; margin:0; }
  .prog { color:var(--mut); }
  .btn { background:var(--acc); color:#fff; border:0; padding:8px 14px; border-radius:7px; cursor:pointer; font-size:14px; }
  .btn.secondary { background:#2a2f3a; }
  .wrap { max-width:860px; margin:18px auto; padding:0 16px; }
  .card { background:var(--card); border:1px solid #262a33; border-radius:12px; padding:16px; margin:0 0 16px; }
  .card.done { border-color:var(--ok); opacity:.6; }
  .card.skip { border-color:var(--skip); opacity:.55; }
  .meta { color:var(--mut); font-size:13px; margin-bottom:6px; }
  .author { font-weight:600; }
  .post { white-space:pre-wrap; background:#0c0e13; border:1px solid #20242d; border-radius:8px;
          padding:10px; max-height:140px; overflow:auto; font-size:13.5px; color:#c8cdd9; margin:8px 0 12px; }
  .variant { display:flex; gap:8px; align-items:flex-start; margin-bottom:8px; }
  .variant textarea { flex:1; background:#0c0e13; color:#e6e9ef; border:1px solid #20242d; border-radius:8px;
                      padding:8px; font:14px/1.45 inherit; resize:vertical; min-height:62px; }
  .variant textarea.used { border-color:var(--acc); }
  .copy { white-space:nowrap; }
  .actions { display:flex; gap:8px; margin-top:6px; }
  a.open { color:var(--acc); text-decoration:none; font-weight:600; }
  .tag { font-size:11px; padding:2px 7px; border-radius:6px; background:#2a2f3a; color:var(--mut); }
  .toppick { border:1px solid #2f3b52; background:#10151f; border-radius:8px; padding:10px; margin-top:10px; }
  .pickhdr { font-size:12.5px; color:#9fc1ff; margin-bottom:6px; font-weight:600; }
  details { margin-top:8px; }
  details summary { cursor:pointer; color:var(--mut); font-size:13px; padding:4px 0; }
  .conf5 { color:var(--ok); } .conf4 { color:#9fc1ff; } .conflow { color:var(--skip); }
</style></head><body>
<header>
  <h1>Comment Runner</h1>
  <span class="prog" id="prog"></span>
  <span style="flex:1"></span>
  <button class="btn secondary" onclick="resetAll()">Reset</button>
  <button class="btn" onclick="exportCsv()">Export feedback CSV</button>
</header>
<div class="wrap" id="list"></div>
<script>
const DATA = __DATA__;
const KEY = "comment_runner___TITLE__";
let state = JSON.parse(localStorage.getItem(KEY) || "{}");
function save(){ localStorage.setItem(KEY, JSON.stringify(state)); render(); }
function st(i){ return state[i] || {status:"", used:-1, text:""}; }

function copyVariant(i, v){
  const ta = document.getElementById(`ta_${i}_${v}`);
  ta.select(); document.execCommand("copy");
  const s = st(i); s.used = v; s.text = ta.value; state[i]=s; save();
}
function mark(i, status){
  const s = st(i); s.status = (s.status===status? "" : status); state[i]=s; save();
}
function resetAll(){ if(confirm("Clear all progress?")){ state={}; save(); } }

function render(){
  const list = document.getElementById("list");
  list.innerHTML = "";
  let done=0, skip=0;
  DATA.forEach((d,i)=>{
    const s = st(i);
    if(s.status==="done") done++; if(s.status==="skip") skip++;
    const card = document.createElement("div");
    card.className = "card" + (s.status? " "+s.status : "");
    card.innerHTML = `
      <div class="meta">#${d.rank} · <span class="tag">${d.tier}</span> · rank ${d.rank_score} · ${d.gate_reason||""}</div>
      <div class="author">${esc(d.author)}</div>
      <div class="post">${esc(d.post)}</div>
      <a class="open" href="${d.url}" target="_blank" rel="noopener">↗ Open post on LinkedIn</a>
      <div class="toppick">
        <div class="pickhdr">★ Top pick · <span class="${confClass(d.confidence)}">confidence ${d.confidence||'?'}/5</span>${d.top_reason? ' · '+esc(d.top_reason):''}</div>
        <div class="variant">
          <textarea id="ta_${i}_0" class="${s.used===0?'used':''}">${esc(d.comments[0]||'')}</textarea>
          <button class="btn copy" onclick="copyVariant(${i},0)">Copy${s.used===0?' ✓':''}</button>
        </div>
      </div>
      ${altCount(d)? `<details><summary>Show ${altCount(d)} alternative${altCount(d)>1?'s':''}</summary>
        ${d.comments.map((c,v)=> (v>=1 && c.trim())? `
          <div class="variant">
            <textarea id="ta_${i}_${v}" class="${s.used===v?'used':''}">${esc(c)}</textarea>
            <button class="btn copy" onclick="copyVariant(${i},${v})">Copy${s.used===v?' ✓':''}</button>
          </div>`:'').join("")}
      </details>`:''}
      <div class="actions">
        <button class="btn" style="background:${s.status==='done'?'#2ecc71':'#2a2f3a'}" onclick="mark(${i},'done')">✓ Done</button>
        <button class="btn" style="background:${s.status==='skip'?'#e67e22':'#2a2f3a'}" onclick="mark(${i},'skip')">Skip</button>
      </div>`;
    list.appendChild(card);
  });
  document.getElementById("prog").textContent = `${done} done · ${skip} skipped · ${DATA.length} total`;
}
function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
function altCount(d){ return d.comments.slice(1).filter(c=>c&&c.trim()).length; }
function confClass(c){ return c==='5'?'conf5': c==='4'?'conf4': c?'conflow':''; }

function exportCsv(){
  const head = ["rank","status","variant_used","used_text","post_url","author","exported_at"];
  const ts = new Date().toISOString();
  const lines = [head.join(",")];
  DATA.forEach((d,i)=>{ const s=st(i); if(!s.status) return;
    const row = [d.rank, s.status, s.used>=0? s.used+1 : "", s.text||"", d.url, d.author, ts]
      .map(x=>`"${String(x).replace(/"/g,'""')}"`).join(",");
    lines.push(row);
  });
  const blob = new Blob([lines.join("\\n")], {type:"text/csv"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "commented_log___TITLE__.csv";
  a.click();
}
render();
</script></body></html>"""

html = HTML.replace("__DATA__", data_json).replace("__TITLE__", today)
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Built {out}  ({len(data)} posts)")
