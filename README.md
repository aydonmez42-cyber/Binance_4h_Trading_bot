# Binance 4H Trading Bot — Baseline

## Strategy

### LONG
- 4H timeframe
- Price > EMA100
- ADX(14) > 20
- RSI(14) > 50
- CCI(20) > +50 within last 3 closed candles
- Stoch RSI bullish K/D cross within last 3 closed candles
- Stoch RSI K > 20 on trigger candle
- EMA50 crosses above EMA100 on the closed trigger candle
- Trigger candle closes above EMA100

### SHORT
- Price < EMA100
- ADX(14) > 20
- RSI(14) < 50
- CCI(20) < -50 within last 3 closed candles
- Stoch RSI bearish K/D cross within last 3 closed candles
- Stoch RSI K < 80 on trigger candle
- EMA50 crosses below EMA100 on the closed trigger candle
- Trigger candle closes below EMA100

### Exit
LONG:
- Closed 4H candle closes below EMA100

SHORT:
- Closed 4H candle closes above EMA100

## Important signal architecture

EMA50/EMA100 cross is the ENTRY TRIGGER.

The other conditions do NOT have to occur on the same candle.
CCI and Stoch RSI have configurable recent-validity windows.
ADX, RSI and price-vs-EMA100 are checked on the trigger candle.

Signals are generated only from CLOSED candles.
Execution in the backtest is at the NEXT candle OPEN with configurable slippage and fees.

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python backtest.py
```

Default:
- BTCUSDT
- Binance Spot public klines for historical OHLCV
- 4H
- from 2020-01-01

For a Futures production backtest, the data source should later be switched to Binance Futures klines and funding costs should be modeled.

## Phase 2

Do not optimize immediately. First save the baseline result.

Then add:
- train/test split
- out-of-sample testing
- walk-forward analysis
- parameter sensitivity
- multi-symbol validation
- funding fees
- realistic execution model
- live paper trading
