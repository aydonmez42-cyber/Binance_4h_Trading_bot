import json
import random
import re
import string
import time
from datetime import datetime, timezone

import pandas as pd
import websocket

TV_WS_URL = "wss://data.tradingview.com/socket.io/websocket"
TV_TOKEN = "unauthorized_user_token"
DEFAULT_TIMEOUT = 20


def _session(prefix):
    return prefix + "_" + "".join(random.choice(string.ascii_lowercase) for _ in range(12))


def _frame(method, params):
    payload = json.dumps({"m": method, "p": params}, separators=(",", ":"))
    return f"~m~{len(payload)}~m~{payload}"


def _frames(text):
    out = []
    pos = 0
    while pos < len(text):
        if text.startswith("~m~", pos):
            m = re.match(r"~m~(\d+)~m~", text[pos:])
            if not m:
                break
            n = int(m.group(1))
            start = pos + m.end()
            payload = text[start:start + n]
            pos = start + n
            if payload == "":
                continue
            try:
                out.append(json.loads(payload))
            except json.JSONDecodeError:
                pass
        elif text.startswith("~protocol_error~", pos):
            break
        else:
            nxt = text.find("~m~", pos)
            if nxt < 0:
                break
            pos = nxt
    return out


def _extract_rows(message):
    """Extract TradingView chart bars from timescale_update/du messages."""
    if not isinstance(message, dict):
        return []
    method = message.get("m")
    if method not in ("timescale_update", "du"):
        return []
    p = message.get("p") or []
    if len(p) < 2 or not isinstance(p[1], dict):
        return []
    container = p[1]
    rows = []
    for series in container.values():
        if not isinstance(series, dict):
            continue
        for item in series.get("s", []) or []:
            v = item.get("v") if isinstance(item, dict) else None
            if not isinstance(v, list) or len(v) < 5:
                continue
            # Standard TradingView chart payload: [bar_index, time, open, high, low, close, volume]
            if len(v) >= 7:
                _, ts, op, hi, lo, cl, vol = v[:7]
            else:
                _, ts, op, hi, lo = v[:5]
                cl = v[5] if len(v) > 5 else None
                vol = v[6] if len(v) > 6 else None
            try:
                ts = float(ts)
                rows.append({"timestamp": pd.Timestamp(ts, unit="s", tz="UTC"),
                             "open": float(op), "high": float(hi), "low": float(lo),
                             "close": float(cl), "volume": float(vol) if vol is not None else 0.0})
            except (TypeError, ValueError):
                continue
    return rows


def fetch_tv_bars(symbol, interval="240", bars=300, timeout=DEFAULT_TIMEOUT, retries=2):
    """Fetch native TradingView chart bars. interval 240 = 4H."""
    full = symbol if ":" in symbol else f"BIST:{symbol}"
    last_error = None
    for attempt in range(retries + 1):
        ws = None
        try:
            ws = websocket.create_connection(
                TV_WS_URL,
                timeout=timeout,
                origin="https://www.tradingview.com",
                header=["User-Agent: Mozilla/5.0"],
            )
            cs = _session("cs")
            qs = _session("qs")
            ws.send(_frame("set_auth_token", [TV_TOKEN]))
            ws.send(_frame("chart_create_session", [cs, ""]))
            ws.send(_frame("quote_create_session", [qs]))
            ws.send(_frame("resolve_symbol", [
                cs, "sds_sym_1",
                "=" + json.dumps({"symbol": full, "adjustment": "splits"}, separators=(",", ":"))
            ]))
            ws.send(_frame("create_series", [cs, "sds_1", "s1", "sds_sym_1", interval, int(bars), ""]))

            rows = []
            deadline = time.time() + timeout
            completed = False
            while time.time() < deadline:
                raw = ws.recv()
                if not raw:
                    continue
                # TradingView heartbeat is ~m~N~m~~h~...; echo it back.
                if "~h~" in raw:
                    for h in re.findall(r"~m~\d+~m~~h~\d+", raw):
                        try:
                            ws.send(h)
                        except Exception:
                            pass
                for msg in _frames(raw):
                    method = msg.get("m") if isinstance(msg, dict) else None
                    if method in ("symbol_error", "series_error", "critical_error", "protocol_error"):
                        raise RuntimeError(f"TradingView {method}: {msg.get('p')}")
                    rows.extend(_extract_rows(msg))
                    if method == "series_completed":
                        completed = True
                if completed and rows:
                    break
            if not rows:
                raise RuntimeError("TradingView 4H veri döndürmedi")
            df = pd.DataFrame(rows).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
            return df.reset_index(drop=True)
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.8 * (attempt + 1))
        finally:
            try:
                if ws:
                    ws.close()
            except Exception:
                pass
    raise RuntimeError(f"TradingView veri hatası {full}: {last_error}")


def add_close_time(df, hours=4):
    x = df.copy()
    # Chart timestamps are bar-open timestamps. For BIST native 4H bars,
    # 10:00→14:00 and 14:00→18:00 session bars are therefore closed +4h later.
    x["close_time"] = x["timestamp"] + pd.Timedelta(hours=hours)
    return x
