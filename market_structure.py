import numpy as np
import pandas as pd


def _is_confirmed_pivot(values, j, left, right, is_high=True):
    if j < left or j + right >= len(values):
        return False
    center = values[j]
    window_left = values[j-left:j]
    window_right = values[j+1:j+right+1]
    if is_high:
        return bool(center > np.max(window_left) and center > np.max(window_right))
    return bool(center < np.min(window_left) and center < np.min(window_right))


def add_confirmed_pivots(df, left=5, right=5):
    """Add confirmed swing pivots without look-ahead.

    A pivot located at bar j becomes available only on bar j+right.
    Thus no signal bar can use a pivot whose confirmation has not occurred yet.
    """
    out = df.copy()
    n = len(out)
    highs = out["high"].to_numpy(dtype=float)
    lows = out["low"].to_numpy(dtype=float)

    out["confirmed_swing_high"] = np.nan
    out["confirmed_swing_low"] = np.nan

    for j in range(left, n - right):
        confirm_i = j + right
        if _is_confirmed_pivot(highs, j, left, right, True):
            out.iloc[confirm_i, out.columns.get_loc("confirmed_swing_high")] = highs[j]
        if _is_confirmed_pivot(lows, j, left, right, False):
            out.iloc[confirm_i, out.columns.get_loc("confirmed_swing_low")] = lows[j]
    return out


def add_market_structure(df, left=5, right=5):
    """Derive bullish/bearish 4H structure from the two latest confirmed HH/HL or LH/LL pivots."""
    out = add_confirmed_pivots(df, left=left, right=right)
    bias = []
    highs_hist = []
    lows_hist = []

    for _, row in out.iterrows():
        if pd.notna(row["confirmed_swing_high"]):
            highs_hist.append(float(row["confirmed_swing_high"]))
        if pd.notna(row["confirmed_swing_low"]):
            lows_hist.append(float(row["confirmed_swing_low"]))

        structure = "NONE"
        if len(highs_hist) >= 2 and len(lows_hist) >= 2:
            hh = highs_hist[-1] > highs_hist[-2]
            hl = lows_hist[-1] > lows_hist[-2]
            lh = highs_hist[-1] < highs_hist[-2]
            ll = lows_hist[-1] < lows_hist[-2]
            if hh and hl:
                structure = "LONG"
            elif lh and ll:
                structure = "SHORT"
        bias.append(structure)

    out["structure_bias"] = bias
    out["structure_bullish"] = out["structure_bias"].eq("LONG")
    out["structure_bearish"] = out["structure_bias"].eq("SHORT")
    return out
