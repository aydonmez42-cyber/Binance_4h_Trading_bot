import csv, json, os, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from scanner import snapshot as scanner_snapshot, start_scan as scanner_start, ensure_background_scan, background_loop
from bist_scanner import snapshot as bist_scanner_snapshot, start_scan as bist_scanner_start, background_loop as bist_background_loop

STATE_FILE = os.environ.get('PAPER_STATE_FILE', 'paper_state.json')
TRADES_FILE = os.environ.get('PAPER_TRADES_FILE', 'paper_trades.csv')
PORT = int(os.environ.get('PORT', '8080'))

HTML = r'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FINAL V1 Paper Trading Dashboard</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#e8ecf7;font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif} .wrap{max-width:1400px;margin:auto;padding:20px}
header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px}h1{font-size:24px;margin:0}.sub{color:#94a0ba;font-size:13px;margin-top:4px}.status{padding:8px 12px;border-radius:999px;background:#143d2a;color:#72e2a4;font-size:12px;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px}.card{background:#121a2d;border:1px solid #202b45;border-radius:14px;padding:15px}.label{color:#8e9ab4;font-size:12px}.value{font-size:23px;font-weight:750;margin-top:5px}.small{font-size:12px;color:#9ba7bf;margin-top:5px}.green{color:#65e3a1}.red{color:#ff7f8c}.yellow{color:#f6cc6d}
.section{margin-top:12px}.section h2{font-size:16px;margin:0 0 10px}.cols{display:grid;grid-template-columns:1.1fr .9fr;gap:12px}.pos{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.pill{display:inline-block;padding:5px 8px;border-radius:7px;font-size:12px;font-weight:700}.long{background:#143d2a;color:#72e2a4}.short{background:#48202b;color:#ff8b98}.flat{background:#27324b;color:#b8c1d6}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;padding:9px;border-bottom:1px solid #202b45}th{color:#8e9ab4;font-weight:600} .bar{height:10px;background:#202b45;border-radius:8px;overflow:hidden}.bar>i{display:block;height:100%;background:#65e3a1;width:0}.reason{font-size:11px;color:#9ba7bf}.footer{color:#6f7b95;font-size:11px;margin-top:14px}
.scanner-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}.scanner-actions{display:flex;gap:8px;flex-wrap:wrap}.scanner-actions input,.scanner-actions select,.scanner-actions button{background:#0d1425;color:#e8ecf7;border:1px solid #2a3857;border-radius:8px;padding:8px 10px}.scanner-actions button{cursor:pointer}.scanner-summary{display:flex;gap:16px;margin:10px 0;color:#9ba7bf;font-size:12px}.sig-long{color:#65e3a1;font-weight:800}.sig-short{color:#ff7f8c;font-weight:800}.sig-none{color:#9ba7bf;font-weight:700}.sig-error{color:#f6cc6d;font-weight:700}.clickrow{cursor:pointer}.detail{font-size:11px;color:#9ba7bf}@media(max-width:700px){.scanner-head{flex-direction:column}}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}.cols{grid-template-columns:1fr}}@media(max-width:600px){.wrap{padding:12px}.grid{grid-template-columns:1fr 1fr}.pos{grid-template-columns:1fr 1fr}.value{font-size:18px}header{align-items:flex-start}}
</style></head><body><div class="wrap">
<header><div><h1>FINAL V1 Paper Trading</h1><div class="sub">ETH 4H • REAL MARKET DATA • NO REAL ORDERS</div></div><div class="status" id="status">● BAĞLANIYOR</div></header>
<div class="grid">
<div class="card"><div class="label">Sanal Bakiye</div><div class="value" id="equity">—</div><div class="small" id="pnl">—</div></div>
<div class="card"><div class="label">ETH Fiyatı</div><div class="value" id="price">—</div><div class="small" id="priceTime">—</div></div>
<div class="card"><div class="label">Toplam İşlem</div><div class="value" id="trades">—</div><div class="small" id="winrate">—</div></div>
<div class="card"><div class="label">Profit Factor</div><div class="value" id="pf">—</div><div class="small" id="avg">—</div></div>
</div>
<div class="cols">
<div class="card section"><h2>📌 Açık Pozisyon</h2><div id="position">Pozisyon yok</div></div>
<div class="card section"><h2>🧠 FINAL V1 Sinyal Durumu</h2><div id="signals">—</div></div>
</div>
<div class="grid section">
<div class="card"><div class="label">Net P&L</div><div class="value" id="net">—</div></div>
<div class="card"><div class="label">Win Rate</div><div class="value" id="wr">—</div></div>
<div class="card"><div class="label">Max Drawdown</div><div class="value" id="dd">—</div></div>
<div class="card"><div class="label">Son Mum</div><div class="value" id="candle">—</div></div>
</div>
<div class="card section"><h2>📜 Son İşlemler</h2><div style="overflow:auto"><table><thead><tr><th>Tarih</th><th>Yön</th><th>Sembol</th><th>Entry</th><th>Exit</th><th>P&L</th><th>Çıkış</th></tr></thead><tbody id="history"></tbody></table></div></div>
<div class="card section scanner"><div class="scanner-head"><div><h2>🪙 Binance Futures — FINAL V1 Coin Scanner</h2><div class="small">USDT-M perpetual • 4H kapalı mum • Sadece sinyal taraması • Gerçek emir yok</div></div><div class="scanner-actions"><input id="coinSearch" placeholder="Coin ara..." oninput="renderScanner()"><select id="signalFilter" onchange="renderScanner()"><option value="ALL">Tümü</option><option value="LONG">LONG</option><option value="SHORT">SHORT</option><option value="NO SIGNAL">NO SIGNAL</option></select><button onclick="startScanner(true)">🔄 Tümünü Tara</button></div></div><div class="small" id="scannerStatus">Hazırlanıyor...</div><div class="scanner-summary"><span id="coinCount">0 coin</span><span id="longCount">LONG 0</span><span id="shortCount">SHORT 0</span><span id="noCount">NO SIGNAL 0</span></div><div style="overflow:auto;max-height:620px"><table><thead><tr><th>Coin</th><th>Fiyat</th><th>24s %</th><th>Hacim</th><th>ST</th><th>ADX</th><th>RSI</th><th>CCI</th><th>MACD</th><th>ATRP %ile</th><th>Sinyal</th><th>Açıklama</th></tr></thead><tbody id="scannerRows"><tr><td colspan="12">Tarama bekleniyor...</td></tr></tbody></table></div></div><div class="card section scanner"><div class="scanner-head"><div><h2>🇹🇷 XUTUM — TEST32 RSI72 Scanner</h2><div class="small">XUTUM • TradingView Screener evreni • tüm BIST common hisseleri • 4H kapalı mum • TEST32 RSI72 teknik koşulları • Gözlem/sinyal amaçlı • Gerçek emir yok</div></div><div class="scanner-actions"><input id="bistSearch" placeholder="Hisse ara..." oninput="renderBistScanner()"><select id="bistSignalFilter" onchange="renderBistScanner()"><option value="ALL">Tümü</option><option value="LONG">LONG</option><option value="SHORT">SHORT</option><option value="NO SIGNAL">NO SIGNAL</option></select><button onclick="startBistScanner(true)">🔄 XUTUM Tara</button></div></div><div class="small" id="bistScannerStatus">Hazırlanıyor...</div><div class="scanner-summary"><span id="bistCount">0 hisse</span><span id="bistLongCount">LONG 0</span><span id="bistShortCount">SHORT 0</span><span id="bistNoCount">NO SIGNAL 0</span></div><div style="overflow:auto;max-height:620px"><table><thead><tr><th>Hisse</th><th>Fiyat</th><th>Değişim</th><th>ST</th><th>ADX</th><th>RSI</th><th>CCI</th><th>MACD</th><th>Stoch K/D</th><th>ATRP %ile</th><th>Sinyal</th><th>Açıklama</th></tr></thead><tbody id="bistScannerRows"><tr><td colspan="12">Tarama bekleniyor...</td></tr></tbody></table></div><div class="small">Not: SHORT burada yalnızca stratejinin teknik sinyalidir; BIST spot piyasasında doğrudan açığa satış emri anlamına gelmez.</div></div><div class="footer">Otomatik yenileme: 10 sn • Paper trading, gerçek emir yok.</div>
</div>
<script>
const money=x=>x==null?'—':'$'+Number(x).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
const num=x=>x==null?'—':Number(x).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
function cls(x){return Number(x)>=0?'green':'red'}
function render(d){
 document.getElementById('status').textContent=d.bot_alive?'● BOT AKTİF':'● BEKLEMEDE';
 document.getElementById('status').style.background=d.bot_alive?'#143d2a':'#3c3020'; document.getElementById('status').style.color=d.bot_alive?'#72e2a4':'#f6cc6d';
 document.getElementById('equity').textContent=money(d.equity); document.getElementById('pnl').innerHTML='<span class="'+cls(d.net_pnl)+'">'+money(d.net_pnl)+'</span> • '+Number(d.return_pct||0).toFixed(2)+'%';
 document.getElementById('price').textContent=money(d.price); document.getElementById('priceTime').textContent=d.price_time||'—';
 document.getElementById('trades').textContent=d.stats.trades; document.getElementById('winrate').textContent='Win rate '+d.stats.win_rate.toFixed(2)+'%'; document.getElementById('pf').textContent=d.stats.profit_factor.toFixed(3); document.getElementById('avg').textContent='Ort. '+money(d.stats.avg_trade);
 document.getElementById('net').innerHTML='<span class="'+cls(d.net_pnl)+'">'+money(d.net_pnl)+'</span>'; document.getElementById('wr').textContent=d.stats.win_rate.toFixed(2)+'%'; document.getElementById('dd').textContent=d.stats.max_drawdown.toFixed(2)+'%'; document.getElementById('candle').textContent=d.last_closed_time||'—';
 const p=d.position;
 if(!p){document.getElementById('position').innerHTML='<span class="pill flat">FLAT</span><div class="small" style="margin-top:10px">Açık paper pozisyon yok.</div>'}
 else {let pnl=p.unrealized_pnl; document.getElementById('position').innerHTML=`<div class="pos"><div><div class="label">Yön / Sembol</div><div class="value"><span class="pill ${p.side.toLowerCase()}">${p.side}</span> ${p.symbol}</div></div><div><div class="label">Giriş / Güncel</div><div class="value">${num(p.entry_price)} / ${num(p.current_price)}</div></div><div><div class="label">Unrealized P&L</div><div class="value ${cls(pnl)}">${money(pnl)}</div></div><div><div class="label">ATR</div><div class="value">${num(p.atr)}</div></div><div><div class="label">Stop</div><div class="value">${num(p.active_stop)}</div></div><div><div class="label">TP</div><div class="value">${num(p.tp)}</div></div></div><div class="small">Trailing: ${p.trail_active?'AKTİF @ '+num(p.trail_stop):'Beklemede'} • Giriş: ${p.entry_time}</div>`}
 const s=d.signals||{}; document.getElementById('signals').innerHTML=`<table><tbody>${[['EMA 50 / 200',s.ema],['Supertrend',s.supertrend],['ADX',s.adx],['RSI',s.rsi],['CCI',s.cci],['Stoch RSI',s.stoch],['MACD',s.macd],['1D Volatilite',s.volatility],['1D ATRP %ile',s.atrp_percentile_1d],['Son sinyal',s.final]].map(r=>`<tr><td>${r[0]}</td><td><b>${r[1]??'—'}</b></td></tr>`).join('')}</tbody></table>`;
 document.getElementById('history').innerHTML=d.history.map(t=>`<tr><td>${t.exit_time||'—'}</td><td><span class="pill ${String(t.side).toLowerCase()}">${t.side}</span></td><td>${t.symbol}</td><td>${num(t.entry_price)}</td><td>${num(t.exit_price)}</td><td class="${cls(t.net_pnl)}"><b>${money(t.net_pnl)}</b></td><td class="reason">${t.reason}</td></tr>`).join('') || '<tr><td colspan="7">Henüz kapanmış işlem yok.</td></tr>';
}
async function scannerData(){try{let r=await fetch('/api/scanner',{cache:'no-store'});return await r.json()}catch(e){return {status:'ERROR',results:[],last_error:String(e)}}}
function sigClass(x){return x==='LONG'?'sig-long':x==='SHORT'?'sig-short':x==='ERROR'?'sig-error':'sig-none'}
let scannerCache={results:[]};
function renderScanner(){let q=(document.getElementById('coinSearch')?.value||'').toUpperCase();let f=document.getElementById('signalFilter')?.value||'ALL';let rows=scannerCache.results.filter(x=>(!q||x.symbol.includes(q))&&(f==='ALL'||x.signal===f));document.getElementById('scannerRows').innerHTML=rows.map(x=>`<tr class="clickrow"><td><b>${x.symbol}</b></td><td>${num(x.price)}</td><td class="${Number(x.change_pct)>=0?'green':'red'}">${Number(x.change_pct||0).toFixed(2)}%</td><td>${Number(x.volume||0).toLocaleString('en-US',{maximumFractionDigits:0})}</td><td>${x.st||'—'}</td><td>${x.adx??'—'}</td><td>${x.rsi??'—'}</td><td>${x.cci??'—'}</td><td>${x.macd||'—'}</td><td>${x.atrp_percentile_1d??'—'}</td><td class="${sigClass(x.signal)}">${x.signal}</td><td class="detail">${x.reason||''}</td></tr>`).join('')||'<tr><td colspan="12">Sonuç yok.</td></tr>';document.getElementById('coinCount').textContent=rows.length+' coin';document.getElementById('longCount').textContent='LONG '+rows.filter(x=>x.signal==='LONG').length;document.getElementById('shortCount').textContent='SHORT '+rows.filter(x=>x.signal==='SHORT').length;document.getElementById('noCount').textContent='NO SIGNAL '+rows.filter(x=>x.signal==='NO SIGNAL').length;}
async function bistScannerData(){try{let r=await fetch('/api/bist-scanner',{cache:'no-store'});return await r.json()}catch(e){return {status:'ERROR',results:[],last_error:String(e)}}}
let bistScannerCache={results:[]};
function renderBistScanner(){let q=(document.getElementById('bistSearch')?.value||'').toUpperCase();let f=document.getElementById('bistSignalFilter')?.value||'ALL';let rows=bistScannerCache.results.filter(x=>(!q||x.symbol.includes(q))&&(f==='ALL'||x.signal===f));document.getElementById('bistScannerRows').innerHTML=rows.map(x=>`<tr class="clickrow"><td><b>${x.symbol}</b></td><td>${num(x.price)}</td><td class="${Number(x.change_pct)>=0?'green':'red'}">${Number(x.change_pct||0).toFixed(2)}%</td><td>${x.st||'—'}</td><td>${x.adx??'—'}</td><td>${x.rsi??'—'}</td><td>${x.cci??'—'}</td><td>${x.macd||'—'}</td><td>${x.stoch_k??'—'} / ${x.stoch_d??'—'}</td><td>${x.atrp_percentile_1d??'—'}</td><td class="${sigClass(x.signal)}">${x.signal}</td><td class="detail">${x.reason||''}</td></tr>`).join('')||'<tr><td colspan="12">Sonuç yok.</td></tr>';document.getElementById('bistCount').textContent=rows.length+' hisse';document.getElementById('bistLongCount').textContent='LONG '+rows.filter(x=>x.signal==='LONG').length;document.getElementById('bistShortCount').textContent='SHORT '+rows.filter(x=>x.signal==='SHORT').length;document.getElementById('bistNoCount').textContent='NO SIGNAL '+rows.filter(x=>x.signal==='NO SIGNAL').length;}
async function refreshBistScanner(){let d=await bistScannerData();bistScannerCache=d;let st=d.status||'IDLE';let src=d.universe_source?` • Evren: ${d.universe_source}`:'';let txt=st==='SCANNING'?`XUTUM taraması: ${d.symbols_done||0}/${d.symbols_total||0}`:st==='READY'?`Hazır • Son 4H: ${d.last_scan_candle||'—'}${src}`:st==='ERROR'?`Hata: ${d.last_error||'Bilinmeyen hata'}`:'Bekleniyor...';document.getElementById('bistScannerStatus').textContent=txt;renderBistScanner();}
async function startBistScanner(force=false){document.getElementById('bistScannerStatus').textContent='XUTUM taraması başlatılıyor...';try{await fetch('/api/bist-scanner/scan?force='+(force?'1':'0'),{cache:'no-store'})}catch(e){}refreshBistScanner();}
refreshBistScanner();setInterval(refreshBistScanner,10000);
async function refreshScanner(){let d=await scannerData();scannerCache=d;let st=d.status||'IDLE';let txt=st==='SCANNING'?`Tarama yapılıyor: ${d.symbols_done||0}/${d.symbols_total||0}`:st==='READY'?`Hazır • Son 4H tarama: ${d.last_scan_candle||'—'}`:st==='ERROR'?`Hata: ${d.last_error||'Bilinmeyen hata'}`:'Bekleniyor...';document.getElementById('scannerStatus').textContent=txt;renderScanner();}
async function startScanner(force=false){document.getElementById('scannerStatus').textContent='Tarama başlatılıyor...';try{await fetch('/api/scanner/scan?force='+(force?'1':'0'),{cache:'no-store'})}catch(e){}refreshScanner();}
refreshScanner();setInterval(refreshScanner,10000);
async function refresh(){try{let r=await fetch('/api/status',{cache:'no-store'});let d=await r.json();render(d)}catch(e){document.getElementById('status').textContent='● BAĞLANTI HATASI'}} refresh();setInterval(refresh,5000);
</script></body></html>'''

def read_state():
    try:
        with open(STATE_FILE,'r',encoding='utf-8') as f:return json.load(f)
    except Exception:return {}

def read_trades():
    if not os.path.exists(TRADES_FILE): return []
    try:
        with open(TRADES_FILE,'r',encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
    except Exception:return []

def f(v):
    try:return float(v)
    except:return 0.0

def status():
    s=read_state(); trades=read_trades(); closed=[]
    for t in trades:
        for k in ['entry_price','exit_price','net_pnl','gross_pnl','fees','equity_after','qty_eth']:
            if k in t:t[k]=f(t[k])
        closed.append(t)
    wins=sum(1 for t in closed if t.get('net_pnl',0)>0); losses=sum(1 for t in closed if t.get('net_pnl',0)<0)
    gross_win=sum(t['net_pnl'] for t in closed if t['net_pnl']>0); gross_loss=abs(sum(t['net_pnl'] for t in closed if t['net_pnl']<0))
    pf=gross_win/gross_loss if gross_loss else (999.0 if gross_win else 0.0)
    avg=sum(t['net_pnl'] for t in closed)/len(closed) if closed else 0
    start=float(os.environ.get('PAPER_INITIAL_CAPITAL','10000'))
    equity=f(s.get('equity',start)); net=equity-start
    peak=start; maxdd=0
    for t in closed:
        e=f(t.get('equity_after',start)); peak=max(peak,e); maxdd=min(maxdd,(e/peak-1)*100 if peak else 0)
    p=s.get('position'); pos=None
    if p:
        cp=f(s.get('market_prices',{}).get(p.get('symbol'),p.get('entry_price')))
        qty=f(p.get('qty_eth',1)); ep=f(p.get('entry_price')); unreal=(cp-ep)*qty if p.get('side')=='LONG' else (ep-cp)*qty
        active=f(p.get('trail_stop')) if p.get('trail_active') and p.get('trail_stop') is not None else f(p.get('sl'))
        pos={**p,'current_price':cp,'unrealized_pnl':unreal,'active_stop':active}
    indicators=s.get('indicators',{})
    return {'bot_alive': bool(s.get('last_heartbeat')),'heartbeat':s.get('last_heartbeat'),'equity':equity,'net_pnl':net,'return_pct':net/start*100,'price':f(s.get('market_prices',{}).get('ETHUSDT',0)),'price_time':s.get('market_price_time'),'last_closed_time':s.get('last_closed_time'),'position':pos,'signals':s.get('signals',indicators),'stats':{'trades':len(closed),'wins':wins,'losses':losses,'win_rate':wins/len(closed)*100 if closed else 0,'profit_factor':pf,'avg_trade':avg,'max_drawdown':maxdd},'history':list(reversed(closed[-20:]))}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/status':
            body=json.dumps(status(),ensure_ascii=False).encode(); self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        if path=='/health':
            body=b'OK'; self.send_response(200); self.send_header('Content-Type','text/plain; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        if path=='/api/bist-scanner':
            body=json.dumps(bist_scanner_snapshot(),ensure_ascii=False).encode(); self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        if path=='/api/bist-scanner/scan':
            q=parse_qs(urlparse(self.path).query); force=q.get('force',['0'])[0]=='1'
            started=bist_scanner_start(force=force)
            body=json.dumps({'started':started,'status':bist_scanner_snapshot().get('status')}).encode(); self.send_response(202 if started else 200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        if path=='/api/scanner':
            body=json.dumps(scanner_snapshot(),ensure_ascii=False).encode(); self.send_response(200); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        if path=='/api/scanner/scan':
            q=parse_qs(urlparse(self.path).query); force=q.get('force',['0'])[0]=='1'
            started=scanner_start(force=force)
            body=json.dumps({'started':started,'status':scanner_snapshot().get('status')}).encode(); self.send_response(202 if started else 200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        body=HTML.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args):return

def start_dashboard():
    server=ThreadingHTTPServer(('0.0.0.0',PORT),Handler)
    print(f'DASHBOARD | http://0.0.0.0:{PORT} | PAPER ONLY + COIN SCANNER',flush=True)
    threading.Thread(target=background_loop, daemon=True).start()
    threading.Thread(target=bist_background_loop, daemon=True).start()
    server.serve_forever()
