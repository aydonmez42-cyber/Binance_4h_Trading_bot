import pandas as pd

def recent_true(series, current_pos, max_bars):
    start = max(0, current_pos - max_bars + 1)
    window = series.iloc[start:current_pos + 1]
    return bool(window.fillna(False).any())


def fomo_blocked(df, i, cfg):
    """TEST37 FOMO veto on the fixed 4H decision timeframe.

    The rule-set definition is abs(C[TF_E,0]-C[TF_E,1]) > 3*ATR(TF_E,1).
    Because this project is intentionally fixed at 4H, TF_E is mapped to 4H.
    Only closed bars are used: current signal close vs previous close, with
    ATR from the previous closed bar.
    """
    if not getattr(cfg, "USE_FOMO_FILTER", False):
        return False
    if i < 1:
        return False
    atr_prev = df.iloc[i - 1].get("atr")
    if pd.isna(atr_prev) or float(atr_prev) <= 0:
        return False
    move = abs(float(df.iloc[i]["close"]) - float(df.iloc[i - 1]["close"]))
    return move > float(cfg.FOMO_ATR_MULTIPLE) * float(atr_prev)


def long_signal(df, i, cfg):
    row = df.iloc[i]

    if i < 1:
        return False

    # TEST36: 1D regime + confirmed 4H market structure are hard entry filters.
    if cfg.USE_1D_REGIME_FILTER and row.get("bias_1d", "NONE") != "LONG":
        return False
    if cfg.USE_MARKET_STRUCTURE and row.get("structure_bias", "NONE") != "LONG":
        return False
    if fomo_blocked(df, i, cfg):
        return False

    # EMA50/EMA200 define the main trend regime; Supertrend is the trend filter.
    if not (row["close"] > row["ema100"]):
        return False
    if not (row["ema50"] > row["ema100"]):
        return False
    if not (row["adx"] > cfg.ADX_THRESHOLD):
        return False
    if not bool(row["supertrend_bullish"]):
        return False
    if not (row["rsi"] > cfg.RSI_LONG_THRESHOLD):
        return False
    if cfg.USE_MACD_LONG_FILTER and not bool(row["macd_long_ok"]):
        return False

    if not recent_true(
        df["cci"] > cfg.CCI_LONG_THRESHOLD, i, cfg.CCI_VALID_BARS
    ):
        return False

    if not recent_true(
        df["stoch_bull_cross"], i, cfg.STOCH_VALID_BARS
    ):
        return False

    if not (row["stoch_d"] > cfg.STOCH_LONG_D_THRESHOLD):
        return False

    return True


def short_signal(df, i, cfg):
    row = df.iloc[i]

    if i < 1:
        return False

    # TEST36: 1D regime + confirmed 4H market structure are hard entry filters.
    if cfg.USE_1D_REGIME_FILTER and row.get("bias_1d", "NONE") != "SHORT":
        return False
    if cfg.USE_MARKET_STRUCTURE and row.get("structure_bias", "NONE") != "SHORT":
        return False
    if fomo_blocked(df, i, cfg):
        return False

    if not (row["close"] < row["ema100"]):
        return False
    if not (row["ema50"] < row["ema100"]):
        return False
    if not (row["adx"] > cfg.ADX_THRESHOLD):
        return False
    if not bool(row["supertrend_bearish"]):
        return False
    if not (row["rsi"] < cfg.RSI_SHORT_THRESHOLD):
        return False

    # Bollinger short filter disabled for this test.
    # 
    if cfg.USE_BB_SHORT_FILTER and not bool(row["bb_short_reentry"]):
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

    return True


def exit_signal(position, row):
    if position == "LONG":
        return row["close"] < row["ema100"]
    if position == "SHORT":
        return row["close"] > row["ema100"]
    return False
