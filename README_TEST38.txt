TEST38 — 4H Volume Confirmation

Base: TEST36 (1D regime + confirmed 4H market structure + TEST32/26 rules).

Added only:
- Volume SMA(20)
- Volume Ratio = current 4H volume / SMA(20) volume
- New entry is blocked when Volume Ratio < 1.0
- Applied to both LONG and SHORT

Important:
- Fixed timeframe remains 4H.
- Signals use closed 4H candles.
- No FOMO filter from TEST37.
- No funding/OI, BTC confirmation, relative strength, score engine, 1H engine, risk-based sizing or live orders.
- Existing TEST36 parameters remain unchanged.
