# Binance 4H Trading Bot — TEST 4

Controlled test based on TEST 1.

## TEST 4 changes
- Timeframe: 4h (unchanged)
- DI cross filter: removed completely from entry logic
- ADX threshold: > 25
- Supertrend filter: Period 10, Multiplier 7.4
- ATR exits: SL 2 ATR, TP 4 ATR, trailing activation +2 ATR, trailing distance 2 ATR
- EMA100 exit: enabled
- Entry execution: signal from closed candle, next candle open
- Symbol: BTCUSDT

All other entry conditions remain unchanged from TEST 1.

## Entry logic
LONG requires EMA50/EMA100 bullish cross, close above EMA100, ADX >25, Supertrend bullish, RSI >50, recent CCI >+50, recent bullish Stoch RSI cross and K >20.

SHORT requires EMA50/EMA100 bearish cross, close below EMA100, ADX >25, Supertrend bearish, RSI <50, recent CCI <-50, recent bearish Stoch RSI cross and K <80.

## Important
This is a controlled experiment. Do not optimize parameters until the baseline result is reviewed.
