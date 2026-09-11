# TEST 10 — TEST 9 Robustness Test

This test does **not** change the TEST 9 strategy parameters.

It evaluates the same configuration independently across:

- 2020–2022
- 2023–2024
- 2025–2026

The full history is downloaded first so EMA200, ATR and Supertrend have proper warm-up data. Each period then starts with a fresh $10,000 account and no open position.

### Strategy kept unchanged
- BTCUSDT, 4H
- EMA50 / EMA200 trend filter
- Supertrend 10 / 5
- ADX > 25
- RSI / CCI / Stoch RSI filters unchanged
- TEST 9 Bollinger short filter unchanged
- ATR SL 2x
- ATR TP 4x
- trailing activation +2x ATR
- trailing distance 2x ATR
- EMA exit OFF
- 100% equity position sizing, 1x leverage

### Run
```bash
python robustness_test.py
```

Outputs:
- `test10_robustness_summary.csv`
- `test10_trades.csv`
- `test10_equity.csv`

The purpose is to see whether TEST 9 remains effective across different BTC market regimes rather than selecting parameters based only on the full 2020–2026 result.
