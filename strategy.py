import pandas as pd

def recent_true(series, current_pos, max_bars):
    start = max(0, current_pos - max_bars + 1)
    window = series.iloc[start:current_pos + 1]
    return bool(window.fillna(False).any())

def long_signal(df, i, cfg):
    row = df.iloc[i]

    if i < 1:
        return False

    # EMA50/EMA100 cross is the ONLY entry trigger.
    if not bool(row["ema_bull_cross"]):
        return False

    # Conditions that must be valid at the trigger candle.
    if not (row["close"] > row["ema100"]):
        return False
    if not (row["adx"] > cfg.ADX_THRESHOLD):
        return False
    if not (row["rsi"] > cfg.RSI_LONG_THRESHOLD):
        return False

    # CCI can have occurred within the recent validity window.
    if not recent_true(
        df["cci"] > cfg.CCI_LONG_THRESHOLD, i, cfg.CCI_VALID_BARS
    ):
        return False

    # Stoch RSI bullish cross can have occurred within its validity window.
    if not recent_true(
        df["stoch_bull_cross"], i, cfg.STOCH_VALID_BARS
    ):
        return False

    # The stochastic level must still be valid at the trigger candle.
    if not (row["stoch_k"] > cfg.STOCH_LONG_THRESHOLD):
        return False

    # The EMA cross candle itself must close above EMA100.
    if not (row["close"] > row["ema100"]):
        return False

    return True

def short_signal(df, i, cfg):
    row = df.iloc[i]

    if i < 1:
        return False

    if not bool(row["ema_bear_cross"]):
        return False

    if not (row["close"] < row["ema100"]):
        return False
    if not (row["adx"] > cfg.ADX_THRESHOLD):
        return False
    if not (row["rsi"] < cfg.RSI_SHORT_THRESHOLD):
        return False

    if not recent_true(
        df["cci"] < cfg.CCI_SHORT_THRESHOLD, i, cfg.CCI_VALID_BARS
    ):
        return False

    if not recent_true(
        df["stoch_bear_cross"], i, cfg.STOCH_VALID_BARS
    ):
        return False

    if not (row["stoch_k"] < cfg.STOCH_SHORT_THRESHOLD):
        return False

    if not (row["close"] < row["ema100"]):
        return False

    return True

def exit_signal(position, row):
    if position == "LONG":
        return row["close"] < row["ema100"]
    if position == "SHORT":
        return row["close"] > row["ema100"]
    return False
