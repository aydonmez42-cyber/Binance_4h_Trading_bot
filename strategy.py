import pandas as pd

def recent_true(series, current_pos, max_bars):
    start = max(0, current_pos - max_bars + 1)
    window = series.iloc[start:current_pos + 1]
    return bool(window.fillna(False).any())


def supertrend_bull_cross_series(df):
    prev_close = df["close"].shift(1)
    prev_st = df["supertrend"].shift(1)
    return (prev_close <= prev_st) & (df["close"] > df["supertrend"])


def supertrend_bear_cross_series(df):
    prev_close = df["close"].shift(1)
    prev_st = df["supertrend"].shift(1)
    return (prev_close >= prev_st) & (df["close"] < df["supertrend"])


def long_signal(df, i, cfg):
    row = df.iloc[i]
    if i < 1:
        return False

    # ENTRY TRIGGER: closed candle price crosses the Supertrend line upward.
    if not bool(supertrend_bull_cross_series(df).iloc[i]):
        return False

    # Existing filters remain unchanged unless explicitly changed for this test.
    if not (row["adx"] > cfg.ADX_THRESHOLD):
        return False
    if not (row["rsi"] > cfg.RSI_LONG_THRESHOLD):
        return False

    if not recent_true(df["cci"] > cfg.CCI_LONG_THRESHOLD, i, cfg.CCI_VALID_BARS):
        return False

    if not recent_true(df["stoch_bull_cross"], i, cfg.STOCH_VALID_BARS):
        return False

    if not (row["stoch_k"] > cfg.STOCH_LONG_THRESHOLD):
        return False

    return True


def short_signal(df, i, cfg):
    row = df.iloc[i]
    if i < 1:
        return False

    # ENTRY TRIGGER: closed candle price crosses the Supertrend line downward.
    if not bool(supertrend_bear_cross_series(df).iloc[i]):
        return False

    if not (row["adx"] > cfg.ADX_THRESHOLD):
        return False
    if not (row["rsi"] <= cfg.RSI_SHORT_THRESHOLD):
        return False

    if not recent_true(df["cci"] < cfg.CCI_SHORT_THRESHOLD, i, cfg.CCI_VALID_BARS):
        return False

    if not recent_true(df["stoch_bear_cross"], i, cfg.STOCH_VALID_BARS):
        return False

    if not (row["stoch_k"] < cfg.STOCH_SHORT_THRESHOLD):
        return False

    return True


def exit_signal(position, row):
    # EMA100 exit is disabled for this test. ATR SL and trailing are handled
    # intrabar by backtest.py.
    return False
