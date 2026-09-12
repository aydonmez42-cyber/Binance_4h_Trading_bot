TEST 32 – Separate Long/Short Take Profit

Base: TEST 29

Fixed constraints:
- Symbol/signal: ETHUSDT Futures
- Long execution: ETHUSD_PERP (COIN-M)
- Short execution: ETHUSDT (USD-M)
- Timeframe: 4H (fixed)
- Fixed economic exposure: 1 ETH
- EMA 50/200
- Supertrend 10 / 6
- ADX > 25
- Long RSI > 55
- Short RSI < 30
- Long CCI +100
- Stoch RSI Long: K crosses D, D > 30
- MACD Long filter: MACD > signal and histogram > 0
- Bollinger filter OFF
- Long SL = 3.5 ATR
- Short SL = 1.5 ATR
- Long TP = 4.0 ATR
- Short TP = 3.0 ATR  <-- ONLY TEST VARIABLE
- Trailing activation = +2 ATR
- Trailing distance = 2 ATR
- EMA exit OFF
- Entry on next candle open after closed-candle signal

Purpose:
Test whether a shorter Short take-profit improves the Short side and total system without changing the Long side.

Benchmark: TEST 29
TEST 29: +36.69% return, PF 1.611, win rate 66.17%, max DD -6.92%.
