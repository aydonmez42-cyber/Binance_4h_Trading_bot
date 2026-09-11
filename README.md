# TEST 11 — Bollinger Short Filter

Based on TEST 8. Only the SHORT entry logic is changed.

## TEST 11 changes
- BTCUSDT, 4H
- EMA50 / EMA200 trend filter
- Supertrend 10 / 5
- ADX > 25
- RSI long > 50 / short < 50
- CCI and Stoch RSI conditions unchanged
- SHORT additionally requires: previous closed candle closed above the upper Bollinger Band, and the current closed candle closes back at or below the upper band.
- LONG logic is unchanged from TEST 8.
- ATR SL = 2x ATR
- ATR TP = 4x ATR
- ATR trailing activation = +2x ATR
- ATR trailing distance = 2x ATR
- EMA exit OFF

The purpose of TEST 11 is to improve the weak SHORT side without changing the successful LONG side.
# Binance 4H Trading Bot — TEST 4

Controlled test based on TEST 1.

## TEST 4 changes
- Timeframe: 4h (unchanged)
- DI cross filter: removed completely from entry logic
- ADX threshold: > 25
- Supertrend filter: Period 10, Multiplier 4.0
- ATR exits: SL 2 ATR, TP 4 ATR, trailing activation +2 ATR, trailing distance 2 ATR
- EMA200 exit: enabled
- Entry execution: signal from closed candle, next candle open
- Symbol: BTCUSDT

All other entry conditions remain unchanged from TEST 1.

## Entry logic
LONG requires EMA50/EMA200 bullish cross, close above EMA200, ADX >25, Supertrend bullish, RSI >50, recent CCI >+50, recent bullish Stoch RSI cross and K >20.

SHORT requires EMA50/EMA200 bearish cross, close below EMA200, ADX >25, Supertrend bearish, RSI <50, recent CCI <-50, recent bearish Stoch RSI cross and K <80.

## Important
This is a controlled experiment. Do not optimize parameters until the baseline result is reviewed.


## TEST 8 controlled changes
- EMA slow: 100 -> 200
- Supertrend multiplier: 7.4 -> 4.0
- EMA exit disabled
- EMA50/EMA200 used as trend regime filter, not cross trigger
- ATR SL 2x, ATR TP 4x, trailing activation 2x and distance 2x retained
- ADX > 25 retained; DI remains removed
