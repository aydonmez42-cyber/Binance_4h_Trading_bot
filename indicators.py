import numpy as np
import pandas as pd


def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def rsi(close, length=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    result = result.where(avg_loss != 0, 100)
    result = result.where(~((avg_gain == 0) & (avg_loss == 0)), 50)
    return result


def cci(high, low, close, length=20):
    typical_price = (high + low + close) / 3.0
    sma = typical_price.rolling(length).mean()
    mean_dev = typical_price.rolling(length).apply(
        lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
    )
    return (typical_price - sma) / (0.015 * mean_dev.replace(0, np.nan))


def atr(high, low, close, length=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # Wilder-style ATR, consistent with the ADX smoothing used here.
    return tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def adx(high, low, close, length=14):
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=high.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=high.index,
    )

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_value = tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    plus_smoothed = plus_dm.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    minus_smoothed = minus_dm.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()

    plus_di = 100 * plus_smoothed / atr_value.replace(0, np.nan)
    minus_di = 100 * minus_smoothed / atr_value.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def stoch_rsi(close, rsi_length=14, stoch_length=14, k_smooth=3, d_smooth=3):
    r = rsi(close, rsi_length)
    lowest = r.rolling(stoch_length).min()
    highest = r.rolling(stoch_length).max()

    raw = 100 * (r - lowest) / (highest - lowest).replace(0, np.nan)
    k = raw.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


def add_indicators(df, cfg):
    out = df.copy()

    out["ema50"] = ema(out["close"], cfg.EMA_FAST)
    out["ema100"] = ema(out["close"], cfg.EMA_SLOW)
    out["atr"] = atr(out["high"], out["low"], out["close"], cfg.ATR_LENGTH)
    out["adx"] = adx(out["high"], out["low"], out["close"], cfg.ADX_LENGTH)
    out["cci"] = cci(out["high"], out["low"], out["close"], cfg.CCI_LENGTH)
    out["rsi"] = rsi(out["close"], cfg.RSI_LENGTH)

    out["stoch_k"], out["stoch_d"] = stoch_rsi(
        out["close"],
        cfg.STOCH_RSI_RSI_LENGTH,
        cfg.STOCH_RSI_STOCH_LENGTH,
        cfg.STOCH_RSI_K_SMOOTH,
        cfg.STOCH_RSI_D_SMOOTH,
    )

    out["ema_bull_cross"] = (
        (out["ema50"].shift(1) <= out["ema100"].shift(1))
        & (out["ema50"] > out["ema100"])
    )
    out["ema_bear_cross"] = (
        (out["ema50"].shift(1) >= out["ema100"].shift(1))
        & (out["ema50"] < out["ema100"])
    )

    out["stoch_bull_cross"] = (
        (out["stoch_k"].shift(1) <= out["stoch_d"].shift(1))
        & (out["stoch_k"] > out["stoch_d"])
    )
    out["stoch_bear_cross"] = (
        (out["stoch_k"].shift(1) >= out["stoch_d"].shift(1))
        & (out["stoch_k"] < out["stoch_d"])
    )

    return out
