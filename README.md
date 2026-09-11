# TEST 6 — Supertrend Price-Cross Entry / ATR SL + Trailing

Controlled backtest variant based on TEST 4/5.

## Strategy changes
- Timeframe remains 4H.
- DI filter removed.
- Supertrend Period = 10.
- Supertrend Multiplier = 7.4.
- Entry trigger is now the **closed-candle price crossing the Supertrend line**:
  - Long: previous close <= previous Supertrend and current close > current Supertrend.
  - Short: previous close >= previous Supertrend and current close < current Supertrend.
- EMA50/EMA100 cross is no longer an entry trigger.
- ADX > 25 remains a filter.
- Long RSI remains > 50.
- Short RSI is changed to <= 40.
- CCI and Stoch RSI filters remain.
- ATR SL remains 2x ATR.
- ATR TP is disabled.
- ATR trailing remains active at +2 ATR with 2x ATR distance.
- EMA100 exit is disabled.

All signals are generated only from closed candles and entries execute at the next candle open.
