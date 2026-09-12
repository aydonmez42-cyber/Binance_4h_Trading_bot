import math
import pandas as pd

import config as cfg
from data_manager import fetch_klines
from indicators import add_indicators
from strategy import long_signal, short_signal, exit_signal


def execution_price(price, side, is_entry, slippage):
    # Conservative slippage model.
    if (side == "LONG" and is_entry) or (side == "SHORT" and not is_entry):
        return price * (1 + slippage)
    return price * (1 - slippage)


def commission(notional):
    return notional * cfg.FEE_RATE


def build_exit_levels(side, entry_price, atr_value):
    """Create initial ATR-based SL/TP levels from the closed signal candle ATR."""
    levels = {
        "stop_loss": None,
        "take_profit": None,
        "trailing_stop": None,
        "trail_active": False,
        "highest_price": entry_price,
        "lowest_price": entry_price,
    }

    if not pd.notna(atr_value) or atr_value <= 0:
        raise ValueError("ATR is invalid at entry; cannot initialize ATR exits.")

    if side == "LONG":
        if cfg.USE_ATR_SL:
            levels["stop_loss"] = entry_price - atr_value * (cfg.ATR_SHORT_SL_MULTIPLIER if side == "SHORT" else cfg.ATR_SL_MULTIPLIER)
        if cfg.USE_ATR_TP:
            levels["take_profit"] = entry_price + atr_value * cfg.ATR_TP_MULTIPLIER
    else:
        if cfg.USE_ATR_SL:
            levels["stop_loss"] = entry_price + atr_value * (cfg.ATR_SHORT_SL_MULTIPLIER if side == "SHORT" else cfg.ATR_SL_MULTIPLIER)
        if cfg.USE_ATR_TP:
            levels["take_profit"] = entry_price - atr_value * cfg.ATR_TP_MULTIPLIER

    levels["entry_atr"] = atr_value
    return levels


def apply_slippage_to_exit(level, side):
    # For a long exit, selling at a stop/TP receives slightly less.
    # For a short exit, buying back pays slightly more.
    if side == "LONG":
        return level * (1 - cfg.SLIPPAGE_RATE)
    return level * (1 + cfg.SLIPPAGE_RATE)


def check_intrabar_exit(position, row, levels):
    """Return (reason, raw_exit_price) for the first modeled intrabar exit.

    OHLC does not reveal the exact sequence of high/low inside a 4H candle.
    To avoid optimistic bias, if the initial SL and TP are both touched in the
    same candle, SL is assumed to happen first. The same conservative priority
    is used when a trailing stop and profit target are both touched.
    """
    high = float(row["high"])
    low = float(row["low"])

    if position == "LONG":
        stop = levels.get("stop_loss")
        tp = levels.get("take_profit")
        trail = levels.get("trailing_stop")

        # Conservative priority: protective stop before profit target.
        if stop is not None and low <= stop:
            return "ATR_SL", stop
        if trail is not None and low <= trail:
            return "ATR_TRAILING_SL", trail
        if tp is not None and high >= tp:
            return "ATR_TP", tp

    else:
        stop = levels.get("stop_loss")
        tp = levels.get("take_profit")
        trail = levels.get("trailing_stop")

        if stop is not None and high >= stop:
            return "ATR_SL", stop
        if trail is not None and high >= trail:
            return "ATR_TRAILING_SL", trail
        if tp is not None and low <= tp:
            return "ATR_TP", tp

    return None, None


def update_trailing(position, row, levels):
    """Update trailing state using current candle extremes."""
    entry = levels["entry_price"]
    atr_value = levels["entry_atr"]

    if position == "LONG":
        levels["highest_price"] = max(levels["highest_price"], float(row["high"]))
        activation_price = entry + atr_value * cfg.ATR_TRAIL_ACTIVATION

        if cfg.USE_ATR_TRAILING and levels["highest_price"] >= activation_price:
            levels["trail_active"] = True
            new_trail = levels["highest_price"] - atr_value * cfg.ATR_TRAIL_MULTIPLIER
            if levels["trailing_stop"] is None:
                levels["trailing_stop"] = new_trail
            else:
                levels["trailing_stop"] = max(levels["trailing_stop"], new_trail)

    else:
        levels["lowest_price"] = min(levels["lowest_price"], float(row["low"]))
        activation_price = entry - atr_value * cfg.ATR_TRAIL_ACTIVATION

        if cfg.USE_ATR_TRAILING and levels["lowest_price"] <= activation_price:
            levels["trail_active"] = True
            new_trail = levels["lowest_price"] + atr_value * cfg.ATR_TRAIL_MULTIPLIER
            if levels["trailing_stop"] is None:
                levels["trailing_stop"] = new_trail
            else:
                levels["trailing_stop"] = min(levels["trailing_stop"], new_trail)


