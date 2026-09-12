import os
import requests

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_message(text: str) -> bool:
    """Send a Telegram message. Returns False silently if not configured."""
    if not TELEGRAM_ENABLED:
        print('TELEGRAM | not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)', flush=True)
        return False
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    try:
        r = requests.post(
            url,
            json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get('ok'):
            raise RuntimeError(data)
        return True
    except Exception as e:
        print(f'TELEGRAM ERROR | {type(e).__name__}: {e}', flush=True)
        return False


def entry_message(p: dict) -> str:
    side_emoji = '🟢' if p['side'] == 'LONG' else '🔴'
    return (
        f'{side_emoji} <b>TEST32 PAPER — YENİ POZİSYON</b>\n\n'
        f'<b>{p["side"]}</b> {p["symbol"]}\n'
        f'Giriş: <b>{p["entry_price"]:,.2f}</b>\n'
        f'ATR: {p["atr"]:,.2f}\n'
        f'SL: <b>{p["sl"]:,.2f}</b>\n'
        f'TP: <b>{p["tp"]:,.2f}</b>\n'
        f'Miktar: {p["qty_eth"]:.2f} ETH\n'
        f'Sinyal: {p["signal_time"]}'
    )


def exit_message(t: dict) -> str:
    positive = float(t['net_pnl']) >= 0
    emoji = '✅' if positive else '❌'
    return (
        f'{emoji} <b>TEST32 PAPER — POZİSYON KAPANDI</b>\n\n'
        f'<b>{t["side"]}</b> {t["symbol"]}\n'
        f'Giriş: {float(t["entry_price"]):,.2f}\n'
        f'Çıkış: <b>{float(t["exit_price"]):,.2f}</b>\n'
        f'Net P&L: <b>{float(t["net_pnl"]):+,.2f} $</b>\n'
        f'Ücretler: {float(t["fees"]):,.2f} $\n'
        f'Çıkış nedeni: <b>{t["reason"]}</b>\n'
        f'Süre: {t.get("entry_time", "-")} → {t.get("exit_time", "-")}\n'
        f'Sanal bakiye: <b>{float(t["equity_after"]):,.2f} $</b>'
    )


def daily_report(state: dict, trades: list, report_date: str) -> str:
    # At 09:00 Europe/Istanbul, report trades closed during the previous local calendar day.
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    local_date = datetime.fromisoformat(report_date).date()
    previous_date = (local_date - timedelta(days=1)).isoformat()
    day_trades = []
    for t in trades:
        raw = str(t.get('exit_time', ''))
        try:
            dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo('UTC'))
            if dt.astimezone(ZoneInfo('Europe/Istanbul')).date().isoformat() == previous_date:
                day_trades.append(t)
        except Exception:
            continue
    wins = sum(1 for t in day_trades if float(t.get('net_pnl', 0)) > 0)
    losses = sum(1 for t in day_trades if float(t.get('net_pnl', 0)) < 0)
    day_pnl = sum(float(t.get('net_pnl', 0)) for t in day_trades)
    all_pnl = sum(float(t.get('net_pnl', 0)) for t in trades)
    start = float(os.environ.get('PAPER_INITIAL_CAPITAL', '10000'))
    equity = float(state.get('equity', start))
    pos = state.get('position')
    lines = [
        '📊 <b>TEST32 PAPER — GÜNLÜK RAPOR</b>',
        f'Rapor saati: <b>09:00 Europe/Istanbul</b> | Gün: <b>{previous_date}</b>',
        '',
        f'<b>Önceki gün:</b> {len(day_trades)} işlem | {wins}W / {losses}L | P&L <b>{day_pnl:+,.2f} $</b>',
        f'<b>Toplam:</b> {len(trades)} işlem | P&L <b>{all_pnl:+,.2f} $</b>',
        f'<b>Sanal bakiye:</b> {equity:,.2f} $',
        f'<b>Getiri:</b> {(equity/start-1)*100:+.2f}%',
    ]
    if pos:
        side = pos['side']
        symbol = pos['symbol']
        entry = float(pos['entry_price'])
        cp = float(state.get('market_prices', {}).get(symbol, entry))
        qty = float(pos.get('qty_eth', 1))
        unreal = (cp-entry)*qty if side == 'LONG' else (entry-cp)*qty
        active_stop = float(pos.get('trail_stop')) if pos.get('trail_active') and pos.get('trail_stop') is not None else float(pos['sl'])
        lines += [
            '',
            f'📌 <b>Açık pozisyon:</b> {side} {symbol}',
            f'Giriş {entry:,.2f} | Güncel {cp:,.2f}',
            f'Unrealized P&L: <b>{unreal:+,.2f} $</b>',
            f'SL {active_stop:,.2f} | TP {float(pos["tp"]):,.2f}',
        ]
    else:
        lines += ['', '📌 <b>Açık pozisyon:</b> FLAT']
    return '\n'.join(lines)
