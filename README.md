# TEST 17

- Timeframe: 4h
- Signal source: ETHUSDT Futures
- LONG: ETHUSD_PERP (Binance COIN-M), modeled at fixed 1 ETH exposure
- SHORT: ETHUSDT (Binance USD-M), fixed 1 ETH exposure
- Long RSI: >55
- Short RSI: <30
- Supertrend: 10 / 5
- EMA: 50 / 200
- ADX: >25
- Bollinger: OFF
- Long SL: 2 ATR
- Short SL: 1.5 ATR
- TP: 4 ATR
- Trailing: activates +2 ATR, distance 2 ATR
- EMA exit: OFF

Run on Railway SSH:
`python backtest.py`

Note: ETHUSD_PERP is Binance COIN-M. This backtest models a fixed 1 ETH economic exposure; actual live COIN-M order sizing must account for the contract size and inverse contract mechanics.