def close_position(position, px, row, entry_price, entry_notional, entry_fee, reason, equity):
    qty = entry_notional / entry_price
    if position == "LONG":
        pnl_gross = (px - entry_price) * qty
    else:
        pnl_gross = (entry_price - px) * qty

    exit_fee = commission(abs(px * qty))
    pnl_net = pnl_gross - entry_fee - exit_fee
    starting_equity_for_trade = equity - pnl_gross + exit_fee
    equity += pnl_gross - exit_fee

    trade = {
        "entry_time": row["entry_time_for_trade"],
        "exit_time": row["open_time"],
        "side": position,
        "entry_price": entry_price,
        "exit_price": px,
        "gross_pnl": pnl_gross,
        "fees": entry_fee + exit_fee,
        "net_pnl": pnl_net,
        "return_pct_on_equity": pnl_net / max(starting_equity_for_trade, 1e-12),
        "reason": reason,
    }
    return trade, equity


def run_backtest(df):
    equity = cfg.INITIAL_CAPITAL
    position = None
    entry_price = None
    entry_time = None
    entry_notional = None
    entry_fee = 0.0
    exit_levels = None

    trades = []
    equity_curve = []
    pending_entry = None
    pending_ema_exit = False

    for i in range(len(df)):
        row = df.iloc[i]

        # 1) Execute EMA100 close signal from the previous CLOSED candle at current open.
        if pending_ema_exit and position is not None:
            px = execution_price(float(row["open"]), position, False, cfg.SLIPPAGE_RATE)
            trade_row = row.copy()
            trade_row["entry_time_for_trade"] = entry_time
            trade, equity = close_position(
                position, px, trade_row, entry_price, entry_notional,
                entry_fee, "EMA100_CLOSE", equity
            )
            trades.append(trade)
            position = None
            entry_price = entry_time = entry_notional = None
            entry_fee = 0.0
            exit_levels = None
            pending_ema_exit = False

        # 2) Execute entry generated by the previous CLOSED candle at current open.
        if pending_entry is not None and position is None:
            side = pending_entry["side"]
            px = execution_price(float(row["open"]), side, True, cfg.SLIPPAGE_RATE)
            entry_notional = equity * cfg.POSITION_SIZE_PCT * cfg.LEVERAGE
            entry_fee = commission(entry_notional)
            equity -= entry_fee

            position = side
            entry_price = px
            entry_time = row["open_time"]
            exit_levels = build_exit_levels(side, entry_price, pending_entry["atr"])
            exit_levels["entry_price"] = entry_price
            pending_entry = None

            # If the opening price gaps through an exit level, the actual open is
            # the executable price rather than the stale level.
            if position == "LONG":
                if exit_levels["stop_loss"] is not None and float(row["open"]) <= exit_levels["stop_loss"]:
                    exit_levels["stop_loss"] = float(row["open"])
                if exit_levels["take_profit"] is not None and float(row["open"]) >= exit_levels["take_profit"]:
                    exit_levels["take_profit"] = float(row["open"])
            else:
                if exit_levels["stop_loss"] is not None and float(row["open"]) >= exit_levels["stop_loss"]:
                    exit_levels["stop_loss"] = float(row["open"])
                if exit_levels["take_profit"] is not None and float(row["open"]) <= exit_levels["take_profit"]:
                    exit_levels["take_profit"] = float(row["open"])

        # 3) Intrabar ATR exits on the current 4H candle.
        if position is not None and exit_levels is not None:
            # Check initial levels before updating trailing state. This avoids
            # using future high/low to retroactively improve the stop.
            reason, raw_px = check_intrabar_exit(position, row, exit_levels)

            if reason is not None:
                px = apply_slippage_to_exit(raw_px, position)
                trade_row = row.copy()
                trade_row["entry_time_for_trade"] = entry_time
                trade, equity = close_position(
                    position, px, trade_row, entry_price, entry_notional,
                    entry_fee, reason, equity
                )
                trades.append(trade)
                position = None
                entry_price = entry_time = entry_notional = None
                entry_fee = 0.0
                exit_levels = None
            else:
                # Update trailing only if the candle did not already hit an exit.
                update_trailing(position, row, exit_levels)

                # A newly activated trailing stop can be hit later in the same
                # candle, but OHLC cannot establish ordering. We conservatively
                # do not re-enter the candle after activation; it will be tested
                # from the next candle onward. This prevents look-ahead optimism.

        # 4) Mark-to-market equity at current close.
        marked_equity = equity
        if position is not None:
            qty = entry_notional / entry_price
            if position == "LONG":
                unrealized = (float(row["close"]) - entry_price) * qty
            else:
                unrealized = (entry_price - float(row["close"])) * qty
            marked_equity += unrealized

        equity_curve.append({
            "time": row["close_time"],
            "equity": marked_equity,
            "position": position or "FLAT",
        })

        # 5) Generate signals only from the fully CLOSED candle.
        if i < len(df) - 1 and position is not None:
            if cfg.USE_EMA100_EXIT and exit_signal(position, row):
                pending_ema_exit = True

        if i < len(df) - 1 and position is None and pending_entry is None:
            if long_signal(df, i, cfg):
                pending_entry = {"side": "LONG", "atr": float(row["atr"])}
            elif short_signal(df, i, cfg):
                pending_entry = {"side": "SHORT", "atr": float(row["atr"])}

    # Close any remaining position at final close for complete accounting.
    if position is not None:
        row = df.iloc[-1]
        px = execution_price(float(row["close"]), position, False, cfg.SLIPPAGE_RATE)
        trade_row = row.copy()
        trade_row["entry_time_for_trade"] = entry_time
        trade, equity = close_position(
            position, px, trade_row, entry_price, entry_notional,
            entry_fee, "END_OF_DATA", equity
        )
        trades.append(trade)

    return pd.DataFrame(trades), pd.DataFrame(equity_curve), equity


