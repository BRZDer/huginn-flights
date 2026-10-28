#!/usr/bin/env python3
"""
huginn_dashboard_builder.py — 逆向自「ProjectHuginn 機票追蹤 Dashboard」的靜態頁產生器（精簡複刻）

輸入：一個 JSON（格式見 SAMPLE），每個追蹤組合給 label / flight 資訊 / 每日價格點
輸出：
  <out>.html        自包含 HTML（內嵌 <script type="application/json"> 快照 + 預算好座標的 SVG 曲線）
  <out>.data.json   sidecar 快照；頁面用 http(s) 開啟時會 fetch 它比對 generatedAt，新版就自動 reload

用法：
  python3 2026-10-28_huginn_dashboard_builder.py input.json out/dashboard
  python3 2026-10-28_huginn_dashboard_builder.py --demo out/dashboard     # 用內建範例跑一次

原作的設計要點（本檔忠實保留）：
  1. 資料與版型分離：抓價腳本只負責產 JSON，頁面是純輸出，沒有後端 API
  2. 曲線座標在產生端算好（x,y 寫進 data-points），前端 JS 只做 hover 找最近點
  3. 離線打開看快照，掛在本機伺服器時自動偵測新資料
"""
import json, sys, html, datetime as dt
from pathlib import Path

W, H, PAD_L, PAD_R, PAD_T, PAD_B = 800, 260, 24, 24, 20, 40

SAMPLE = {
    "trips": [{"id": "demo_trip", "name": "Sapporo Dec 10", "dates": "Dec 10 – 15", "depart": "2026-12-10"}],
    "quotes": [{
        "quoteId": "demo_airasia", "trip": "demo_trip",
        "item": "TPE ⇄ CTS · Thai AirAsia · Dec 10", "target": None,
        "flight": {"outbound": "FD 242 TPE 07:15 → CTS 12:00", "inbound": "FD 243 CTS 14:00 → TPE 17:55"},
        "points": [{"date": (dt.date(2026, 9, 1) + dt.timedelta(d)).isoformat(), "v": 18000 + (d * 137) % 3000}
                   for d in range(56)],
    }],
}


def money(v):
    return "NT$" + f"{int(v):,}"


def chart_points(points):
    """把 (date, v) 轉成 SVG 座標，等距 x、線性 y；回傳 list[dict] 供 data-points 與 polyline 使用。"""
    vals = [p["v"] for p in points]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    n = max(len(points) - 1, 1)
    out = []
    for i, p in enumerate(points):
        x = PAD_L + (W - PAD_L - PAD_R) * i / n
        y = PAD_T + (H - PAD_T - PAD_B) * (1 - (p["v"] - lo) / span)
        out.append({"x": round(x, 2), "y": round(y, 2), "date": p["date"], "value": p["v"],
                    "label": p["date"][5:] if i in (0, len(points) - 1) else ""})
    return out, lo, hi


def pct_change(points, days=7):
    if len(points) < 2:
        return 0.0
    now = points[-1]
    cutoff = (dt.date.fromisoformat(now["date"]) - dt.timedelta(days=days)).isoformat()
    base = next((p for p in points if p["date"] >= cutoff), points[0])
    return round((now["v"] - base["v"]) / base["v"] * 100, 1) if base["v"] else 0.0


def build(data, out_base: Path):
    generated = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    today = dt.date.today().isoformat()
    cards = []
    snapshot_quotes = []
    for q in data["quotes"]:
        pts = sorted(q["points"], key=lambda p: p["date"])
        cpts, lo, hi = chart_points(pts)
        now = pts[-1]["v"]
        chg = pct_change(pts)
        snapshot_quotes.append({**q, "current": now, "low": lo, "changePct": chg, "latestPriceDate": pts[-1]["date"]})
        poly = " ".join(f"{p['x']},{p['y']}" for p in cpts)
        area = f"{cpts[0]['x']},{H - PAD_B} {poly} {cpts[-1]['x']},{H - PAD_B}"
        qid = html.escape(q["quoteId"])
        trend_cls = "down" if chg < 0 else "up"
        cards.append(f"""
<article class="fare-card">
  <header class="card-top">
    <div><div class="eyebrow">{html.escape(q.get('trip', ''))}</div><h2>{html.escape(q['item'])}</h2></div>
    <label class="select-fare"><input type="checkbox" data-select-fare="{qid}"> Add to plan</label>
  </header>
  <div class="fare-metrics">
    <div><span class="sub">Now</span><b>{money(now)}</b></div>
    <div><span class="sub">Low</span><b>{money(lo)}</b></div>
    <div><span class="sub">7d</span><b class="{trend_cls}">{chg:+.1f}%</b></div>
    <div><span class="sub">Target</span><b>{money(q['target']) if q.get('target') else '—'}</b></div>
  </div>
  <div class="flight-legs"><span>🛫 {html.escape(q['flight']['outbound'])}</span><span>🛬 {html.escape(q['flight']['inbound'])}</span></div>
  <div class="chart-wrap">
    <svg class="price-chart" viewBox="0 0 {W} {H}" role="img" aria-label="{qid} price trend"
         data-points='{html.escape(json.dumps(cpts, ensure_ascii=False), quote=True)}'>
      <defs><linearGradient id="fill-{qid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="var(--good)" stop-opacity=".28"/><stop offset="1" stop-color="var(--good)" stop-opacity="0"/>
      </linearGradient></defs>
      <polygon points="{area}" fill="url(#fill-{qid})"/>
      <polyline class="chart-line" points="{poly}" fill="none" stroke="var(--good)" stroke-width="2.2" stroke-linejoin="round"/>
      <line class="hover-guide" y1="{PAD_T}" y2="{H - PAD_B}" stroke="var(--muted)" stroke-dasharray="3 3" hidden/>
      <circle class="hover-dot" r="4.5" fill="var(--ink)" hidden/>
    </svg>
    <div class="chart-tooltip" hidden></div>
  </div>
</article>""")

    snapshot = {"HUGINN_GENERATED_AT": generated, "HUGINN_TODAY": today,
                "HUGINN_DATA": {"trips": data["trips"], "watchlist": snapshot_quotes}}
    sidecar = out_base.with_suffix(".data.json")
    page = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>機票追蹤 Dashboard</title>
