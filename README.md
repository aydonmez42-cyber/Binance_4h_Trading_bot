# TEST 16 — Fixed 1 ETH Dual Contract

- Signal / indicators: ETHUSDT Futures 4H
- LONG execution: ETHUSDT Futures, fixed 1.0 ETH
- SHORT execution: ETHUSDC Futures, fixed 1.0 ETH
- RSI short threshold: < 30
- EMA: 50 / 200
- Supertrend: 10 / 5
- ADX: > 25
- Bollinger short filter: OFF
- Long ATR SL: 2.0 ATR
- Short ATR SL: 1.5 ATR
- ATR TP: 4.0 ATR
- ATR trailing: activates at +2 ATR, distance 2 ATR
- EMA exit: OFF

## Railway

Set the service Start Command to:

`python main.py`

Then use Railway SSH to run:

`python backtest.py`

The backtest downloads Binance Futures data for ETHUSDT and ETHUSDC and writes:
- `backtest_trades.csv`
- `backtest_equity.csv`

## Important implementation note

The backtest stores `open_time` as the DataFrame index after mapping. Entry/exit timestamps are therefore read from `Series.name` rather than an `open_time` column.
