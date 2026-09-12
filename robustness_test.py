
import os
import pandas as pd

import config as cfg
from data_manager import fetch_klines
from indicators import add_indicators
from backtest import run_backtest, calculate_metrics

PERIODS = [
    ("2020-2022", "2020-01-01", "2022-12-31 23:59:59"),
    ("2023-2024", "2023-01-01", "2024-12-31 23:59:59"),
    ("2025-2026", "2025-01-01", None),
]

def slice_period(df, start, end):
    out = df[df["open_time"] >= pd.Timestamp(start, tz="UTC")].copy()
    if end is not None:
        out = out[out["open_time"] <= pd.Timestamp(end, tz="UTC")].copy()
    return out.reset_index(drop=True)

def main():
    print("TEST 26 ROBUSTNESS")
    print("MACD Long filter: MACD > Signal AND Histogram > 0")
    print("Base: TEST 25B | Long SL 3 ATR | Short SL 1.5 ATR")
    print("Fresh $10,000 account for each period.")
    print()

    # Download full history once so indicators have warm-up data.
    signal_df = fetch_klines(cfg.SIGNAL_SYMBOL, cfg.INTERVAL, cfg.DATA_START, cfg.DATA_END)
    long_df = fetch_klines(cfg.LONG_SYMBOL, cfg.INTERVAL, cfg.DATA_START, cfg.DATA_END, market_type="COIN_M")
    short_df = fetch_klines(cfg.SHORT_SYMBOL, cfg.INTERVAL, cfg.DATA_START, cfg.DATA_END, market_type="USD_M")

    print(f"Full rows: signal={len(signal_df):,}, long={len(long_df):,}, short={len(short_df):,}")
    signal_df = add_indicators(signal_df, cfg)

    summaries = []
    all_trades = []
    all_equity = []

    for label, start, end in PERIODS:
        period_signal = slice_period(signal_df, start, end)
        if period_signal.empty:
            print(f"{label}: NO DATA")
            continue

        trades, equity, final_equity = run_backtest(period_signal, long_df, short_df)
        metrics = calculate_metrics(trades, equity)

        row = {
            "period": label,
            "start": start,
            "end": end or "2026-12-31",
            **metrics,
        }
        summaries.append(row)

        if not trades.empty:
            t = trades.copy()
            t["period"] = label
            all_trades.append(t)

        if not equity.empty:
            e = equity.copy()
            e["period"] = label
            all_equity.append(e)

        print(f"{label}: trades={metrics.get('trades',0)}, "
              f"return={metrics.get('return_pct',0):.2f}%, "
              f"PF={metrics.get('profit_factor',0):.3f}, "
              f"win={metrics.get('win_rate_pct',0):.2f}%, "
              f"DD={metrics.get('max_drawdown_pct',0):.2f}%, "
              f"Long={metrics.get('long_trades',0)}, Short={metrics.get('short_trades',0)}")

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv("test26_robustness_summary.csv", index=False)

    if all_trades:
        pd.concat(all_trades, ignore_index=True).to_csv("test26_robustness_trades.csv", index=False)
    else:
        pd.DataFrame().to_csv("test26_robustness_trades.csv", index=False)

    if all_equity:
        pd.concat(all_equity, ignore_index=True).to_csv("test26_robustness_equity.csv", index=False)
    else:
        pd.DataFrame().to_csv("test26_robustness_equity.csv", index=False)

    print("\n========== ROBUSTNESS SUMMARY ==========")
    if not summary_df.empty:
        cols = ["period","trades","return_pct","profit_factor","expectancy_per_trade",
                "max_drawdown_pct","long_trades","short_trades",
                "long_win_rate_pct","short_win_rate_pct"]
        print(summary_df[cols].to_string(index=False))
    print("========================================")

if __name__ == "__main__":
    main()
