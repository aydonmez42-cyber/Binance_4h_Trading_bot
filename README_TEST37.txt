TEST 36 — TEST32 + 1D REGIME + CONFIRMED 4H MARKET STRUCTURE

Base: TEST35. Only one controlled change is added: confirmed 4H market structure as a hard entry-direction filter.

Market structure:
- Confirmed swing pivots use 5 bars left + 5 bars right.
- A pivot at bar j is only available from confirmation bar j+5 onward.
- Bullish structure: latest confirmed swing high > previous confirmed swing high AND latest confirmed swing low > previous confirmed swing low (HH + HL).
- Bearish structure: latest confirmed swing high < previous confirmed swing high AND latest confirmed swing low < previous confirmed swing low (LH + LL).
- LONG entries require structure_bias == LONG.
- SHORT entries require structure_bias == SHORT.
- Until two confirmed highs and two confirmed lows exist, structure is NONE and no directional entry is permitted by this filter.

Unchanged from TEST35:
- 4H timeframe is permanent.
- 1D regime filter remains active with the TEST35 settings.
- TEST32 entry filters, Supertrend filter, MACD long filter and ATR exits remain unchanged.
- Fixed 1 ETH economic exposure.
- LONG ETHUSD COIN-M; SHORT ETHUSDT USD-M.
- No BOS emergency exit is added in TEST37; this test isolates structure as an entry filter only.
- No 1H entry engine, funding/OI, BTC confirmation, relative strength, score engine, risk-based sizing or portfolio layer is added.
- Signals use closed candles only and entries execute at the next candle open.

Purpose:
Measure whether confirmed 4H HH/HL vs LH/LL structure improves TEST35 trade quality without changing the rest of the system.


TEST37 — TEST36 + FOMO VETO
=============================
Only one controlled change is added to TEST36: FOMO extension veto.

Rule adapted to the project-fixed 4H decision timeframe:
  abs(C[4h,0] - C[4h,1]) > 3 * ATR(4h,1) -> block new entry.

The current and previous bars are closed bars; ATR is taken from the previous
closed bar. This is an adaptation of V-34 because the project has permanently
fixed its decision timeframe at 4H. No 1H entry engine is introduced.

Everything else is unchanged from TEST36. No score, risk sizing, funding/OI,
BTC confirmation, relative strength, partial exits, or live execution changes.
