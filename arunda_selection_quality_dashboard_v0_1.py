"""Local, read-only dashboard for ArundaTrader selection-quality evidence.

Binds to loopback by default, reads only the append-only real-observation JSONL
stream, and never calls an exchange, writes the DB, or enables execution.
Run: python arunda_selection_quality_dashboard_v0_1.py
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from global_selection_outcome_tracker_v0_1 import DEFAULT_STREAM_PATH, load_events
from global_selection_quality_report_v0_1 import build_quality_report

HTML = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ArundaTrader | کیفیت انتخاب ارزها</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#141c30;--line:#27344e;--text:#eaf0ff;--muted:#aab7d0;--accent:#70d6b3;--warn:#f5c66a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.7 Segoe UI,Tahoma,sans-serif}
main{max-width:1200px;margin:auto;padding:24px}header{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap}
h1{font-size:25px;margin:0}h2{font-size:18px;margin:0 0 12px}.muted{color:var(--muted)}.status{color:var(--accent);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:22px 0}
.card,section{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}
.metric{font-size:28px;font-weight:700;direction:ltr;text-align:right}.label{color:var(--muted);font-size:13px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.tabs button,button{background:#202d46;color:var(--text);border:1px solid var(--line);border-radius:9px;padding:8px 13px;cursor:pointer}
.tabs button.active{border-color:var(--accent);color:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:right;padding:10px 8px;border-bottom:1px solid var(--line);white-space:nowrap}th{color:var(--muted);font-weight:500}
.wrap{overflow-x:auto}.empty{padding:20px;color:var(--muted);text-align:center}.notice{border-right:3px solid var(--warn);padding:10px 13px;color:var(--muted);margin:16px 0}
footer{color:var(--muted);font-size:12px;margin-top:18px}@media(max-width:600px){main{padding:14px}h1{font-size:20px}.metric{font-size:24px}}
</style></head>
<body><main>
<header><div><h1>آروندا تریدر — کیفیت انتخاب ارزها</h1><div class="muted">شواهد واقعی بازار · داشبورد فقط‌خواندنی</div></div>
<div><div id="status" class="status">در حال خواندن شواهد…</div><button id="refresh">به‌روزرسانی</button></div></header>
<div class="cards" id="metrics"></div>
<section><h2>رتبه‌بندی توصیفی دارایی‌ها</h2><div class="tabs" id="tabs">
<button data-h="1h" class="active">۱ ساعت</button><button data-h="4h">۴ ساعت</button><button data-h="24h">۲۴ ساعت</button></div>
<div class="wrap"><table><thead><tr><th>دارایی</th><th>نمونه معتبر</th><th>نرخ برد</th><th>میانگین بازده جهت‌دار</th><th>میانه بازده</th><th>حرکت مطلوب متوسط</th><th>حرکت نامطلوب متوسط</th></tr></thead><tbody id="rows"></tbody></table></div>
<div id="empty" class="empty" hidden>هنوز نمونه واقعی کافی برای رتبه‌بندی وجود ندارد؛ این وضعیت با داده ساختگی پر نمی‌شود.</div></section>
<div class="notice">این رتبه‌بندی توصیفی است، نه سیگنال معامله. نمونه‌های کمتر از حداقل تعیین‌شده رتبه نمی‌گیرند؛ افق‌های زمانی ناقص، زیان محسوب نمی‌شوند.</div>
<section><h2>وضعیت شواهد</h2><div id="details" class="muted">—</div></section>
<footer>منبع: runtime_observations/global_selection_outcomes.jsonl · بدون تماس با صرافی · بدون تغییر پایگاه‌داده یا وضعیت اجرا</footer>
</main><script>
let report=null, horizon='1h';
const esc=(v)=>String(v).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));\nconst fmt=(v,suffix='')=>v===null||v===undefined?'—':Number(v).toLocaleString('en-US',{maximumFractionDigits:2})+suffix;
function metric(label,value){return '<div class="card"><div class="label">'+label+'</div><div class="metric">'+value+'</div></div>'}
function render(){
 if(!report)return;
 const o=report.overall||{};
 document.getElementById('metrics').innerHTML=[
 metric('کل انتخاب‌ها',fmt(report.selection_count)),
 metric('نمونه‌های ارزیابی‌شده در ۱س',fmt(o.horizons?.['1h']?.direction_scored_count??0)),
 metric('نرخ برد ۱س',fmt(o.horizons?.['1h']?.win_rate_pct,'%')),
 metric('بازده میانه ۱س',fmt(o.horizons?.['1h']?.median_directional_return_pct,'%'))
 ].join('');
 const rows=report.rankings_by_horizon?.[horizon]||[];
 document.getElementById('rows').innerHTML=rows.map(r=>'<tr><td><b>'+esc(r.asset)+'</b></td><td>'+fmt(r.sample_count)+'</td><td>'+fmt(r.win_rate_pct,'%')+'</td><td>'+fmt(r.mean_directional_return_pct,'%')+'</td><td>'+fmt(r.median_directional_return_pct,'%')+'</td><td>'+fmt(r.mean_max_favorable_excursion_pct,'%')+'</td><td>'+fmt(r.mean_max_adverse_excursion_pct,'%')+'</td></tr>').join('');
 document.getElementById('empty').hidden=rows.length>0;
 document.getElementById('details').textContent='حداقل نمونه برای رتبه‌بندی: '+report.min_sample_size+' | مبنای شواهد: بازار واقعی | رویدادهای انتخاب: '+report.selection_count+' | گزارش صرفاً توصیفی است.';
}
async function refresh(){
 const s=document.getElementById('status');s.textContent='در حال به‌روزرسانی…';
 try{const r=await fetch('/api/report',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);report=await r.json();render();s.textContent='آخرین به‌روزرسانی: '+new Date().toLocaleTimeString('fa-IR');}
 catch(e){s.textContent='خواندن شواهد ناموفق بود: '+e.message;document.getElementById('empty').hidden=false;}
}
document.getElementById('refresh').addEventListener('click',refresh);
document.querySelectorAll('[data-h]').forEach(b=>b.addEventListener('click',()=>{horizon=b.dataset.h;document.querySelectorAll('[data-h]').forEach(x=>x.classList.toggle('active',x===b));render()}));
refresh();setInterval(refresh,60000);
</script></body></html>"""


