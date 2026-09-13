import numpy as np
import pandas as pd

from indicators import ema, atr, adx


def rolling_percentile_rank(series, window):
    """Percentile rank of the current value inside the trailing window (0-100)."""
    def rank_last(values):
        arr = np.asarray(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0:
            return np.nan
        x = arr[-1]
        return 100.0 * np.mean(arr <= x)
    return series.rolling(window, min_periods=window).apply(rank_last, raw=True)


def add_daily_regime_indicators(df, cfg):
    out = df.copy()
    out["regime_ema50"] = ema(out["close"], cfg.REGIME_EMA_FAST)
    out["regime_ema200"] = ema(out["close"], cfg.REGIME_EMA_SLOW)
    out["regime_atr"] = atr(out["high"], out["low"], out["close"], cfg.ATR_LENGTH)
    out["regime_atrp"] = out["regime_atr"] / out["close"] * 100.0
    out["regime_atrp_pctl"] = rolling_percentile_rank(
        out["regime_atrp"], cfg.REGIME_ATRP_PCTL_WINDOW
    )
    adx_df = adx(out["high"], out["low"], out["close"], cfg.ADX_LENGTH)
    out["regime_adx"] = adx_df["adx"]
    out["regime_plus_di"] = adx_df["plus_di"]
    out["regime_minus_di"] = adx_df["minus_di"]
    return out


def classify_daily_regime(row, cfg):
    pctl = row["regime_atrp_pctl"]
    if pd.notna(pctl) and (pctl > cfg.REGIME_ATRP_PCTL_HIGH or pctl < cfg.REGIME_ATRP_PCTL_LOW):
        return "VOLATILE"

    if (
        row["close"] > row["regime_ema200"]
        and row["regime_ema50"] > row["regime_ema200"]
        and row["regime_adx"] > cfg.REGIME_ADX_THRESHOLD
        and row["regime_plus_di"] > row["regime_minus_di"]
    ):
        return "BULL"

    if (
        row["close"] < row["regime_ema200"]
        and row["regime_ema50"] < row["regime_ema200"]
        and row["regime_adx"] > cfg.REGIME_ADX_THRESHOLD
        and row["regime_minus_di"] > row["regime_plus_di"]
    ):
        return "BEAR"

    return "RANGE"


def apply_regime_hysteresis(daily_df, cfg):
    """Accept a regime change only after two consecutive daily bars agree."""
    out = daily_df.copy()
    candidates = out.apply(lambda r: classify_daily_regime(r, cfg), axis=1)
    confirmed = []
    current = "NONE"
    prev_candidate = None
    streak = 0

    for candidate in candidates:
        if candidate == prev_candidate:
            streak += 1
        else:
            prev_candidate = candidate
            streak = 1

        if streak >= cfg.REGIME_HYSTERESIS_BARS:
            current = candidate
        confirmed.append(current)

    out["regime_candidate"] = candidates
    out["regime"] = confirmed
    out["bias_1d"] = out["regime"].map({"BULL": "LONG", "BEAR": "SHORT"}).fillna("NONE")
    return out
