import json, os, time
from datetime import datetime, timezone
import requests
import pandas as pd

import config as cfg
from indicators import add_indicators
from strategy import long_signal, short_signal
from dashboard import start_dashboard
from telegram_notifier import send_message, entry_message, exit_message, daily_report
import threading

STATE_FILE = os.environ.get('PAPER_STATE_FILE', 'paper_state.json')
TRADES_FILE = os.environ.get('PAPER_TRADES_FILE', 'paper_trades.csv')
POLL_SECONDS = int(os.environ.get('POLL_SECONDS', '30'))
STARTING_EQUITY = float(os.environ.get('PAPER_INITIAL_CAPITAL', str(cfg.INITIAL_CAPITAL)))

USD_M_URL = 'https://fapi.binance.com/fapi/v1/klines'
COIN_M_URL = 'https://dapi.binance.com/dapi/v1/klines'


def fetch(symbol, market_type, limit=250):
    url = COIN_M_URL if market_type == 'COIN_M' else USD_M_URL
    r = requests.get(url, params={'symbol': symbol, 'interval': cfg.INTERVAL, 'limit': limit}, timeout=20)
    r.raise_for_status()
    data = r.json()
    cols = ['open_time','open','high','low','close','volume','close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore']
    df = pd.DataFrame(data, columns=cols)
    for c in ['open','high','low','close','volume','quote_volume']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms', utc=True)
    return df


def load_state():
    if not os.path.exists(STATE_FILE):
        return {'equity': STARTING_EQUITY, 'position': None, 'last_closed_time': None, 'last_processed_entry_time': None, 'market_prices': {}, 'signals': {}, 'last_heartbeat': None}
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        s=json.load(f)
    s.setdefault('market_prices', {}); s.setdefault('signals', {}); s.setdefault('last_heartbeat', None); s.setdefault('last_daily_report_date', None)
    return s


def save_state(s):
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def log_trade(t):
    exists = os.path.exists(TRADES_FILE)
    pd.DataFrame([t]).to_csv(TRADES_FILE, mode='a', header=not exists, index=False)


def exec_price(raw, side):
    return raw * (1 + cfg.SLIPPAGE_RATE) if side == 'BUY' else raw * (1 - cfg.SLIPPAGE_RATE)


def close_price(raw, side):
    # side is the position side being closed: LONG sells, SHORT buys
    return exec_price(raw, 'SELL' if side == 'LONG' else 'BUY')


def fee(notional):
    return abs(notional) * cfg.FEE_RATE


def enter(state, position, price, signal_row, now):
    side = position
    atr = float(signal_row['atr'])
    if side == 'LONG':
        symbol = cfg.LONG_SYMBOL
        sl = price - cfg.ATR_SL_MULTIPLIER * atr
        tp = price + cfg.ATR_LONG_TP_MULTIPLIER * atr
    else:
        symbol = cfg.SHORT_SYMBOL
        sl = price + cfg.ATR_SHORT_SL_MULTIPLIER * atr
        tp = price - cfg.ATR_SHORT_TP_MULTIPLIER * atr
    state['position'] = {
        'side': side, 'symbol': symbol, 'qty_eth': cfg.POSITION_QTY_ETH,
        'entry_price': price, 'entry_time': now.isoformat(),
        'signal_time': signal_row['close_time'].isoformat(), 'atr': atr,
        'sl': sl, 'tp': tp, 'trail_active': False, 'trail_stop': None,
        'highest_high': price, 'lowest_low': price,
        'entry_fee': fee(price * cfg.POSITION_QTY_ETH),
    }
    state['equity'] -= state['position']['entry_fee']
    save_state(state)
    send_message(entry_message(state['position']))
    print(f"PAPER ENTRY | {side} {symbol} | price={price:.4f} | ATR={atr:.4f} | SL={sl:.4f} | TP={tp:.4f}", flush=True)


