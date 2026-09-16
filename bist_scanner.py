import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd
import requests

import config as cfg
from indicators import add_indicators, atr
from strategy import long_signal, short_signal

# BIST scanner is OBSERVATION ONLY. It never places orders.
BIST100_SOURCE_URL = os.environ.get(
    'BIST100_SOURCE_URL',
    'https://www.cnbce.com/borsa/hisseler/bist-100-hisseleri'
)
BIST_TUM100_SOURCE_URL = os.environ.get(
    'BIST_TUM100_SOURCE_URL',
    'https://www.cnbce.com/borsa/endeksler/bist-tum-100'
)
YAHOO_CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'

BIST_SCANNER_WORKERS = int(os.environ.get('BIST_SCANNER_WORKERS', '6'))
BIST_SCANNER_CACHE_SECONDS = int(os.environ.get('BIST_SCANNER_CACHE_SECONDS', '900'))
BIST_HOURS_LOOKBACK_DAYS = int(os.environ.get('BIST_HOURS_LOOKBACK_DAYS', '365'))
BIST_MIN_4H_BARS = int(os.environ.get('BIST_MIN_4H_BARS', '230'))

# Fallback universe based on the 2026 BIST-100 universe used in project research.
# Runtime source is preferred so periodic index changes are picked up automatically.
BIST100_FALLBACK = '''
AEFES AGHOL AKBNK AKSA AKSEN ALARK ALTNY ANSGR ARCLK ASELS ASTOR BALSU BIMAS BRSAN BRYAT BSOKE BTCIM CANTE CCOLA CIMSA CVKMD CWENE DAPGM DOAS DOHOL DSTKF ECILC EFOR EKGYO ENERY ENJSA ENKAI EREGL EUPWR EUREN FENER FROTO GARAN GENIL GESAN GLRMK GRSEL GRTHO GSRAY GUBRF HALKB HEKTS ISCTR ISMEN IZENR KCHOL KLRHO KONTR KRDMD KTLEV KUYAS MAGEN MAVI MGROS MIATK MPARK OBAMS ODAS OTKAR OYAKC PAHOL PASEU PATEK PETKM PGSUS PSGYO QUAGR RALYH REEDR SAHOL SARKY SASA SISE SKBNK SOKM TABGD TAVHL TCELL THYAO TKFEN TOASO TRALT TRENJ TRMET TSKB TUKAS TUPRS TUREX TURSG ULKER VAKBN VESTL YKBNK ZOREN
ESEN IEYHO ODINE
'''.split()

_lock = threading.Lock()
_state = {
    'status': 'IDLE',
    'started_at': None,
    'finished_at': None,
    'last_error': None,
    'symbols_total': 0,
    'symbols_done': 0,
    'results': [],
    'last_scan_candle': None,
    'universe_source': None,
}


def _get(url, params=None, timeout=20):
    r = requests.get(url, params=params, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0'})
    r.raise_for_status()
    return r


def _parse_cnbce_symbols(html):
    # CNBC-E links use /borsa/hisseler/<symbol>-<slug>.
    found = re.findall(r'/borsa/hisseler/([a-z0-9]+)-', html, flags=re.I)
    symbols = []
    seen = set()
    for s in found:
        s = s.upper()
        if s not in seen and 2 <= len(s) <= 8:
            seen.add(s)
            symbols.append(s)
    return set(symbols)


def get_bist_tum_symbols():
    """
    Get the current BIST Tüm universe. BIST Tüm is BIST 100 plus
    BIST Tüm-100, so the scanner combines those two live universes.
    """
    try:
        h100 = _get(BIST100_SOURCE_URL, timeout=20).text
        htum100 = _get(BIST_TUM100_SOURCE_URL, timeout=20).text
        s100 = _parse_cnbce_symbols(h100)
        stum100 = _parse_cnbce_symbols(htum100)
        symbols = sorted(s100 | stum100)
        # BIST Tüm should be materially larger than BIST 100.
        if len(symbols) >= 150:
            with _lock:
                _state['universe_source'] = f'CNBC-E dynamic BIST100 + BIST TUM-100 ({len(symbols)})'
            return symbols
    except Exception as exc:
        with _lock:
            _state['last_error'] = f'BIST Tüm universe source: {exc}'
    with _lock:
        _state['universe_source'] = 'project fallback (BIST100)'
    return sorted(set(BIST100_FALLBACK))


def get_bist100_symbols():
    # Backward-compatible alias.
    return get_bist_tum_symbols()


def fetch_yahoo_1h(symbol):
    now = int(time.time())
    period1 = now - BIST_HOURS_LOOKBACK_DAYS * 86400
    period2 = now
    r = _get(
        YAHOO_CHART_URL.format(symbol=f'{symbol}.IS'),
        params={'period1': period1, 'period2': period2, 'interval': '1h', 'events': 'history', 'includeAdjustedClose': 'true'},
        timeout=25,
    )
    payload = r.json().get('chart', {}).get('result', [])
    if not payload:
        raise RuntimeError('Yahoo veri döndürmedi')
    item = payload[0]
    timestamps = item.get('timestamp', [])
    q = item.get('indicators', {}).get('quote', [{}])[0]
    if not timestamps:
        raise RuntimeError('Yahoo candle verisi boş')
    df = pd.DataFrame({
        'timestamp': pd.to_datetime(timestamps, unit='s', utc=True),
        'open': q.get('open', []),
        'high': q.get('high', []),
        'low': q.get('low', []),
        'close': q.get('close', []),
        'volume': q.get('volume', []),
    })
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['open', 'high', 'low', 'close']).copy()
    return df


