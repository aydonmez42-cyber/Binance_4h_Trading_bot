"""TEST 10 - robustness / out-of-sample style period test.

Keeps TEST 9 parameters unchanged. Downloads the full history once so EMA200,
ATR and Supertrend have warm-up data, then runs independent backtests on
three fixed periods using the same strategy and execution model.
"""
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


def main():
    print(f"Downloading full {cfg.SYMBOL} {cfg.INTERVAL} history for indicator warm-up...")
    df = fetch_klines(cfg.SYMBOL, cfg.INTERVAL, "2020-01-01", cfg.DATA_END)
    print(f"Rows: {len(df):,}")
    df = add_indicators(df, cfg)

    rows = []
    all_trades = []
    all_equity = []

    for name, start, end in PERIODS:
        mask = df["open_time"] >= pd.Timestamp(start, tz="UTC")
        if end is not None:
            mask &= df["open_time"] <= pd.Timestamp(end, tz="UTC")
        period_df = df.loc[mask].copy().reset_index(drop=True)

        trades, equity_curve, _ = run_backtest(period_df)
        metrics = calculate_metrics(trades, equity_curve)
        metrics["period"] = name
        metrics["start"] = start
        metrics["end"] = end or str(df["open_time"].iloc[-1])
        rows.append(metrics)

        if not trades.empty:
            t = trades.copy()
            t["period"] = name
            all_trades.append(t)
        if not equity_curve.empty:
            e = equity_curve.copy()
            e["period"] = name
            all_equity.append(e)

    summary = pd.DataFrame(rows)
    summary = summary[[
        "period", "start", "end", "initial_capital", "final_equity", "net_profit",
        "return_pct", "trades", "wins", "losses", "win_rate_pct", "profit_factor",
        "expectancy_per_trade", "max_drawdown_pct", "long_trades", "short_trades",
        "long_win_rate_pct", "short_win_rate_pct"
    ]]
    summary.to_csv("test10_robustness_summary.csv", index=False)
    if all_trades:
        pd.concat(all_trades, ignore_index=True).to_csv("test10_trades.csv", index=False)
    if all_equity:
        pd.concat(all_equity, ignore_index=True).to_csv("test10_equity.csv", index=False)

    print("\n========== TEST 10 ROBUSTNESS ==========")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("========================================")
    print("Saved: test10_robustness_summary.csv, test10_trades.csv, test10_equity.csv")


if __name__ == "__main__":
    main()
