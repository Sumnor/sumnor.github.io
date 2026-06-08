#!/usr/bin/env python3
"""build_index.py — scans results/ and regenerates index.html"""
import os, re
from datetime import datetime

RESULTS_DIR = "results"
OUTPUT_FILE = "index.html"

def scan_results():
    files = []
    if not os.path.isdir(RESULTS_DIR):
        return files
    for fname in sorted(os.listdir(RESULTS_DIR), reverse=True):
        if not (fname.endswith(".pdf") or fname.endswith(".pptx")):
            continue
        path = os.path.join(RESULTS_DIR, fname)
        size = os.path.getsize(path)
        size_str = f"{size // 1024} KB" if size < 1024*1024 else f"{size / 1024 / 1024:.1f} MB"

        # Parse topic + date from filename: research_TOPIC_YYYYMMDD_HHMMSS.ext
        m = re.match(r"research_(.+?)_(\d{8})_(\d{6})\.(pdf|pptx)$", fname)
        if m:
            raw_topic = m.group(1).replace("_", " ")
            date_str  = datetime.strptime(m.group(2) + m.group(3), "%Y%m%d%H%M%S").strftime("%b %d, %Y %H:%M")
            ext       = m.group(4).upper()
        else:
            raw_topic = fname
            date_str  = "—"
            ext       = fname.rsplit(".", 1)[-1].upper()

        icon = "📄" if ext == "PDF" else "📊"
        files.append({"fname": fname, "topic": raw_topic, "date": date_str,
                      "size": size_str, "ext": ext, "icon": icon})
    return files

def build_html(files):
    rows = ""
    if not files:
        rows = '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:2rem">No results yet. Trigger a run from the Actions tab.</td></tr>'
    else:
        for f in files:
            badge_color = "#6366f1" if f["ext"] == "PDF" else "#0891b2"
            rows += f"""
        <tr>
          <td><span class="icon">{f["icon"]}</span></td>
          <td class="topic">{f["topic"]}</td>
          <td><span class="badge" style="background:{badge_color}">{f["ext"]}</span></td>
          <td class="date">{f["date"]}</td>
          <td class="size">{f["size"]}</td>
          <td><a class="dl" href="{RESULTS_DIR}/{f["fname"]}" download>↓ Download</a></td>
        </tr>"""

    total = len(files)
    updated = datetime.utcnow().strftime("%b %d, %Y at %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research Agent — Results</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      min-height: 100vh;
      padding: 2rem 1rem;
    }}
    .container {{ max-width: 860px; margin: 0 auto; }}
    header {{
      text-align: center;
      padding: 2.5rem 0 2rem;
    }}
    header h1 {{
      font-size: 2rem;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.02em;
    }}
    header p {{
      margin-top: 0.5rem;
      color: #94a3b8;
      font-size: 0.9rem;
    }}
    .stats {{
      display: flex;
      gap: 1rem;
      justify-content: center;
      margin: 1.5rem 0 2rem;
    }}
    .stat {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 0.6rem 1.2rem;
      font-size: 0.85rem;
      color: #94a3b8;
    }}
    .stat strong {{ color: #a5b4fc; }}
    .card {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      overflow: hidden;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    thead tr {{
      background: #0f172a;
      border-bottom: 1px solid #334155;
    }}
    thead th {{
      padding: 0.75rem 1rem;
      text-align: left;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #64748b;
      font-weight: 600;
    }}
    tbody tr {{
      border-bottom: 1px solid #1e293b;
      transition: background 0.15s;
    }}
    tbody tr:last-child {{ border-bottom: none; }}
    tbody tr:hover {{ background: #263347; }}
    td {{
      padding: 0.85rem 1rem;
      font-size: 0.9rem;
      vertical-align: middle;
    }}
    .icon {{ font-size: 1.2rem; }}
    .topic {{
      color: #e2e8f0;
      font-weight: 500;
      text-transform: capitalize;
      max-width: 280px;
    }}
    .badge {{
      display: inline-block;
      padding: 0.2rem 0.55rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 700;
      color: #fff;
      letter-spacing: 0.04em;
    }}
    .date, .size {{ color: #64748b; font-size: 0.82rem; white-space: nowrap; }}
    .dl {{
      display: inline-block;
      background: #6366f1;
      color: #fff;
      text-decoration: none;
      padding: 0.35rem 0.85rem;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 600;
      white-space: nowrap;
      transition: background 0.15s;
    }}
    .dl:hover {{ background: #4f46e5; }}
    footer {{
      text-align: center;
      margin-top: 2rem;
      color: #475569;
      font-size: 0.8rem;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>🔬 Research Agent</h1>
      <p>Auto-generated research reports. Trigger a new run from the GitHub Actions tab.</p>
    </header>
    <div class="stats">
      <div class="stat"><strong>{total}</strong> report{"s" if total != 1 else ""}</div>
      <div class="stat">Updated <strong>{updated}</strong></div>
    </div>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th></th>
            <th>Topic</th>
            <th>Type</th>
            <th>Date</th>
            <th>Size</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>
    <footer>
      Research Agent · Powered by DuckDuckGo + Python · No AI
    </footer>
  </div>
</body>
</html>"""

if __name__ == "__main__":
    files = scan_results()
    html  = build_html(files)
    with open(OUTPUT_FILE, "w") as f:
        f.write(html)
    print(f"✅ index.html rebuilt — {len(files)} result(s)")
