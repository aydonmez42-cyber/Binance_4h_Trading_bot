# Multi-Coin Scanner / Backtest V1

FINAL V1'i değiştirmeden Binance Futures USDT-M perpetual coin evreninde 4H backtest.
Coin bazlı optimizasyon ve gerçek emir yoktur.

Veri formatı: data/<SYMBOL>_4h.csv
Kolonlar: timestamp, open, high, low, close, volume

Çalıştırma:
python multicoin_backtest.py --data-dir data --output results
