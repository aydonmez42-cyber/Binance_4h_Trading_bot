# TEST32 — Paper Trading

Bu paket TEST32 stratejisinin **gerçek Binance Futures piyasa verisiyle, fakat gerçek emir göndermeden** çalıştırılması içindir.

## ÖNEMLİ
- Gerçek emir göndermez.
- Binance API key/secret gerektirmez; yalnızca public Futures market-data endpoint'lerini kullanır.
- Sinyaller yalnızca kapanmış 4H ETHUSDT mumunda hesaplanır.
- Long execution: ETHUSD_PERP (COIN-M).
- Short execution: ETHUSDT (USD-M).
- Pozisyon boyutu: 1 ETH.
- SL/TP/trailing intrabar high/low ile izlenir.
- Aynı mumda SL ve TP birlikte dokunursa SL önce kabul edilir.
- Yeni trailing stop, aktive olduğu mumda geriye dönük uygulanmaz; sonraki mumdan itibaren etkili olur.
- Durum `paper_state.json` dosyasında saklanır; trade kayıtları `paper_trades.csv` dosyasına eklenir.

## Railway
Start Command:
```bash
python paper_trading.py
```

Web servis istenirse:
```bash
python main.py
```
Ancak Railway'de tek process kullanılacaksa paper trading sürecini çalıştırmak tercih edilir. Railway'in PORT healthcheck ihtiyacı varsa mevcut proje yapısına ayrıca health endpoint eklenebilir.

## TEST32 kilitli parametreleri
- 4H
- EMA 50/200
- Supertrend 10/6
- ADX >25
- RSI Long >55 / Short <30
- CCI Long >100 / Short <-50
- Stoch RSI Long D >30
- MACD Long filter ON (12/26/9)
- Long SL 3.5 ATR
- Short SL 1.5 ATR
- Long TP 4 ATR
- Short TP 3 ATR
- Trailing activation +2 ATR / distance 2 ATR
- EMA exit OFF
- Supertrend exit OFF
- Stop sonrası özel re-entry OFF

## İzlenecek dosyalar
`paper_state.json` ve `paper_trades.csv`.

İlk gerçek emir kesinlikle bu paket tarafından gönderilmemelidir. Paper trading dönemi tamamlandıktan sonra ayrı bir live-execution katmanı oluşturulmalıdır.

## Telegram bildirimleri

Railway Variables / Environment Variables bölümüne şunları ekleyin:

- `TELEGRAM_BOT_TOKEN` = Telegram bot token
- `TELEGRAM_CHAT_ID` = Bildirimlerin gönderileceği chat ID

Bot:
- Yeni paper pozisyon açıldığında anlık bildirim gönderir.
- Pozisyon kapandığında anlık bildirim gönderir.
- Her gün **09:00 Europe/Istanbul** saatinde günlük rapor gönderir.
- Servis 09:00'dan sonra yeniden başlarsa, o günün raporunu ilk çalışmada gönderir; aynı gün ikinci kez göndermez.
- Token/chat ID tanımlı değilse paper trading çalışmaya devam eder; sadece Telegram devre dışı kalır.

> Not: Telegram tokenını kaynak koduna koymayın; Railway Variables kullanın.
