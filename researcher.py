#!/usr/bin/env python3
"""
researcher_nosql.py — Pure scraper research agent
No AI. Searches, scrapes, deduplicates, outputs polished PDF or PPTX.

Input format:
  quantum computing
  * focus on 2024 breakthroughs
  * ignore basic explanations

Modes:
  1 — Detailed Research Paper (PDF)
  2 — Breakdown (PDF, bullet points)
  3 — Presentation (PPTX, define slide structure with * lines)
      e.g.  * title, what is quantum computing, qubit types, real world uses, conclusion
            * 8 slides total
"""

import os, sys, re, io, json, subprocess, tempfile, requests
from datetime import datetime
from difflib import SequenceMatcher
from ddgs import DDGS
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, Image, PageBreak, KeepTogether, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

# ── COLORS ────────────────────────────────────────────────────────────────────
DARK    = colors.HexColor("#0f172a")
ACCENT  = colors.HexColor("#6366f1")
ACCENT2 = colors.HexColor("#a5b4fc")
LIGHT   = colors.HexColor("#f1f5f9")
MID     = colors.HexColor("#64748b")
WHITE   = colors.white

# ── MODE PROFILES ─────────────────────────────────────────────────────────────
MODES = {
    "1": {"label": "Detailed Research Paper", "num_results": 10, "max_chars": 6000,
          "min_words": 20, "sim_thresh": 0.80, "max_paras": None, "emoji": "📄"},
    "2": {"label": "Breakdown",               "num_results": 6,  "max_chars": 3000,
          "min_words": 15, "sim_thresh": 0.70, "max_paras": 6,   "emoji": "⚡"},
    "3": {"label": "Presentation (.pptx)",    "num_results": 8,  "max_chars": 3000,
          "min_words": 15, "sim_thresh": 0.75, "max_paras": 5,   "emoji": "📊"},
}

OUTPUT_DIR = "."

# ── ACCESS CHECK ──────────────────────────────────────────────────────────────
BLOCK_PATTERNS = [
    r"sign\s*in",  r"log\s*in",  r"create\s+an?\s+account",
    r"subscribe\s+to\s+(read|access|continue)",
    r"this\s+content\s+is\s+(only\s+)?for\s+(subscribers|members|premium)",
    r"cloudflare",  r"ddos\s+protection",  r"access\s+denied",
    r"403\s+forbidden",  r"enable\s+javascript",
    r"you('ve)?\s+reached\s+(your\s+)?(free\s+)?(article|read)\s+limit",
    r"paywall",  r"premium\s+content",
]

def is_blocked(html: str, status: int) -> tuple[bool, str]:
    if status in (401, 403, 429, 451):
        return True, f"HTTP {status}"
    text = html[:8000].lower()
    for pat in BLOCK_PATTERNS:
        if re.search(pat, text):
            return True, pat
    return False, ""

# ── 1. PARSE INPUT ────────────────────────────────────────────────────────────
def parse_input(raw: str):
    lines = raw.strip().splitlines()
    topic_lines, context_lines = [], []
    for line in lines:
        s = line.strip()
        if s.startswith("*"):
            context_lines.append(s.lstrip("*").strip())
        else:
            topic_lines.append(s)
    return " ".join(topic_lines).strip(), context_lines

def parse_slide_outline(context_lines: list[str]) -> tuple[list[str], int | None]:
    """Extract slide titles and optional total count from * lines."""
    slides, total = [], None
    for line in context_lines:
        # Check for "N slides total" or "total N slides"
        m = re.search(r"(\d+)\s+slides?\s*(total)?|(total)?\s*(\d+)\s+slides?", line, re.I)
        if m:
            total = int(m.group(1) or m.group(4))
            continue
        # Otherwise split on commas — each chunk is a slide title
        parts = [p.strip() for p in line.split(",") if p.strip()]
        slides.extend(parts)
    return slides, total

# ── 2. SEARCH ─────────────────────────────────────────────────────────────────
def search(query, n):
    print(f"  🔍 Searching: {query} ({n} results)")
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=n))

