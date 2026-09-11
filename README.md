# Binance 4H Trend-Cross Trading Bot — ATR Exit Version

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
- 4H timeframe
- Price < EMA100
- ADX(14) > 20
- RSI(14) < 50
- CCI(20) < -50 within last 3 closed candles
- Stoch RSI bearish K/D cross within last 3 closed candles
- Stoch RSI K < 80 on trigger candle
- EMA50 crosses below EMA100 on the closed trigger candle
- Trigger candle closes below EMA100

## Entry timing

Signals are calculated only on CLOSED 4H candles.
Execution occurs at the NEXT candle OPEN with configured slippage and fees.
The EMA50/EMA100 cross remains the entry trigger; other filters may have occurred during their allowed validity window.

## ATR exit engine

ATR is calculated with length 14. The ATR value on the closed signal candle is used to establish the initial exit levels.

Default model:
- Initial Stop Loss: 1.5 ATR
- Take Profit: 4.0 ATR
- Trailing activation: +2.0 ATR
- Trailing distance: 2.0 ATR
- EMA100 exit remains enabled

For LONG:
- SL = Entry - 1.5 ATR
- TP = Entry + 4 ATR
- Trailing activates after price reaches Entry + 2 ATR
- Trailing stop = Highest High - 2 ATR

For SHORT:
- SL = Entry + 1.5 ATR
- TP = Entry - 4 ATR
- Trailing activates after price reaches Entry - 2 ATR
- Trailing stop = Lowest Low + 2 ATR

## Intrabar backtest rule

Because the data is 4H OHLC, the exact order of high/low movement inside a candle is unknown. The backtest therefore uses a conservative rule: if a protective stop and profit target are both touched in the same candle, the protective stop is assumed to happen first.

If a new trailing stop is activated from a candle's extreme, it is tested from the next candle onward rather than retroactively inside the same candle. This avoids look-ahead optimism.

## Exit priority

1. ATR initial SL
2. ATR trailing SL
3. ATR TP
4. EMA100 close exit (generated on a closed candle and executed at next open)
5. End-of-data close

## Current data source limitation

Historical data currently comes from Binance Spot public klines. The production/backtest version should later be switched to Binance Futures klines and should model funding fees, Futures fees, leverage, margin and liquidation behavior.

## Run

```bash
pip install -r requirements.txt
python backtest.py
```

## Important research rule

Do not optimize parameters immediately. First compare this ATR-exit baseline with the original EMA100-only baseline. Then validate on multiple symbols and out-of-sample / walk-forward periods before any parameter optimization.


## Controlled Exit Test 1

This package is the first controlled ATR exit test after ATR Exit V1.

Parameters:
- Initial SL: 2.0 ATR
- TP: 4.0 ATR
- Trailing activation: +2.0 ATR
- Trailing distance: 2.0 ATR
- EMA100 exit: enabled

Only the initial SL multiplier was changed from ATR Exit V1 (1.5 ATR -> 2.0 ATR).
All entry rules and other exit parameters remain unchanged.

This is a research backtest, not a live-trading configuration.
