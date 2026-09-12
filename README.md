# TEST 16 — Dual Contract / Fixed 1 ETH

## Architecture
- Timeframe: 4H
- Signal/indicator reference: ETHUSDT Futures
- LONG execution: ETHUSDT Futures
- SHORT execution: ETHUSDC Futures
- Position size: fixed **1 ETH** per trade
- RSI short threshold: **<30**
- Supertrend: 10 / 5
- EMA: 50 / 200 trend filter
- ADX: >25
- Bollinger short filter: OFF
- Long SL: 2 ATR
- Short SL: 1.5 ATR
- TP: 4 ATR
- Trailing activation: +2 ATR
- Trailing distance: 2 ATR
- EMA exit: OFF

## Important
This test uses Binance Futures OHLCV for both execution symbols. Signals are calculated from ETHUSDT so that the strategy logic remains identical while Long and Short are executed on separate contracts.

Funding costs are not included yet. Live deployment must also account for funding, actual futures fees, spread, margin and liquidation rules.