def exit_position(state, raw_price, reason, event_time):
    p = state['position']
    side = p['side']
    price = close_price(raw_price, side)
    qty = p['qty_eth']
    gross = (price - p['entry_price']) * qty if side == 'LONG' else (p['entry_price'] - price) * qty
    exit_fee = fee(price * qty)
    net = gross - exit_fee - p['entry_fee']
    state['equity'] += gross - exit_fee
    trade = {
        'signal_time': p['signal_time'], 'entry_time': p['entry_time'], 'exit_time': event_time.isoformat(),
        'side': side, 'symbol': p['symbol'], 'qty_eth': qty, 'entry_price': p['entry_price'],
        'exit_price': price, 'atr': p['atr'], 'sl': p['sl'], 'tp': p['tp'],
        'trail_active': p['trail_active'], 'trail_stop': p['trail_stop'],
        'gross_pnl': gross, 'fees': p['entry_fee'] + exit_fee, 'net_pnl': net, 'reason': reason,
        'equity_after': state['equity']
    }
    log_trade(trade)
    print(f"PAPER EXIT  | {side} {p['symbol']} | reason={reason} | price={price:.4f} | net={net:.2f} | equity={state['equity']:.2f}", flush=True)
    send_message(exit_message(trade))
    state['position'] = None
    save_state(state)


def process_intrabar(state, long_candle, short_candle, now):
    p = state['position']
    if not p:
        return False
    candle = long_candle if p['side'] == 'LONG' else short_candle
    high, low = float(candle['high']), float(candle['low'])
    entry, atr = p['entry_price'], p['atr']

    # Existing stops/TP have priority. If both hit in the same candle, SL first.
    if p['side'] == 'LONG':
        stop = p['trail_stop'] if p['trail_active'] and p['trail_stop'] is not None else p['sl']
        if low <= stop:
            exit_position(state, stop, 'ATR_TRAILING_SL' if p['trail_active'] else 'ATR_SL', now)
            return True
        if cfg.USE_ATR_TP and high >= p['tp']:
            exit_position(state, p['tp'], 'ATR_TP', now)
            return True
        if cfg.USE_ATR_TRAILING:
            if high >= entry + cfg.ATR_TRAIL_ACTIVATION * atr:
                if not p['trail_active']:
                    p['trail_active'] = True
                    p['highest_high'] = high
                    p['trail_stop'] = high - cfg.ATR_TRAIL_MULTIPLIER * atr
                else:
                    p['highest_high'] = max(p['highest_high'], high)
                    p['trail_stop'] = max(p['trail_stop'], p['highest_high'] - cfg.ATR_TRAIL_MULTIPLIER * atr)
    else:
        stop = p['trail_stop'] if p['trail_active'] and p['trail_stop'] is not None else p['sl']
        if high >= stop:
            exit_position(state, stop, 'ATR_TRAILING_SL' if p['trail_active'] else 'ATR_SL', now)
            return True
        if cfg.USE_ATR_TP and low <= p['tp']:
            exit_position(state, p['tp'], 'ATR_TP', now)
            return True
        if cfg.USE_ATR_TRAILING:
            if low <= entry - cfg.ATR_TRAIL_ACTIVATION * atr:
                if not p['trail_active']:
                    p['trail_active'] = True
                    p['lowest_low'] = low
                    p['trail_stop'] = low + cfg.ATR_TRAIL_MULTIPLIER * atr
                else:
                    p['lowest_low'] = min(p['lowest_low'], low)
                    p['trail_stop'] = min(p['trail_stop'], p['lowest_low'] + cfg.ATR_TRAIL_MULTIPLIER * atr)
    save_state(state)
    return False