def make_4h(df):
    """Build exchange-session 4H bars: 10:00-14:00 and 14:00-18:00 Europe/Istanbul."""
    if df.empty:
        return df
    x = df.copy().set_index('timestamp').sort_index()
    x = x.tz_convert('Europe/Istanbul')
    # Only BIST regular continuous session. Yahoo can contain odd pre/post bars.
    x = x[(x.index.hour >= 10) & (x.index.hour < 18)]
    if x.empty:
        return x.reset_index()
    # Session-anchored 4H bins.
    out = x.resample('4h', origin='start_day', offset='10h', label='right', closed='right').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    })
    counts = x['close'].resample('4h', origin='start_day', offset='10h', label='right', closed='right').count()
    out = out[counts >= 3].dropna(subset=['open', 'high', 'low', 'close'])
    out.index.name = 'close_time'
    out = out.reset_index()
    return out


def daily_atrp_percentile(symbol):
    try:
        df = fetch_yahoo_1h(symbol)
        d = df.set_index('timestamp').tz_convert('Europe/Istanbul').resample('1D').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna()
        if len(d) < cfg.VOLATILITY_PERCENTILE_LENGTH + 30:
            return None
        d['atr'] = atr(d['high'], d['low'], d['close'], cfg.VOLATILITY_ATR_LENGTH)
        d['atrp'] = d['atr'] / d['close'] * 100
        s = d['atrp'].dropna()
        if len(s) < cfg.VOLATILITY_PERCENTILE_LENGTH:
            return None
        latest = float(s.iloc[-1])
        window = s.iloc[-cfg.VOLATILITY_PERCENTILE_LENGTH:]
        return float((window <= latest).mean() * 100)
    except Exception:
        return None


def _reason_map(row):
    long_checks = {
        'EMA200 trend': bool(row.close > row.ema100),
        'EMA50 > EMA200': bool(row.ema50 > row.ema100),
        'ADX > threshold': bool(row.adx > cfg.ADX_THRESHOLD),
        'Supertrend bullish': bool(row.supertrend_bullish),
        'RSI 55–72': bool(row.rsi > cfg.RSI_LONG_THRESHOLD and row.rsi <= cfg.RSI_LONG_MAX),
        'MACD bullish': bool(row.macd_long_ok) if cfg.USE_MACD_LONG_FILTER else True,
        'CCI > 100': bool(row.cci > cfg.CCI_LONG_THRESHOLD),
        'Stoch cross': bool(row.stoch_bull_cross),
        'Stoch D > 30': bool(row.stoch_d > cfg.STOCH_LONG_D_THRESHOLD),
    }
    short_checks = {
        'EMA200 trend': bool(row.close < row.ema100),
        'EMA50 < EMA200': bool(row.ema50 < row.ema100),
        'ADX > threshold': bool(row.adx > cfg.ADX_THRESHOLD),
        'Supertrend bearish': bool(row.supertrend_bearish),
        'RSI < 30': bool(row.rsi < cfg.RSI_SHORT_THRESHOLD),
        'CCI < -50': bool(row.cci < cfg.CCI_SHORT_THRESHOLD),
        'Stoch cross': bool(row.stoch_bear_cross),
        'Stoch K < 80': bool(row.stoch_k < cfg.STOCH_SHORT_THRESHOLD),
    }
    return long_checks, short_checks