def calculate_metrics(trades, equity_curve):
    if equity_curve.empty:
        return {}

    eq = equity_curve["equity"]
    peak = eq.cummax()
    drawdown = eq / peak - 1.0
    max_dd = drawdown.min()

    net_profit = trades["net_pnl"].sum() if not trades.empty else 0.0
    wins = trades[trades["net_pnl"] > 0] if not trades.empty else pd.DataFrame()
    losses = trades[trades["net_pnl"] <= 0] if not trades.empty else pd.DataFrame()

    gross_profit = wins["net_pnl"].sum() if not wins.empty else 0.0
    gross_loss = abs(losses["net_pnl"].sum()) if not losses.empty else 0.0
    pf = gross_profit / gross_loss if gross_loss > 0 else math.inf
    win_rate = len(wins) / len(trades) if len(trades) else 0.0
    expectancy = net_profit / len(trades) if len(trades) else 0.0

    long_trades = trades[trades["side"] == "LONG"] if not trades.empty else pd.DataFrame()
    short_trades = trades[trades["side"] == "SHORT"] if not trades.empty else pd.DataFrame()

    return {
        "initial_capital": cfg.INITIAL_CAPITAL,
        "final_equity": float(eq.iloc[-1]),
        "net_profit": float(net_profit),
        "return_pct": float((eq.iloc[-1] / cfg.INITIAL_CAPITAL - 1) * 100),
        "trades": int(len(trades)),
        "wins": int(len(wins)),
        "losses": int(len(losses)),
        "win_rate_pct": float(win_rate * 100),
        "profit_factor": float(pf),
        "expectancy_per_trade": float(expectancy),
        "max_drawdown_pct": float(max_dd * 100),
        "long_trades": int(len(long_trades)),
        "short_trades": int(len(short_trades)),
        "long_win_rate_pct": float((long_trades["net_pnl"] > 0).mean() * 100) if len(long_trades) else 0.0,
        "short_win_rate_pct": float((short_trades["net_pnl"] > 0).mean() * 100) if len(short_trades) else 0.0,
    }


def main():
    print(f"Downloading {cfg.SYMBOL} {cfg.INTERVAL} data...")
    df = fetch_klines(cfg.SYMBOL, cfg.INTERVAL, cfg.DATA_START, cfg.DATA_END)

    print(f"Rows: {len(df):,}")
    print("Calculating indicators...")
    df = add_indicators(df, cfg)

    print("Running ATR SL/TP/Trailing backtest...")
    print(
        f"ATR({cfg.ATR_LENGTH}) | SL={cfg.ATR_SL_MULTIPLIER}x | "
        f"TP={cfg.ATR_TP_MULTIPLIER}x | Trail activation={cfg.ATR_TRAIL_ACTIVATION}x | "
        f"Trail distance={cfg.ATR_TRAIL_MULTIPLIER}x"
    )

    trades, equity_curve, final_equity = run_backtest(df)
    metrics = calculate_metrics(trades, equity_curve)

    trades.to_csv(cfg.TRADES_CSV, index=False)
    equity_curve.to_csv(cfg.EQUITY_CSV, index=False)

    print("\n========== BACKTEST RESULT ==========")
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"{k:25s}: {v:.4f}")
        else:
            print(f"{k:25s}: {v}")
    print("=====================================\n")
    print(f"Trades saved: {cfg.TRADES_CSV}")
    print(f"Equity saved: {cfg.EQUITY_CSV}")


if __name__ == "__main__":
    main()