def main():
    print('TEST32 PAPER TRADING | REAL MARKET DATA | NO REAL ORDERS', flush=True)
    threading.Thread(target=start_dashboard, daemon=True).start()
    state = load_state()
    while True:
        try:
            signal_df = fetch(cfg.SIGNAL_SYMBOL, 'USD_M', 300)
            long_df = fetch(cfg.LONG_SYMBOL, 'COIN_M', 100)
            short_df = fetch(cfg.SHORT_SYMBOL, 'USD_M', 100)
            # Only fully closed candles are eligible for signals.
            closed = signal_df.iloc[:-1].copy()
            enriched = add_indicators(closed, cfg)
            latest = enriched.iloc[-1]
            latest_closed_time = latest['close_time']
            now = datetime.now(timezone.utc)
            state['last_heartbeat'] = now.isoformat()
            # Daily Telegram report at 09:00 Europe/Istanbul. If the service restarts after 09:00,
            # send the missed report immediately, but never more than once per local calendar day.
            from zoneinfo import ZoneInfo
            tr_now = now.astimezone(ZoneInfo('Europe/Istanbul'))
            report_date = tr_now.date().isoformat()
            if tr_now.hour >= 9 and state.get('last_daily_report_date') != report_date:
                # Read current trade history before sending the report.
                report_trades = []
                if os.path.exists(TRADES_FILE):
                    try:
                        report_trades = pd.read_csv(TRADES_FILE).fillna('').to_dict('records')
                    except Exception:
                        report_trades = []
                msg = daily_report(state, report_trades, (tr_now.date()).isoformat())
                if send_message(msg):
                    state['last_daily_report_date'] = report_date
                    save_state(state)
                    print(f'TELEGRAM | daily report sent | {report_date} 09:00 Europe/Istanbul', flush=True)
            state['market_prices'] = {
                'ETHUSDT': float(short_df.iloc[-1]['close']),
                'ETHUSD_PERP': float(long_df.iloc[-1]['close'])
            }
            state['market_price_time'] = now.isoformat()
            def fmt(v):
                try:
                    x=float(v)
                    return round(x,4)
                except Exception:
                    return None
            state['signals'] = {
                'ema': 'BULLISH' if float(latest.get('ema_fast',0)) > float(latest.get('ema_slow',0)) else 'BEARISH',
                'supertrend': 'BULLISH' if bool(latest.get('supertrend_direction', False)) else 'BEARISH',
                'adx': fmt(latest.get('adx')), 'rsi': fmt(latest.get('rsi')),
                'cci': fmt(latest.get('cci')), 'stoch': 'K/D loaded',
                'macd': 'BULLISH' if float(latest.get('macd',0)) > float(latest.get('macd_signal',0)) and float(latest.get('macd_hist',0)) > 0 else 'BEARISH',
                'final': 'LONG' if long_signal(enriched, len(enriched)-1, cfg) else ('SHORT' if short_signal(enriched, len(enriched)-1, cfg) else 'NONE')
            }
            save_state(state)

            # Manage current position using the live execution candle first.
            if state['position']:
                long_live = long_df.iloc[-1]
                short_live = short_df.iloc[-1]
                if process_intrabar(state, long_live, short_live, now):
                    pass

            # Process each newly closed signal candle exactly once.
            last = state.get('last_closed_time')
            last_ts = pd.Timestamp(last) if last else None
            if last_ts is None or latest_closed_time > last_ts:
                # Use the new candle's close to generate a signal; enter at the current execution candle open.
                state['last_closed_time'] = latest_closed_time.isoformat()
                if state['position'] is None:
                    go_long = long_signal(enriched, len(enriched)-1, cfg)
                    go_short = short_signal(enriched, len(enriched)-1, cfg)
                    if go_long and not go_short:
                        px = exec_price(float(long_df.iloc[-1]['open']), 'BUY')
                        enter(state, 'LONG', px, latest, now)
                    elif go_short and not go_long:
                        px = exec_price(float(short_df.iloc[-1]['open']), 'SELL')
                        enter(state, 'SHORT', px, latest, now)
                    else:
                        print(f"CANDLE {latest_closed_time} | no signal", flush=True)
                else:
                    print(f"CANDLE {latest_closed_time} | position already open: {state['position']['side']}", flush=True)
                save_state(state)
            time.sleep(POLL_SECONDS)
        except Exception as e:
            print(f'ERROR | {type(e).__name__}: {e}', flush=True)
            time.sleep(POLL_SECONDS)

if __name__ == '__main__':
    main()