<style>
:root{{--paper:#f7f0e4;--card:#fffaf1;--ink:#2f3525;--muted:#777563;--line:#ded4c2;--good:#3f6b43;--bad:#9a4a3a}}
@media (prefers-color-scheme:dark){{:root{{--paper:#1b1d18;--card:#242721;--ink:#ece6d8;--muted:#a39e8e;--line:#3a3d34;--good:#8fbf8a;--bad:#e08a76}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.45 -apple-system,"Noto Sans TC",sans-serif}}
.shell{{max-width:1100px;margin:0 auto;padding:24px 16px}}h1{{font-size:26px;margin:0 0 4px}}.foot,.sub,.eyebrow{{color:var(--muted);font-size:12px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;margin-top:20px}}
.fare-card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}}
.card-top{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}}h2{{font-size:16px;margin:2px 0 0}}
.fare-metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:12px 0}}.fare-metrics b{{display:block;font-size:17px}}
.down{{color:var(--good)}}.up{{color:var(--bad)}}.flight-legs{{display:grid;gap:4px;font-size:13px;color:var(--muted);margin-bottom:10px}}
.chart-wrap{{position:relative}}.price-chart{{width:100%;height:auto;display:block;touch-action:none}}
.chart-tooltip{{position:absolute;background:var(--ink);color:var(--paper);padding:6px 8px;border-radius:8px;font-size:12px;pointer-events:none}}
.chart-tooltip span{{display:block;opacity:.75}}[hidden]{{display:none!important}}
</style></head><body><div class="shell">
<h1>機票追蹤 Dashboard</h1><div class="sub">資料日期 {today} · {len(data['quotes'])} 個追蹤組合</div>
<div class="cards">{''.join(cards)}</div>
<p class="foot">離線檔案顯示內嵌快照；經由本機伺服器開啟時，重新整理會讀取最新資料檔。</p>
</div>
<script id="huginn-snapshot" type="application/json">{json.dumps(snapshot, ensure_ascii=False)}</script>
<script>
(() => {{
  const money = v => 'NT$' + Number(v).toLocaleString('en-US');
  document.querySelectorAll('.price-chart').forEach(svg => {{
    const points = JSON.parse(svg.dataset.points), wrap = svg.closest('.chart-wrap');
    const tip = wrap.querySelector('.chart-tooltip'), guide = svg.querySelector('.hover-guide'), dot = svg.querySelector('.hover-dot');
    const show = (cx, cy) => {{
      const m = svg.getScreenCTM(); if (!m) return;
      const p = svg.createSVGPoint(); p.x = cx; p.y = cy; const sp = p.matrixTransform(m.inverse());
      const pt = points.reduce((b, c) => Math.abs(c.x - sp.x) < Math.abs(b.x - sp.x) ? c : b);
      const r = svg.getBoundingClientRect(), q = svg.createSVGPoint(); q.x = pt.x; q.y = pt.y; const s = q.matrixTransform(m);
      tip.innerHTML = `<span>${{pt.date}}</span><b>${{money(pt.value)}}</b>`; tip.hidden = false;
      tip.style.left = Math.max(4, Math.min(r.width - (tip.offsetWidth || 120) - 4, s.x - r.left + 12)) + 'px';
      tip.style.top = Math.max(4, s.y - r.top - 60) + 'px';
      guide.hidden = dot.hidden = false; guide.setAttribute('x1', pt.x); guide.setAttribute('x2', pt.x); dot.setAttribute('cx', pt.x); dot.setAttribute('cy', pt.y);
    }};
    svg.addEventListener('pointermove', e => show(e.clientX, e.clientY));
    svg.addEventListener('pointerdown', e => show(e.clientX, e.clientY));
    svg.addEventListener('pointerleave', () => {{ tip.hidden = guide.hidden = dot.hidden = true; }});
  }});
  if (!/^https?:$/.test(location.protocol)) return;
  fetch({json.dumps(sidecar.name)}, {{cache: 'no-store'}}).then(r => r.ok ? r.json() : Promise.reject(r.status)).then(fresh => {{
    const embedded = JSON.parse(document.getElementById('huginn-snapshot').textContent);
    if (fresh.HUGINN_GENERATED_AT && fresh.HUGINN_GENERATED_AT !== embedded.HUGINN_GENERATED_AT) location.reload();
  }}).catch(() => {{}});
}})();
</script></body></html>"""
    out_base.parent.mkdir(parents=True, exist_ok=True)
    out_base.with_suffix(".html").write_text(page, encoding="utf-8")
    sidecar.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    return out_base.with_suffix(".html"), sidecar


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, out = sys.argv[1], Path(sys.argv[2])
    data = SAMPLE if src == "--demo" else json.loads(Path(src).read_text(encoding="utf-8"))
    for p in build(data, out):
        print("wrote", p, p.stat().st_size, "bytes")