def make_handler(stream_path: Path, min_sample_size: int):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            route = urlparse(self.path).path
            if route == "/":
                payload = HTML.encode("utf-8")
                content_type = "text/html; charset=utf-8"
            elif route == "/api/report":
                try:
                    report = build_quality_report(
                        load_events(stream_path), min_sample_size=min_sample_size
                    )
                    payload = (json.dumps(report, ensure_ascii=False) + "\n").encode("utf-8")
                    content_type = "application/json; charset=utf-8"
                except (OSError, ValueError, json.JSONDecodeError) as exc:
                    payload = json.dumps(
                        {"error": "EVIDENCE_READ_FAILED", "detail": str(exc)},
                        ensure_ascii=False,
                    ).encode("utf-8")
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
            else:
                payload = b'{"error":"NOT_FOUND"}'
                content_type = "application/json; charset=utf-8"
                self.send_response(404)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            # Keep routine dashboard refreshes quiet; never log evidence payloads.
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Loopback only by default.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--input", type=Path, default=DEFAULT_STREAM_PATH)
    parser.add_argument("--min-sample-size", type=int, default=5)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("refusing non-loopback host; remote exposure is not supported")
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.min_sample_size < 1:
        parser.error("--min-sample-size must be positive")
    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.input, args.min_sample_size))
    print(f"ArundaTrader read-only dashboard: http://{args.host}:{args.port}")
    print(f"Evidence stream: {args.input}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
