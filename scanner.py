import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import config as cfg
from indicators import add_indicators
from strategy import long_signal, short_signal

EXCHANGE_INFO_URL = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
TICKER_URL = 'https://fapi.binance.com/fapi/v1/ticker/24hr'
KLINES_URL = 'https://fapi.binance.com/fapi/v1/klines'


def _session():
    s = requests.Session()
    s.headers.update({'User-Agent': 'TEST32-Paper-Scanner/1.0'})
    return s


def get_markets():
    s = _session()
    info = s.get(EXCHANGE_INFO_URL, timeout=20).json()
    tickers = s.get(TICKER_URL, timeout=20).json()
    tmap = {x.get('symbol'): x for x in tickers if x.get('symbol')}
    rows = []
    for x in info.get('symbols', []):
        if x.get('status') != 'TRADING':
            continue
        if x.get('contractType') != 'PERPETUAL':
            continue
        if x.get('quoteAsset') != 'USDT':
            continue
        sym = x.get('symbol')
        t = tmap.get(sym, {})
        rows.append({
            'symbol': sym,
            'base': x.get('baseAsset'),
            'quote': x.get('quoteAsset'),
            'price': float(t.get('lastPrice') or 0),
            'change_pct': float(t.get('priceChangePercent') or 0),
            'volume': float(t.get('quoteVolume') or 0),
            'count': int(t.get('count') or 0),
        })
    rows.sort(key=lambda r: r['volume'], reverse=True)
    return rows


def fetch_klines(symbol, limit=300):
    s = _session()
    r = s.get(KLINES_URL, params={'symbol': symbol, 'interval': cfg.INTERVAL, 'limit': limit}, timeout=20)
    r.raise_for_status()
    data = r.json()
    cols = ['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore']
    df = pd.DataFrame(data, columns=cols)
    for c in ['open','high','low','close','volume','quote_volume']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms', utc=True)
    return df


def scan_symbol(symbol):
    try:
        df = fetch_klines(symbol, 300)
        # Ignore the currently forming candle.
        closed = df.iloc[:-1].copy()
        if len(closed) < 230:
            return {'symbol': symbol, 'error': 'Yetersiz veri'}
        e = add_indicators(closed, cfg)
        i = len(e) - 1
        row = e.iloc[i]
        go_long = bool(long_signal(e, i, cfg))
        go_short = bool(short_signal(e, i, cfg))
        if go_long and not go_short:
            signal = 'LONG'
        elif go_short and not go_long:
            signal = 'SHORT'
        else:
            signal = 'NO SIGNAL'
        return {
            'symbol': symbol,
            'signal': signal,
            'close': float(row['close']),
            'close_time': row['close_time'].isoformat(),
            'ema50': float(row['ema50']) if pd.notna(row['ema50']) else None,
            'ema200': float(row['ema100']) if pd.notna(row['ema100']) else None,
            'supertrend': 'BULLISH' if bool(row['supertrend_bullish']) else 'BEARISH',
            'adx': float(row['adx']) if pd.notna(row['adx']) else None,
            'rsi': float(row['rsi']) if pd.notna(row['rsi']) else None,
            'cci': float(row['cci']) if pd.notna(row['cci']) else None,
            'stoch_k': float(row['stoch_k']) if pd.notna(row['stoch_k']) else None,
            'stoch_d': float(row['stoch_d']) if pd.notna(row['stoch_d']) else None,
            'macd_ok': bool(row['macd_long_ok']) if pd.notna(row['macd_long_ok']) else False,
        }
    except Exception as ex:
        return {'symbol': symbol, 'signal': 'ERROR', 'error': f'{type(ex).__name__}: {ex}'}


def scan_symbols(symbols, workers=5):
    results = []
    with ThreadPoolExecutor(max_workers=max(1, min(int(workers), 8))) as ex:
        futures = {ex.submit(scan_symbol, s): s for s in symbols}
        for f in as_completed(futures):
            results.append(f.result())
    order = {s: i for i, s in enumerate(symbols)}
    results.sort(key=lambda x: order.get(x.get('symbol'), 99999))
    return results
