#!/usr/bin/env python3
"""
Generate annotated UX-review reports from a findings JSON file.

Supports single-page OR multi-page reports (see references/report-schema.md).
Produces:
  - report.html  : interactive (page switcher, breakpoint tabs, box overlays, agree/disagree, comments)
  - report.md    : Markdown (one chapter per page)
  - report.pdf   : shareable PDF (headless Edge/Chrome print; reportlab fallback)
  - <page>-<bp>px-annotated.png : screenshots with bounding boxes burned in (needs Pillow)

Usage:
  python generate_report.py --findings findings.json --screenshots-dir . --out-dir ux-report
  python generate_report.py --findings findings.json --format html,md,png,pdf
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SEVERITY_COLORS = {"critical": "#e5484d", "high": "#f5a524", "medium": "#3b82f6", "low": "#8b8d98"}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SEVERITY_RGB = {"critical": (229, 72, 77), "high": (245, 165, 36),
                "medium": (59, 130, 246), "low": (139, 141, 152)}


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return s or "page"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_pages(data: dict) -> list:
    """Return a list of page dicts. A single-page findings file (top-level
    screenshots+findings, no `pages`) is wrapped into one page for back-compat."""
    if data.get("pages"):
        pages = [dict(p) for p in data["pages"]]
    else:
        wrap = {
            "name": data.get("title", "Page"),
            "url": data.get("url", ""),
            "screenshots": data.get("screenshots", {}),
            "findings": data.get("findings", []),
        }
        # Carry over explicit overall verdict/summary so the cover and the
        # single page never disagree.
        if data.get("verdict"):
            wrap["verdict"] = data["verdict"]
        if data.get("summary"):
            wrap["summary"] = data["summary"]
        pages = [wrap]
    for p in pages:
        p.setdefault("findings", [])
        p["findings"].sort(
            key=lambda f: (SEVERITY_ORDER.get(f.get("severity", "low"), 9), f.get("id", "")))
        for i, f in enumerate(p["findings"]):
            f["n"] = i + 1
        p["slug"] = slugify(p.get("name", "page"))
        p.setdefault("summary", count_summary(p["findings"]))
        p.setdefault("verdict", derive_verdict(p["findings"]))
    return pages


def count_summary(findings: list) -> dict:
    c = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        c[f["severity"]] = c.get(f["severity"], 0) + 1
    return c


def derive_verdict(findings: list) -> str:
    c = count_summary(findings)
    if c["critical"] or c["high"] >= 4:
        return "BLOCK"
    if c["high"]:
        return "SHIP WITH FIXES"
    return "SHIP"


def overall_verdict(pages: list) -> str:
    order = {"BLOCK": 0, "SHIP WITH FIXES": 1, "SHIP": 2}
    return min((p["verdict"] for p in pages), key=lambda v: order.get(v, 1), default="SHIP")


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


# ----------------------------------------------------------------------------- annotated PNG

def generate_pngs(pages: list, shots_dir: Path, out_dir: Path) -> dict:
    """Burn numbered boxes into each page's screenshots. Returns {page_slug: {bp: filename}}."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  Pillow not installed - skipping annotated PNGs (HTML report still has overlays)",
              file=sys.stderr)
        return {}
    try:
        font = ImageFont.truetype("arialbd.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    out = {}
    for page in pages:
        by_bp = {}
        for f in page["findings"]:
            # A box is valid only for the one breakpoint it was measured at (the first
            # listed). Drawing it on other breakpoints would misplace it, since the same
            # element sits at a different position per breakpoint.
            primary_bp = str(f.get("breakpoint", "")).split(",")[0].strip()
            by_bp.setdefault(primary_bp, []).append(f)
        page_out = {}
        for bp, fname in (page.get("screenshots") or {}).items():
            src = shots_dir / fname
            items = [f for f in by_bp.get(str(bp), []) if f.get("box")]
            if not src.exists() or not items:
                continue
            img = Image.open(src).convert("RGBA")
            draw = ImageDraw.Draw(img)
            for f in items:
                b = f["box"]
                col = SEVERITY_RGB.get(f["severity"], (139, 141, 152))
                x, y, w, h = b["x"], b["y"], b["w"], b["h"]
                draw.rectangle([x, y, x + w, y + h], outline=col, width=3)
                n, r, cx, cy = str(f["n"]), 15, x - 2, y - 2
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
                tb = draw.textbbox((0, 0), n, font=font)
                draw.text((cx - (tb[2] - tb[0]) / 2, cy - (tb[3] - tb[1]) / 2 - tb[1]),
                          n, fill=(255, 255, 255), font=font)
            name = f"{page['slug']}-{bp}px-annotated.png"
            img.convert("RGB").save(out_dir / name)
            page_out[str(bp)] = name
            print(f"  wrote {out_dir / name}")
        out[page["slug"]] = page_out
    return out


def crop_finding(page: dict, f: dict, shots_dir: Path, pad: int = 70):
    """Crop a screenshot to a band around a finding's box, draw the box + number.
    Returns (PIL.Image, source_width) or (None, 0). Full-page mobile screenshots are
    far too tall to embed whole in a PDF (they span several pages and read poorly), so
    we show a short, focused, captioned crop per finding instead."""
    if not f.get("box"):
        return None, 0
    bp = str(f.get("breakpoint", "")).split(",")[0].strip()
    fname = (page.get("screenshots") or {}).get(bp)
    if not fname:
        return None, 0
    src = shots_dir / fname
    if not src.exists():
        return None, 0
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None, 0
    img = Image.open(src).convert("RGB")
    W, H = img.size
    b = f["box"]
    top = max(0, b["y"] - pad)
    bot = min(H, b["y"] + b["h"] + pad)
    crop = img.crop((0, top, W, bot))
    draw = ImageDraw.Draw(crop)
    col = SEVERITY_RGB.get(f["severity"], (139, 141, 152))
    x, y, w, h = b["x"], b["y"] - top, b["w"], b["h"]
    draw.rectangle([x, y, x + w, y + h], outline=col, width=3)
    try:
        font = ImageFont.truetype("arialbd.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
    n, r, cx, cy = str(f["n"]), 13, max(13, x - 1), max(13, y - 1)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    tb = draw.textbbox((0, 0), n, font=font)
    draw.text((cx - (tb[2] - tb[0]) / 2, cy - (tb[3] - tb[1]) / 2 - tb[1]), n,
              fill=(255, 255, 255), font=font)
    return crop, W


# ----------------------------------------------------------------------------- interactive HTML

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>__TITLE__</title>
<style>
  :root{--critical:#e5484d;--high:#f5a524;--medium:#3b82f6;--low:#8b8d98;
    --bg:#0e0f13;--panel:#171922;--card:#1e212b;--border:#2a2e3a;--text:#e8eaf0;--muted:#9598a6;--accent:#3b82f6;}
  *{box-sizing:border-box;} body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    background:var(--bg);color:var(--text);font-size:14px;line-height:1.5;}
  header{position:sticky;top:0;z-index:50;background:var(--panel);border-bottom:1px solid var(--border);padding:12px 20px;}
  .head-row{display:flex;align-items:center;gap:16px;flex-wrap:wrap;}
  h1{font-size:16px;margin:0;font-weight:600;} .url{color:var(--muted);font-size:12px;word-break:break-all;}
  .verdict{padding:4px 12px;border-radius:999px;font-weight:600;font-size:12px;letter-spacing:.3px;}
  .verdict.ship{background:#1c3829;color:#4ade80;} .verdict.fixes{background:#3a2f17;color:#fbbf24;}
  .verdict.block{background:#3a1d20;color:#f87171;}
  .counts{display:flex;gap:8px;} .pill{padding:3px 9px;border-radius:6px;font-size:12px;font-weight:600;color:#fff;}
  .tabs{display:flex;gap:6px;} .tab{padding:6px 12px;border-radius:7px;border:1px solid var(--border);
    background:transparent;color:var(--muted);cursor:pointer;font-size:12px;font-weight:600;}
  .tab.active{background:var(--accent);color:#fff;border-color:var(--accent);}
  .export{padding:7px 14px;border-radius:7px;border:1px solid var(--accent);background:transparent;
    color:var(--accent);cursor:pointer;font-weight:600;font-size:12px;} .export:hover{background:var(--accent);color:#fff;}
  .pagebar{display:flex;gap:6px;flex-wrap:wrap;padding:10px 20px;background:#11131a;border-bottom:1px solid var(--border);}
  .ptab{display:flex;align-items:center;gap:7px;padding:7px 13px;border-radius:8px;border:1px solid var(--border);
    background:transparent;color:var(--text);cursor:pointer;font-size:12.5px;font-weight:600;}
  .ptab.active{border-color:var(--accent);background:#10243f;} .dot{width:8px;height:8px;border-radius:50%;}
  main{display:flex;align-items:flex-start;} .viewer{flex:1;padding:20px;overflow:auto;height:calc(100vh-118px);
    position:sticky;top:118px;text-align:center;} .img-wrap{position:relative;display:inline-block;
    box-shadow:0 8px 40px rgba(0,0,0,.5);border-radius:6px;overflow:hidden;}
  .img-wrap img{display:block;max-width:100%;height:auto;}
  .box{position:absolute;border:2px solid;border-radius:3px;cursor:pointer;transition:box-shadow .12s;}
  .box:hover,.box.active{box-shadow:0 0 0 3px rgba(255,255,255,.25);z-index:2;}
  .box .marker{position:absolute;top:-11px;left:-11px;width:22px;height:22px;border-radius:50%;color:#fff;
    font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,.4);}
  aside{width:400px;flex-shrink:0;padding:18px 20px 60px;height:calc(100vh-118px);overflow-y:auto;border-left:1px solid var(--border);}
  .group-label{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);margin:16px 0 8px;font-weight:700;}
  .finding{background:var(--card);border:1px solid var(--border);border-left-width:3px;border-radius:9px;
    padding:13px 14px;margin-bottom:10px;scroll-margin-top:130px;}
  .finding.active{box-shadow:0 0 0 2px var(--accent);}
  .f-head{display:flex;align-items:center;gap:9px;cursor:pointer;}
  .f-num{width:22px;height:22px;border-radius:50%;color:#fff;font-size:12px;font-weight:700;display:flex;
    align-items:center;justify-content:center;flex-shrink:0;} .f-title{font-weight:600;font-size:13.5px;}
  .f-meta{color:var(--muted);font-size:11.5px;margin:7px 0 0;} .f-body{font-size:12.5px;margin-top:8px;display:none;}
  .finding.open .f-body{display:block;} .f-body p{margin:6px 0;} .f-body .label{color:var(--muted);font-weight:600;}
  .f-body code{background:#0c0d11;padding:1px 5px;border-radius:4px;font-size:11.5px;}
  .votes{display:flex;gap:8px;margin-top:10px;} .vote{flex:1;padding:6px;border-radius:6px;border:1px solid var(--border);
    background:transparent;color:var(--muted);cursor:pointer;font-size:12px;font-weight:600;}
  .vote.agree.on{background:#1c3829;color:#4ade80;border-color:#1c5837;}
  .vote.disagree.on{background:#3a1d20;color:#f87171;border-color:#5a2a2e;}
  textarea{width:100%;margin-top:8px;background:#0c0d11;border:1px solid var(--border);border-radius:6px;
    color:var(--text);padding:7px;font-size:12px;font-family:inherit;resize:vertical;min-height:34px;}
</style></head><body>
<header><div class="head-row">
  <div><h1>__TITLE__</h1><div class="url">__TIMESTAMP__</div></div>
  <span class="verdict __VERDICT_CLASS__">__VERDICT__</span>
  <div class="counts" id="counts"></div>
  <div class="tabs" id="bptabs" style="margin-left:auto"></div>
  <button class="export" onclick="exportFeedback()">&#11015; Export feedback</button>
</div></header>
<div class="pagebar" id="pagebar"></div>
<main>
  <div class="viewer"><div class="img-wrap"><img id="shot" alt="screenshot"><div id="overlay"></div></div></div>
  <aside id="panel"></aside>
</main>
<script>
const DATA = __DATA__;
const IMAGES = __IMAGES__;   // [ {bp: dataURI}, ... ] indexed by page
const COLORS = {critical:"#e5484d",high:"#f5a524",medium:"#3b82f6",low:"#8b8d98"};
let pageIdx = 0, currentBp = null;
let feedback = JSON.parse(localStorage.getItem("vux_"+DATA.title) || "{}");

const page = () => DATA.pages[pageIdx];
const bps = () => Object.keys(IMAGES[pageIdx] || {}).sort((a,b)=>Number(a)-Number(b));
const esc = s => String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const vClass = v => v==="SHIP"?"ship":(v==="BLOCK"?"block":"fixes");

function renderPageBar(){
  if(DATA.pages.length < 2){ document.getElementById("pagebar").style.display="none"; return; }
  document.getElementById("pagebar").innerHTML = DATA.pages.map((p,i)=>
    `<button class="ptab ${i===pageIdx?'active':''}" onclick="selectPage(${i})">
       <span class="dot" style="background:${p.verdict==='SHIP'?'#4ade80':(p.verdict==='BLOCK'?'#f87171':'#fbbf24')}"></span>
       ${esc(p.name)}</button>`).join("");
}
function renderCounts(){
  const c = page().summary || {};
  document.getElementById("counts").innerHTML = ["critical","high","medium","low"]
    .filter(s=>c[s]>0).map(s=>`<span class="pill" style="background:${COLORS[s]}">${c[s]} ${s}</span>`).join("");
}
function renderBpTabs(){
  document.getElementById("bptabs").innerHTML = bps().map(bp=>
    `<button class="tab" data-bp="${bp}" onclick="selectBp('${bp}')">${bp}px</button>`).join("");
}
function selectPage(i){ pageIdx=i; renderPageBar(); renderCounts(); renderBpTabs(); selectBp(bps()[0]); }
function selectBp(bp){
  currentBp=bp;
  document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("active",t.dataset.bp===bp));
  const img=document.getElementById("shot"); img.onload=renderBoxes; img.src=IMAGES[pageIdx][bp];
  renderPanel();
}
function inBp(f){ return String(f.breakpoint).split(",").map(s=>s.trim()).includes(currentBp); }
function primaryBp(f){ return String(f.breakpoint).split(",")[0].trim(); }
function renderBoxes(){
  const img=document.getElementById("shot"), overlay=document.getElementById("overlay");
  const nw=img.naturalWidth, nh=img.naturalHeight; overlay.innerHTML="";
  // Draw a box only on the breakpoint it was measured at (the first listed) — an element
  // is at a different position per breakpoint, so reusing one box elsewhere misplaces it.
  page().findings.filter(f=>f.box && primaryBp(f)===currentBp).forEach(f=>{
    const d=document.createElement("div"); d.className="box"; d.id="box-"+f.id;
    d.style.left=(f.box.x/nw*100)+"%"; d.style.top=(f.box.y/nh*100)+"%";
    d.style.width=(f.box.w/nw*100)+"%"; d.style.height=(f.box.h/nh*100)+"%";
    d.style.borderColor=COLORS[f.severity];
    d.innerHTML=`<span class="marker" style="background:${COLORS[f.severity]}">${f.n}</span>`;
    d.onclick=()=>focusFinding(f.id); overlay.appendChild(d);
  });
}
function renderPanel(){
  let html="", last=null;
  page().findings.forEach(f=>{
    if(f.severity!==last){ html+=`<div class="group-label">${f.severity}</div>`; last=f.severity; }
    const fb=feedback[page().slug+":"+f.id]||{};
    html+=`<div class="finding" id="find-${f.id}" style="border-left-color:${COLORS[f.severity]};${inBp(f)?'':'opacity:.55'}">
      <div class="f-head" onclick="toggleFinding('${f.id}')">
        <span class="f-num" style="background:${COLORS[f.severity]}">${f.n}</span>
        <span class="f-title">${esc(f.title)}</span></div>
      <div class="f-meta">${esc(f.element||"")} &middot; ${f.breakpoint}px</div>
      <div class="f-body">
        <p><span class="label">Issue:</span> ${esc(f.issue||"")}</p>
        ${f.evidence?`<p><span class="label">Evidence:</span> <code>${esc(f.evidence)}</code></p>`:""}
        ${f.fix?`<p><span class="label">Fix:</span> ${esc(f.fix)}</p>`:""}
        <div class="votes">
          <button class="vote agree ${fb.vote==='agree'?'on':''}" onclick="vote('${f.id}','agree',event)">&#128077; Agree</button>
          <button class="vote disagree ${fb.vote==='disagree'?'on':''}" onclick="vote('${f.id}','disagree',event)">&#128078; Disagree</button>
        </div>
        <textarea placeholder="Your comment..." oninput="comment('${f.id}',this.value)">${esc(fb.comment||"")}</textarea>
      </div></div>`;
  });
  document.getElementById("panel").innerHTML=html;
}
function toggleFinding(id){ document.getElementById("find-"+id).classList.toggle("open"); }
function focusFinding(id){
  const card=document.getElementById("find-"+id); card.classList.add("open");
  document.querySelectorAll(".finding").forEach(c=>c.classList.remove("active"));
  document.querySelectorAll(".box").forEach(b=>b.classList.remove("active"));
  card.classList.add("active"); const box=document.getElementById("box-"+id); if(box) box.classList.add("active");
  card.scrollIntoView({behavior:"smooth",block:"center"});
}
function vote(id,v,e){ e.stopPropagation(); const k=page().slug+":"+id;
  feedback[k]=feedback[k]||{}; feedback[k].vote=feedback[k].vote===v?null:v; save(); renderPanel(); }
function comment(id,val){ const k=page().slug+":"+id; feedback[k]=feedback[k]||{}; feedback[k].comment=val; save(); }
function save(){ localStorage.setItem("vux_"+DATA.title, JSON.stringify(feedback)); }
function exportFeedback(){
  const out={title:DATA.title,timestamp:DATA.timestamp,reviews:[]};
  DATA.pages.forEach(p=>p.findings.forEach(f=>{ const fb=feedback[p.slug+":"+f.id]||{};
    out.reviews.push({page:p.name,id:f.id,title:f.title,severity:f.severity,vote:fb.vote||null,comment:fb.comment||""});}));
  const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{type:"application/json"}));
  a.download="ux-review-feedback.json"; a.click();
}
renderPageBar(); selectPage(0);
</script></body></html>
"""


def generate_html(data: dict, pages: list, images_per_page: list, out_path: Path) -> None:
    verdict = data["verdict"]
    payload = {"title": data.get("title", "Visual UX Review"),
               "timestamp": data.get("timestamp", ""),
               "verdict": verdict,
               "pages": [{"name": p["name"], "url": p.get("url", ""), "slug": p["slug"],
                          "verdict": p["verdict"], "summary": p["summary"],
                          "findings": p["findings"]} for p in pages]}
    html = (HTML_TEMPLATE
            .replace("__TITLE__", data.get("title", "Visual UX Review"))
            .replace("__TIMESTAMP__", data.get("timestamp", ""))
            .replace("__VERDICT_CLASS__", "ship" if verdict == "SHIP" else ("block" if verdict == "BLOCK" else "fixes"))
            .replace("__VERDICT__", verdict)
            .replace("__DATA__", json.dumps(payload))
            .replace("__IMAGES__", json.dumps(images_per_page)))
    out_path.write_text(html, encoding="utf-8")
    print(f"  wrote {out_path}")


# ----------------------------------------------------------------------------- markdown

def generate_md(data: dict, pages: list, png_map: dict, out_path: Path) -> None:
    L = []
    L.append(f"# {data.get('title', 'Visual UX Review')}\n")
    L.append(f"**Date:** {data.get('timestamp', '')}  ")
    L.append(f"**Overall verdict:** {data['verdict']}\n")
    if len(pages) > 1:
        L.append("| Page | Verdict | Critical | High | Medium | Low |")
        L.append("|------|---------|----------|------|--------|-----|")
        for p in pages:
            s = p["summary"]
            L.append(f"| {p['name']} | {p['verdict']} | {s['critical']} | {s['high']} | {s['medium']} | {s['low']} |")
        L.append("")
    for p in pages:
        L.append(f"\n## {p['name']}\n")
        L.append(f"**URL:** {p.get('url', '')}  ")
        L.append(f"**Verdict:** {p['verdict']}\n")
        by = {}
        for f in p["findings"]:
            by.setdefault(f["severity"], []).append(f)
        for sev in ("critical", "high", "medium", "low"):
            for f in by.get(sev, []):
                L.append(f"### [{f.get('id', '')}] {f.get('title', '')} ({sev})")
                L.append(f"- **Element:** {f.get('element', '')}")
                L.append(f"- **Breakpoint:** {f.get('breakpoint', '')}px")
                L.append(f"- **Issue:** {f.get('issue', '')}")
                if f.get("evidence"):
                    L.append(f"- **Evidence:** `{f['evidence']}`")
                if f.get("fix"):
                    L.append(f"- **Fix:** {f['fix']}")
                L.append("")
        for bp, name in sorted((png_map.get(p["slug"]) or {}).items(), key=lambda kv: int(kv[0])):
            L.append(f"- Annotated {bp}px: `{name}`")
    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"  wrote {out_path}")


# ----------------------------------------------------------------------------- PDF

PRINT_CSS = r"""
@page{size:A4;margin:14mm;}
*{box-sizing:border-box;} body{font-family:-apple-system,"Segoe UI",Roboto,sans-serif;color:#1a1c22;font-size:11px;margin:0;}
.cover h1{font-size:22px;margin:0 0 4px;} .cover .sub{color:#666;font-size:12px;margin-bottom:14px;}
.vbadge{display:inline-block;padding:5px 14px;border-radius:999px;font-weight:700;font-size:12px;}
.vbadge.ship{background:#dcfce7;color:#166534;} .vbadge.fixes{background:#fef3c7;color:#92400e;}
.vbadge.block{background:#fee2e2;color:#991b1b;}
table{border-collapse:collapse;width:100%;margin:16px 0;font-size:11px;}
th,td{border:1px solid #ddd;padding:6px 9px;text-align:left;} th{background:#f5f5f7;}
.page-sec{page-break-before:always;} h2{font-size:16px;border-bottom:2px solid #eee;padding-bottom:5px;margin:0 0 3px;}
.purl{color:#666;font-size:10px;word-break:break-all;} .psum{font-size:10px;color:#555;margin:2px 0 12px;}
.grp{font-size:9px;text-transform:uppercase;letter-spacing:.6px;color:#888;font-weight:700;margin:12px 0 6px;}
.fcard{display:flex;gap:12px;align-items:flex-start;page-break-inside:avoid;border:1px solid #e5e5e5;
  border-left:4px solid;border-radius:8px;padding:10px 12px;margin-bottom:9px;}
.fcard.stack{display:block;}
.crop{flex:0 0 72mm;} .crop img{width:100%;border:1px solid #ddd;border-radius:4px;display:block;}
.stack .crop{margin-bottom:7px;} .stack .crop img{width:auto;max-width:100%;max-height:120mm;}
.cap{font-size:8.5px;font-style:italic;color:#777;margin-top:3px;line-height:1.3;}
.txt{flex:1;min-width:0;} .ph{display:flex;align-items:center;gap:8px;}
.pnum{width:20px;height:20px;border-radius:50%;color:#fff;font-size:11px;font-weight:700;display:flex;
  align-items:center;justify-content:center;flex-shrink:0;}
.pt{font-weight:700;font-size:12px;} .pm{color:#777;font-size:10px;margin:4px 0 6px;}
.txt p{margin:3px 0;font-size:10.5px;} .lbl{font-weight:700;color:#555;}
code{background:#f2f2f4;padding:1px 4px;border-radius:3px;word-break:break-word;}
"""


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_print_html(data: dict, pages: list, shots_dir: Path) -> str:
    import io
    vmap = {"SHIP": "ship", "SHIP WITH FIXES": "fixes", "BLOCK": "block"}

    def crop_uri(page, f):
        crop, sw = crop_finding(page, f, shots_dir)
        if crop is None:
            return None, 0
        buf = io.BytesIO()
        crop.save(buf, "PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"), sw

    def card(page, f):
        col = SEVERITY_COLORS[f["severity"]]
        ev = f'<p><span class="lbl">Evidence:</span> <code>{_esc(f["evidence"])}</code></p>' if f.get("evidence") else ""
        fix = f'<p><span class="lbl">Fix:</span> {_esc(f["fix"])}</p>' if f.get("fix") else ""
        txt = (f'<div class="txt"><div class="ph"><span class="pnum" style="background:{col}">{f["n"]}</span>'
               f'<span class="pt">{_esc(f["title"])}</span></div>'
               f'<div class="pm">{_esc(f.get("element",""))} &middot; {f.get("breakpoint","")}px &middot; {f["severity"]}</div>'
               f'<p><span class="lbl">Issue:</span> {_esc(f.get("issue",""))}</p>{ev}{fix}</div>')
        uri, sw = crop_uri(page, f)
        if uri:
            cap = f'<div class="cap">[{f["n"]}] {_esc(f.get("element",""))} &mdash; {f["breakpoint"]}px</div>'
            crop_html = f'<div class="crop"><img src="{uri}">{cap}</div>'
            cls = "fcard stack" if sw >= 600 else "fcard"   # wide desktop crops stack above text
            return f'<div class="{cls}" style="border-left-color:{col}">{crop_html}{txt}</div>'
        return f'<div class="fcard" style="border-left-color:{col}">{txt}</div>'

    parts = [f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{PRINT_CSS}</style></head><body>']
    parts.append(f'<div class="cover"><h1>{_esc(data.get("title","Visual UX Review"))}</h1>'
                 f'<div class="sub">{_esc(data.get("timestamp",""))}</div>'
                 f'<span class="vbadge {vmap.get(data["verdict"],"fixes")}">{data["verdict"]}</span>')
    parts.append('<table><tr><th>Page</th><th>Verdict</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th></tr>')
    for p in pages:
        s = p["summary"]
        parts.append(f'<tr><td>{_esc(p["name"])}</td><td>{p["verdict"]}</td>'
                     f'<td>{s["critical"]}</td><td>{s["high"]}</td><td>{s["medium"]}</td><td>{s["low"]}</td></tr>')
    parts.append('</table></div>')

    for p in pages:
        s = p["summary"]
        sline = " &middot; ".join(f"{s[k]} {k}" for k in ("critical", "high", "medium", "low") if s[k])
        parts.append(f'<div class="page-sec"><h2>{_esc(p["name"])}</h2>'
                     f'<div class="purl">{_esc(p.get("url",""))}</div>'
                     f'<div class="psum">{p["verdict"]} &middot; {sline}</div>')
        last = None
        for f in p["findings"]:
            if f["severity"] != last:
                parts.append(f'<div class="grp">{f["severity"]}</div>')
                last = f["severity"]
            parts.append(card(p, f))
        parts.append('</div>')
    parts.append('</body></html>')
    return "".join(parts)


def find_browser() -> str:
    for env in ("CHROME_BIN", "EDGE_BIN"):
        if os.environ.get(env) and Path(os.environ[env]).exists():
            return os.environ[env]
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "chromium", "chromium-browser", "msedge", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    return ""


def generate_pdf(data: dict, pages: list, shots_dir: Path, out_dir: Path) -> None:
    out_pdf = (out_dir / "report.pdf").resolve()
    print_html = (out_dir / "report-print.html").resolve()
    print_html.write_text(build_print_html(data, pages, shots_dir), encoding="utf-8")

    browser = find_browser()
    if browser:
        cmd = [browser, "--headless", "--disable-gpu", "--no-sandbox",
               "--no-pdf-header-footer", f"--print-to-pdf={out_pdf}", print_html.as_uri()]
        try:
            subprocess.run(cmd, check=True, timeout=90,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if out_pdf.exists() and out_pdf.stat().st_size > 0:
                print(f"  wrote {out_pdf}  (via {Path(browser).name})")
                return
        except Exception as e:
            print(f"  browser PDF failed ({e}); trying reportlab", file=sys.stderr)

    if not generate_pdf_reportlab(data, pages, shots_dir, out_dir, out_pdf):
        print("  PDF skipped: no browser found and reportlab unavailable. "
              "Open report-print.html and print to PDF.", file=sys.stderr)


def generate_pdf_reportlab(data: dict, pages: list, shots_dir: Path, out_dir: Path,
                           out_pdf: Path) -> bool:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
                                        Table, TableStyle, PageBreak)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except ImportError:
        return False
    from PIL import Image as PILImage

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1b", parent=styles["Title"], fontSize=20)
    h2 = ParagraphStyle("h2b", parent=styles["Heading2"], fontSize=14)
    body = ParagraphStyle("b", parent=styles["Normal"], fontSize=9, leading=12)
    doc = SimpleDocTemplate(str(out_pdf), pagesize=A4,
                            leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    page_w = A4[0] - 28 * mm
    flow = [Paragraph(data.get("title", "Visual UX Review"), h1),
            Paragraph(data.get("timestamp", ""), body),
            Paragraph(f"<b>Overall verdict:</b> {data['verdict']}", body), Spacer(1, 8)]
    rows = [["Page", "Verdict", "Crit", "High", "Med", "Low"]]
    for p in pages:
        s = p["summary"]
        rows.append([p["name"], p["verdict"], s["critical"], s["high"], s["medium"], s["low"]])
    t = Table(rows, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f3")),
                           ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                           ("FONTSIZE", (0, 0), (-1, -1), 9), ("PADDING", (0, 0), (-1, -1), 5)]))
    flow.append(t)
    crop_dir = out_dir / "_crops"
    crop_dir.mkdir(exist_ok=True)
    cap_style = ParagraphStyle("cap", parent=body, fontSize=7.5, textColor=colors.HexColor("#777777"))
    for p in pages:
        flow.append(PageBreak())
        flow.append(Paragraph(p["name"], h2))
        flow.append(Paragraph(f"{p.get('url','')} &middot; {p['verdict']}", body))
        flow.append(Spacer(1, 6))
        for f in p["findings"]:
            col = colors.HexColor(SEVERITY_COLORS[f["severity"]])
            txt = (f"<b>[{f['n']}] {f.get('title','')}</b> ({f['severity']})<br/>"
                   f"<font color='#666'>{f.get('element','')} &middot; {f.get('breakpoint','')}px</font><br/>"
                   f"<b>Issue:</b> {f.get('issue','')}")
            if f.get("evidence"):
                txt += f"<br/><b>Evidence:</b> {f['evidence']}"
            if f.get("fix"):
                txt += f"<br/><b>Fix:</b> {f['fix']}"
            # A focused crop (left) beside the text (right), or text-only when no box.
            crop, sw = crop_finding(p, f, shots_dir)
            if crop is not None:
                cpath = crop_dir / f"{p['slug']}-{f['id']}.png"
                crop.save(cpath)
                cw = min(72 * mm, page_w * 0.42)
                ch = cw * crop.size[1] / crop.size[0]
                if ch > 90 * mm:
                    ch, cw = 90 * mm, 90 * mm * crop.size[0] / crop.size[1]
                cap = Paragraph(f"[{f['n']}] {f.get('element','')} &mdash; {f.get('breakpoint','')}px", cap_style)
                left = [RLImage(str(cpath), width=cw, height=ch), Spacer(1, 2), cap]
                card = Table([[left, Paragraph(txt, body)]], colWidths=[cw + 6 * mm, page_w - cw - 6 * mm])
            else:
                card = Table([[Paragraph(txt, body)]], colWidths=[page_w])
            card.setStyle(TableStyle([("LINEBEFORE", (0, 0), (0, -1), 3, col),
                                      ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e5e5")),
                                      ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("PADDING", (0, 0), (-1, -1), 7)]))
            flow.append(card)
            flow.append(Spacer(1, 5))
    doc.build(flow)
    print(f"  wrote {out_pdf}  (via reportlab)")
    return True


# ----------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="Generate annotated UX-review reports.")
    ap.add_argument("--findings", required=True, type=Path)
    ap.add_argument("--screenshots-dir", type=Path, default=Path("."))
    ap.add_argument("--out-dir", type=Path, default=Path("ux-report"))
    ap.add_argument("--format", default="html,md,png,pdf", help="comma list: html,md,png,pdf")
    args = ap.parse_args()

    if not args.findings.exists():
        print(f"error: findings file not found: {args.findings}", file=sys.stderr)
        return 1

    data = load(args.findings)
    pages = normalize_pages(data)
    data["verdict"] = data.get("verdict") or overall_verdict(pages)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    formats = {x.strip() for x in args.format.split(",")}
    total = sum(len(p["findings"]) for p in pages)
    print(f"Generating report: {len(pages)} page(s), {total} finding(s)")

    # Full-page annotated PNGs are a standalone deliverable (and feed the HTML overlays
    # are drawn live, so PNGs are only made when explicitly requested). The PDF builds its
    # own focused crops from the raw screenshots, so it does not need them.
    png_map = {}
    if "png" in formats:
        png_map = generate_pngs(pages, args.screenshots_dir, args.out_dir)

    if "html" in formats:
        images_per_page = []
        for p in pages:
            imgs = {}
            for bp, fname in (p.get("screenshots") or {}).items():
                src = args.screenshots_dir / fname
                if src.exists():
                    imgs[str(bp)] = data_uri(src)
            images_per_page.append(imgs)
        generate_html(data, pages, images_per_page, args.out_dir / "report.html")
    if "md" in formats:
        generate_md(data, pages, png_map, args.out_dir / "report.md")
    if "pdf" in formats:
        generate_pdf(data, pages, args.screenshots_dir, args.out_dir)

    print(f"Done -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