# ── 3. SCRAPE (with access check) ─────────────────────────────────────────────
def scrape(url, max_chars, min_words):
    try:
        resp = requests.get(url, timeout=7, headers={"User-Agent": "Mozilla/5.0"})
        is_wikipedia = "wikipedia.org" in url
        blocked, reason = (False, "") if is_wikipedia else is_blocked(resp.text, resp.status_code)
        if blocked:
            return [], f"blocked ({reason})"
        soup = BeautifulSoup(resp.text, "html.parser")
        for t in soup(["script","style","nav","footer","header","aside","form","noscript"]):
            t.decompose()
        paras = []
        for tag in soup.find_all(["p","h2","h3","li"]):
            text = tag.get_text(" ", strip=True)
            if len(text.split()) >= min_words:
                paras.append(text)
        result, total = [], 0
        for p in paras:
            if total + len(p) > max_chars:
                break
            result.append(p)
            total += len(p)
        if not result:
            return [], "no usable content"
        return result, None
    except requests.exceptions.Timeout:
        return [], "timeout"
    except Exception as e:
        return [], str(e)[:40]

# ── 4. FETCH IMAGES ───────────────────────────────────────────────────────────
def fetch_images(query, n=2):
    print(f"  🖼  Fetching images...")
    imgs = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=15, safesearch="moderate"))
        for r in results:
            if len(imgs) >= n:
                break
            try:
                resp = requests.get(r["image"], timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                ct = resp.headers.get("content-type", "")
                if resp.status_code == 200 and ct.startswith("image") and "svg" not in ct:
                    imgs.append(resp.content)
            except Exception:
                continue
    except Exception:
        pass
    return imgs

# ── 5. DEDUPLICATE ────────────────────────────────────────────────────────────
def deduplicate(sources, thresh, max_paras):
    seen = []
    for src in sources:
        unique = []
        for para in src["paragraphs"]:
            if all(SequenceMatcher(None, para, s).ratio() < thresh for s in seen):
                unique.append(para)
                seen.append(para)
        if max_paras:
            unique = unique[:max_paras]
        src["paragraphs"] = unique
    return [s for s in sources if s["paragraphs"]]

# ── 6A. BUILD PDF (modes 1 & 2) ───────────────────────────────────────────────
def build_pdf(topic, context_lines, mode_cfg, sources, images):
    print("  📄 Building PDF...")
    safe = re.sub(r"[^\w\s-]", "", topic).strip().replace(" ", "_")[:50]
    filename = f"{OUTPUT_DIR}/research_{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    W, _ = A4
    LM = RM = 18*mm
    CW = W - LM - RM
    is_breakdown = mode_cfg["label"] == "Breakdown"

    base = getSampleStyleSheet()
    def S(name, parent="Normal", **kw):
        return ParagraphStyle(name, parent=base[parent], **kw)

    s_cover_label = S("CL", fontSize=10, textColor=ACCENT2, alignment=TA_CENTER, spaceAfter=6)
    s_cover_title = S("CT", fontSize=26, textColor=WHITE, leading=32,
                       alignment=TA_CENTER, fontName="Helvetica-Bold")
    s_cover_meta  = S("CM", fontSize=11, textColor=ACCENT2, alignment=TA_CENTER, spaceAfter=3)
    s_cover_ctx   = S("CX", fontSize=9,  textColor=colors.HexColor("#94a3b8"), alignment=TA_CENTER)
    s_cover_date  = S("CD", fontSize=8,  textColor=MID, alignment=TA_CENTER)
    s_toc_title   = S("TT", fontSize=18, textColor=DARK, fontName="Helvetica-Bold", spaceAfter=6)
    s_toc_num     = S("TN", fontSize=11, textColor=ACCENT, fontName="Helvetica-Bold", leading=14)
    s_toc_entry   = S("TE", fontSize=10, textColor=DARK, leading=14, fontName="Helvetica-Bold")
    s_toc_count   = S("TC", fontSize=9,  textColor=MID, leading=14, alignment=TA_CENTER)
    s_toc_url     = S("TU", fontSize=8,  textColor=ACCENT, leading=11, leftIndent=4)
    s_h1          = S("H1", fontSize=14, textColor=ACCENT, leading=18,
                       spaceBefore=12, spaceAfter=5, fontName="Helvetica-Bold")
    s_source_tag  = S("ST", fontSize=8,  textColor=WHITE, leading=10)
    s_body        = S("BD", fontSize=10, textColor=DARK, leading=15,
                       alignment=TA_JUSTIFY, spaceAfter=6)
    s_bullet      = S("BL", fontSize=10, textColor=DARK, leading=15, spaceAfter=3)
    s_ctx_label   = S("CFH", fontSize=9, textColor=ACCENT2, fontName="Helvetica-Bold", spaceAfter=3)
    s_ctx_body    = S("CB", fontSize=9,  textColor=ACCENT2, leading=13)
    s_footer      = S("FT", fontSize=8,  textColor=MID, alignment=TA_CENTER)

    story = []

    # COVER
    ct = Table([[Paragraph("Research Report", s_cover_label)],
                [Paragraph(topic, s_cover_title)]], colWidths=[CW])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), DARK),
        ("TOPPADDING", (0,0),(-1,-1), 30), ("BOTTOMPADDING", (0,0),(-1,-1), 30),
        ("LEFTPADDING",(0,0),(-1,-1), 20), ("RIGHTPADDING", (0,0),(-1,-1), 20),
        ("ROUNDEDCORNERS",(0,0),(-1,-1), 10),
    ]))
    story.append(ct)
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        f"{mode_cfg['emoji']}  Mode: {mode_cfg['label']}  ·  "
        f"{len(sources)} sources  ·  {sum(len(s['paragraphs']) for s in sources)} items",
        s_cover_meta))
    ctx_display = "; ".join(context_lines)
    if ctx_display:
        story.append(Paragraph(f"Focus: {ctx_display}", s_cover_ctx))
    story.append(Paragraph(f"Generated {datetime.now().strftime('%B %d, %Y at %H:%M')}", s_cover_date))

    # Cover images
    if images:
        story.append(Spacer(1, 6*mm))
        cells = []
        for raw in images[:2]:
            try:
                img = Image(io.BytesIO(raw), width=CW/2 - 3*mm, height=52*mm)
                img.hAlign = "CENTER"
                cells.append(img)
            except Exception:
                cells.append(Paragraph("", base["Normal"]))
        if len(cells) == 2:
            it = Table([cells], colWidths=[CW/2, CW/2])
            it.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                                    ("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2)]))
            story.append(it)
        elif cells:
            story.append(cells[0])
    story.append(PageBreak())

    # Context box
    if context_lines:
        ctx_table = Table([[Paragraph("📌  Research Focus", s_ctx_label)],
                           [Paragraph(ctx_display, s_ctx_body)]], colWidths=[CW])
        ctx_table.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1), DARK),
            ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
            ("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),14),
            ("ROUNDEDCORNERS",(0,0),(-1,-1),6),
        ]))
        story.append(ctx_table)
        story.append(Spacer(1, 6*mm))

    # Inhaltsverzeichnis
    story.append(Paragraph("Inhaltsverzeichnis", s_toc_title))
    story.append(HRFlowable(width=CW, thickness=1, color=ACCENT, spaceAfter=8))
    for i, src in enumerate(sources, 1):
        rt = Table([[Paragraph(f"{i}.", s_toc_num),
                     Paragraph(src["title"] or src["url"], s_toc_entry),
                     Paragraph(f"{len(src['paragraphs'])} {'points' if is_breakdown else 'para.'}", s_toc_count)]],
                   colWidths=[8*mm, CW - 28*mm, 20*mm])
        rt.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),4),
            ("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),2),
            ("BACKGROUND",(0,0),(-1,-1), LIGHT if i%2==0 else WHITE),
        ]))
        story.append(rt)
        story.append(Paragraph(src["url"], s_toc_url))
        story.append(Spacer(1, 1*mm))
    story.append(PageBreak())

    # Content sections
    for i, src in enumerate(sources, 1):
        title = src["title"] or src["url"]
        badge = Table([[Paragraph(f"🔗  {src['url']}", s_source_tag)]], colWidths=[CW])
        badge.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),DARK),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
            ("ROUNDEDCORNERS",(0,0),(-1,-1),4),
        ]))
        story.append(KeepTogether([
            Paragraph(f"{i}. {title}", s_h1),
            HRFlowable(width=CW, thickness=0.5, color=ACCENT2, spaceAfter=5),
            badge, Spacer(1, 4*mm),
        ]))

        if is_breakdown:
            items = [ListItem(Paragraph(p, s_bullet), leftIndent=12, spaceAfter=4)
                     for p in src["paragraphs"]]
            story.append(ListFlowable(items, bulletType="bullet", bulletColor=ACCENT,
                                      bulletFontSize=8, leftIndent=16))
        else:
            for para in src["paragraphs"]:
                story.append(Paragraph(para, s_body))

        story.append(Spacer(1, 6*mm))
        if i < len(sources):
            story.append(HRFlowable(width=CW, thickness=0.3,
                                     color=colors.HexColor("#e2e8f0"), spaceAfter=6))

    # Footer page
    story.append(PageBreak())
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph(f"Mode: {mode_cfg['label']}", s_footer))
    story.append(Paragraph("All content scraped from public web sources.", s_footer))
    story.append(Paragraph(
        f"Duplicates removed at {int(mode_cfg['sim_thresh']*100)}% similarity threshold.", s_footer))
    story.append(Paragraph(f"Generated by Research Agent · {datetime.now().strftime('%Y-%m-%d')}", s_footer))

    doc = SimpleDocTemplate(filename, pagesize=A4,
                            leftMargin=LM, rightMargin=RM, topMargin=18*mm, bottomMargin=18*mm)
    doc.build(story)
    return filename

