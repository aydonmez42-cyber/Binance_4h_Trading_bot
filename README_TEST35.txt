TEST35 — TEST32 + 1D REGIME FILTER

Baseline: TEST32 is frozen. Only one new component is added: the 1D regime filter.

1D regime rules (from TRADE BOT — UYGULAMA KURAL SETİ v1.0, R-01/R-02/R-04):
- VOLATILE first: ATRP percentile over trailing 365 daily bars >90 or <10.
- BULL: close > EMA200 AND EMA50 > EMA200 AND ADX >25 AND +DI > -DI.
- BEAR: close < EMA200 AND EMA50 < EMA200 AND ADX >25 AND -DI > +DI.
- Otherwise RANGE.
- BULL permits LONG only; BEAR permits SHORT only; RANGE/VOLATILE permit no new trades.
- Regime changes require 2 consecutive daily bars with the same candidate regime.

Important:
- The project remains permanently 4H for signal/execution.
- The 1D series is only a higher-timeframe directional filter.
- No 1H entry engine is added.
- TEST32 ATR stops/TP/trailing, fixed 1 ETH, symbols, Supertrend, MACD, RSI, CCI and Stoch rules are unchanged.
- No funding/OI/BTC/RS/score/structure/FOMO/volume rules are added in TEST35.
- Closed daily/4H bars only; no look-ahead from future daily bars.

Run:
python backtest.py