def scan_symbol(symbol):
    try:
        df1 = fetch_yahoo_1h(symbol)
        df = make_4h(df1)
        if len(df) < BIST_MIN_4H_BARS + 5:
            return {'symbol': symbol, 'market': 'BIST_TUM', 'signal': 'DATA', 'reason': f'Yetersiz 4H veri ({len(df)})'}

        # The last bar may still be forming. Use only fully closed session bars.
        now_tr = pd.Timestamp.now(tz='Europe/Istanbul')
        closed = df[df['close_time'] <= now_tr].copy()
        # If the latest bar ends in the future, exclude it.
        if closed.empty:
            return {'symbol': symbol, 'market': 'BIST_TUM', 'signal': 'DATA', 'reason': 'Kapalı 4H mum yok'}

        enriched = add_indicators(closed, cfg)
        i = len(enriched) - 1
        row = enriched.iloc[i]
        long_ok = long_signal(enriched, i, cfg)
        short_ok = short_signal(enriched, i, cfg)
        atrp_pct = daily_atrp_percentile(symbol) if (long_ok or short_ok) else None
        volatile = False
        if cfg.USE_VOLATILE_FILTER and atrp_pct is not None:
            volatile = bool(atrp_pct > cfg.VOLATILITY_HIGH_PERCENTILE or atrp_pct < cfg.VOLATILITY_LOW_PERCENTILE)
            if volatile:
                long_ok = short_ok = False

        sig = 'LONG' if long_ok else ('SHORT' if short_ok else 'NO SIGNAL')
        long_checks, short_checks = _reason_map(row)
        if volatile:
            reason = f'1D VOLATILE BLOCK | ATRP percentile={atrp_pct:.1f}'
        elif sig == 'LONG':
            reason = 'TEST32 RSI72 LONG koşulları sağlandı'
        elif sig == 'SHORT':
            reason = 'TEST32 SHORT koşulları sağlandı'
        else:
            fl = [k for k, v in long_checks.items() if not v]
            fs = [k for k, v in short_checks.items() if not v]
            reason = 'LONG eksik: ' + ', '.join(fl[:3]) + ' | SHORT eksik: ' + ', '.join(fs[:3])

        last = df1.iloc[-1]
        prev_day = df1[df1['timestamp'].dt.date < last['timestamp'].date()]
        # 24h proxy from last available hourly close vs roughly one session/day ago.
        if len(df1) > 8:
            base = float(df1.iloc[-9]['close'])
            change = (float(last['close']) / base - 1) * 100 if base else 0
        else:
            change = 0
        return {
            'symbol': symbol,
            'market': 'BIST_TUM',
            'signal': sig,
            'price': round(float(last['close']), 4),
            'change_pct': round(float(change), 2),
            'volume': round(float(last.get('volume', 0) or 0), 0),
            'rsi': round(float(row.rsi), 2),
            'adx': round(float(row.adx), 2),
            'cci': round(float(row.cci), 2),
            'st': 'BULL' if row.supertrend_bullish else 'BEAR',
            'macd': 'BULL' if row.macd_long_ok else 'BEAR',
            'stoch_k': round(float(row.stoch_k), 2),
            'stoch_d': round(float(row.stoch_d), 2),
            'atr': round(float(row.atr), 6),
            'atrp_percentile_1d': round(float(atrp_pct), 2) if atrp_pct is not None else None,
            'candle_time': pd.Timestamp(row.close_time).isoformat(),
            'reason': reason,
            'short_note': 'Teknik SHORT sinyali; BIST spotta doğrudan short işlem anlamına gelmez.',
        }
    except Exception as e:
        return {'symbol': symbol, 'market': 'BIST_TUM', 'signal': 'ERROR', 'reason': str(e)[:180]}


def _scan_worker(symbols):
    with _lock:
        _state.update(status='SCANNING', started_at=datetime.now(timezone.utc).isoformat(), finished_at=None,
                      last_error=None, symbols_total=len(symbols), symbols_done=0)
    try:
        results = []
        with ThreadPoolExecutor(max_workers=BIST_SCANNER_WORKERS) as ex:
            futs = {ex.submit(scan_symbol, s): s for s in symbols}
            for fut in as_completed(futs):
                results.append(fut.result())
                with _lock:
                    _state['symbols_done'] += 1
        results.sort(key=lambda x: (0 if x.get('signal') == 'LONG' else 1 if x.get('signal') == 'SHORT' else 2, x.get('symbol', '')))
        candle_times = [r.get('candle_time') for r in results if r.get('candle_time')]
        with _lock:
            _state['results'] = results
            _state['status'] = 'READY'
            _state['finished_at'] = datetime.now(timezone.utc).isoformat()
            _state['last_scan_candle'] = max(candle_times) if candle_times else None
    except Exception as e:
        with _lock:
            _state['status'] = 'ERROR'
            _state['last_error'] = str(e)
            _state['finished_at'] = datetime.now(timezone.utc).isoformat()


def start_scan(force=False):
    with _lock:
        if _state['status'] == 'SCANNING':
            return False
        if not force and _state['finished_at']:
            try:
                age = time.time() - datetime.fromisoformat(_state['finished_at']).timestamp()
                if age < BIST_SCANNER_CACHE_SECONDS:
                    return False
            except Exception:
                pass
    symbols = get_bist_tum_symbols()
    threading.Thread(target=_scan_worker, args=(symbols,), daemon=True).start()
    return True


def snapshot():
    with _lock:
        return dict(_state)


def background_loop():
    while True:
        try:
            start_scan(force=False)
        except Exception as e:
            with _lock:
                _state['status'] = 'ERROR'
                _state['last_error'] = str(e)
        time.sleep(max(60, BIST_SCANNER_CACHE_SECONDS))