# ── 6B. BUILD PPTX (mode 3) ───────────────────────────────────────────────────
def build_pptx(topic, slide_titles, sources, images):
    print("  📊 Building PPTX...")
    safe = re.sub(r"[^\w\s-]", "", topic).strip().replace(" ", "_")[:50]
    filename = f"{OUTPUT_DIR}/research_{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"

    # Map each slide title → best matching scraped content
    # Build a lookup: title → list of bullet strings
    all_paras = []
    for src in sources:
        for p in src["paragraphs"]:
            all_paras.append({"text": p, "url": src["url"], "title": src["title"]})

    def best_bullets(slide_title, n=5):
        """Score paragraphs by keyword overlap with slide title."""
        keywords = set(re.findall(r"\w+", slide_title.lower())) - {"the","a","an","of","in","and","or","to","is","are","for","with"}
        scored = []
        for p in all_paras:
            words = set(re.findall(r"\w+", p["text"].lower()))
            score = len(keywords & words)
            scored.append((score, p["text"]))
        scored.sort(key=lambda x: -x[0])
        seen, bullets = [], []
        for _, text in scored:
            if len(bullets) >= n:
                break
            if all(SequenceMatcher(None, text, s).ratio() < 0.7 for s in seen):
                # Trim to one clean sentence or 180 chars
                sentence = re.split(r"(?<=[.!?])\s+", text.strip())[0]
                if len(sentence) > 180:
                    sentence = sentence[:177] + "..."
                bullets.append(sentence)
                seen.append(text)
        return bullets

    # Build JS for pptxgenjs
    slides_js = []

    # Title slide
    slides_js.append(f"""
  // Title slide
  let s0 = pres.addSlide();
  s0.background = {{ color: "0f172a" }};
  s0.addShape(pres.shapes.RECTANGLE, {{ x: 0, y: 2.2, w: 10, h: 1.4, fill: {{ color: "6366f1" }} }});
  s0.addText("{topic.replace('"', '')}", {{
    x: 0.5, y: 2.25, w: 9, h: 1.3,
    fontSize: 38, bold: true, color: "FFFFFF",
    fontFace: "Calibri", align: "center", valign: "middle", margin: 0
  }});
  s0.addText("Research Presentation", {{
    x: 0.5, y: 1.2, w: 9, h: 0.5,
    fontSize: 14, color: "a5b4fc", fontFace: "Calibri", align: "center"
  }});
  s0.addText("{datetime.now().strftime('%B %d, %Y')}", {{
    x: 0.5, y: 4.9, w: 9, h: 0.4,
    fontSize: 11, color: "64748b", fontFace: "Calibri", align: "center"
  }});
""")

    # Inhaltsverzeichnis slide
    toc_items = [t for t in slide_titles if t.lower() not in ("title", "inhaltsverzeichnis", "table of contents")]
    toc_bullets = "\n".join([
        f'  {{ text: "{i+1}. {t.replace(chr(34), chr(39))}", options: {{ bullet: true, breakLine: true, fontSize: 15, color: "0f172a" }} }},'
        for i, t in enumerate(toc_items)
    ])
    slides_js.append(f"""
  // Inhaltsverzeichnis
  let stoc = pres.addSlide();
  stoc.background = {{ color: "f1f5f9" }};
  stoc.addShape(pres.shapes.RECTANGLE, {{ x: 0, y: 0, w: 0.12, h: 5.625, fill: {{ color: "6366f1" }} }});
  stoc.addText("Inhaltsverzeichnis", {{
    x: 0.4, y: 0.3, w: 9.2, h: 0.7,
    fontSize: 28, bold: true, color: "0f172a", fontFace: "Calibri"
  }});
  stoc.addText([
    {toc_bullets}
  ], {{ x: 0.5, y: 1.2, w: 8.8, h: 4.0, fontFace: "Calibri", paraSpaceAfter: 6 }});
""")

    # Content slides
    content_titles = [t for t in slide_titles
                      if t.lower() not in ("title", "inhaltsverzeichnis", "table of contents")]

    for idx, title in enumerate(content_titles):
        bullets = best_bullets(title, n=5)
        if not bullets:
            bullets = ["No specific content found for this topic."]

        bullet_items = "\n".join([
            f'  {{ text: {json.dumps(b)}, options: {{ bullet: true, breakLine: true, fontSize: 13, color: "1e293b" }} }},'
            for b in bullets
        ])
        bg = "FFFFFF" if idx % 2 == 0 else "f8fafc"
        slides_js.append(f"""
  // Slide: {title}
  let s{idx+2} = pres.addSlide();
  s{idx+2}.background = {{ color: "{bg}" }};
  s{idx+2}.addShape(pres.shapes.RECTANGLE, {{ x: 0, y: 0, w: 0.12, h: 5.625, fill: {{ color: "6366f1" }} }});
  s{idx+2}.addShape(pres.shapes.RECTANGLE, {{ x: 0.12, y: 0, w: 9.88, h: 1.0, fill: {{ color: "0f172a" }} }});
  s{idx+2}.addText({json.dumps(title)}, {{
    x: 0.4, y: 0.1, w: 9.3, h: 0.8,
    fontSize: 24, bold: true, color: "FFFFFF", fontFace: "Calibri", valign: "middle", margin: 0
  }});
  s{idx+2}.addText([
    {bullet_items}
  ], {{ x: 0.4, y: 1.15, w: 9.2, h: 4.2, fontFace: "Calibri", paraSpaceAfter: 8 }});
""")

    # Conclusion / last slide if not already in titles
    if not any("conclusion" in t.lower() or "fazit" in t.lower() for t in slide_titles):
        n = len(content_titles) + 2
        slides_js.append(f"""
  // Conclusion
  let s{n} = pres.addSlide();
  s{n}.background = {{ color: "0f172a" }};
  s{n}.addShape(pres.shapes.RECTANGLE, {{ x: 0, y: 2.0, w: 10, h: 1.6, fill: {{ color: "6366f1" }} }});
  s{n}.addText("Thank You", {{
    x: 0.5, y: 2.05, w: 9, h: 1.5,
    fontSize: 40, bold: true, color: "FFFFFF", fontFace: "Calibri", align: "center", valign: "middle", margin: 0
  }});
  s{n}.addText("{topic.replace(chr(34), chr(39))}", {{
    x: 0.5, y: 4.0, w: 9, h: 0.5,
    fontSize: 14, color: "a5b4fc", fontFace: "Calibri", align: "center"
  }});
""")

    all_slides = "\n".join(slides_js)
    js = f"""
const pptxgen = require("pptxgenjs");
let pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = {json.dumps(topic)};

{all_slides}

pres.writeFile({{ fileName: {json.dumps(filename)} }})
  .then(() => console.log("OK:" + {json.dumps(filename)}))
  .catch(e => {{ console.error("ERR:" + e); process.exit(1); }});
"""

    js_path = tempfile.mktemp(suffix=".js")
    with open(js_path, "w") as f:
        f.write(js)

    result = subprocess.run(["node", js_path], capture_output=True, text=True, timeout=30)
    os.unlink(js_path)
    if result.returncode != 0:
        raise RuntimeError(f"pptxgenjs error:\n{result.stderr}")

    return filename

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--topic",  default=None)
    parser.add_argument("--mode",   default=None)
    parser.add_argument("--output", default=".")
    args, _ = parser.parse_known_args()

    global OUTPUT_DIR
    OUTPUT_DIR = args.output
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Non-interactive (GitHub Actions) ──────────────────
    if args.topic:
        raw    = args.topic
        choice = args.mode if args.mode in MODES else "1"
        topic, context_lines = parse_input(raw)
        print(f"\n🔬 Research Agent — {MODES[choice]['label']}")
        print(f"   Topic  : {topic}")
        if context_lines:
            print(f"   Context: {' | '.join(context_lines)}")
    else:
        # ── Interactive (local terminal) ───────────────────
        print("\n╔══════════════════════════════════════════╗")
        print("║     Research Agent 🔬                     ║")
        print("╚══════════════════════════════════════════╝")
        print("\nTip: add * lines for focus or slide structure, e.g.:")
        print("  salad bowl theory")
        print("  * title, what is salad bowl, melting pot, comparison, conclusion")
        print("  * 6 slides total\n")
        print("Enter your topic (press Enter twice when done):")
        lines = []
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
        raw = "\n".join(lines)
        topic, context_lines = parse_input(raw)
        if not topic:
            sys.exit(0)
        print(f"\nTopic : {topic}")
        if context_lines:
            print(f"Context: {' | '.join(context_lines)}")
        print("\nPick a mode:")
        print("  [1] 📄  Detailed Research Paper  — 10 sources, full paragraphs")
        print("  [2] ⚡  Breakdown                — bullet points, key info only")
        print("  [3] 📊  Presentation (.pptx)     — define slides with * lines")
        choice = input("\nMode (1/2/3): ").strip()
        if choice not in MODES:
            print("Invalid, defaulting to 1.")
            choice = "1"

    mode_cfg = MODES[choice]
    print(f"\n🚀 Mode: {mode_cfg['label']}\n")

    # For PPTX, parse slide outline from * lines
    slide_titles = []
    if choice == "3":
        slide_titles, total_count = parse_slide_outline(context_lines)
        if not slide_titles:
            slide_titles = ["title", "inhaltsverzeichnis", "introduction",
                            "main findings", "analysis", "conclusion"]
        elif "title" not in [s.lower() for s in slide_titles]:
            slide_titles = ["title", "inhaltsverzeichnis"] + slide_titles
        elif "inhaltsverzeichnis" not in [s.lower() for s in slide_titles]:
            idx = next((i for i,s in enumerate(slide_titles) if s.lower()=="title"), 0)
            slide_titles.insert(idx+1, "inhaltsverzeichnis")
        print(f"  Slide structure: {' → '.join(slide_titles)}\n")

    # Build search query
    query = topic + (" " + " ".join(context_lines) if context_lines else "")

    print("[ 1/4 ] Searching...")
    results = search(query, mode_cfg["num_results"])
    if not results:
        print("❌  No results found.")
        sys.exit(1)

    print("[ 2/4 ] Scraping pages...")
    sources, skipped = [], 0
    for r in results:
        paras, err = scrape(r["href"], mode_cfg["max_chars"], mode_cfg["min_words"])
        if err:
            print(f"        ⛔ SKIP  {r['title'][:55]} — {err}")
            skipped += 1
        else:
            print(f"        ✅      {r['title'][:55]:<55} → {len(paras)} paragraphs")
            sources.append({"title": r["title"], "url": r["href"], "paragraphs": paras})

    if not sources:
        print("❌  All sources were blocked or inaccessible.")
        sys.exit(1)
    if skipped:
        print(f"        ({skipped} source(s) skipped)")

    print("[ 3/4 ] Deduplicating...")
    before = sum(len(s["paragraphs"]) for s in sources)
    sources = deduplicate(sources, mode_cfg["sim_thresh"], mode_cfg["max_paras"])
    after = sum(len(s["paragraphs"]) for s in sources)
    print(f"        {before} → {after} items ({before - after} duplicates removed)")

    print("[ 4/4 ] Fetching images & building output...")
    images = fetch_images(topic, n=2)

    if choice == "3":
        out = build_pptx(topic, slide_titles, sources, images)
    else:
        out = build_pdf(topic, context_lines, mode_cfg, sources, images)

    print(f"\n✅  Done! Saved to:\n    {os.path.abspath(out)}\n")

if __name__ == "__main__":
    main()
