# TEST32 Paper Trading + Dashboard + Telegram V2

Bu paket TEST32 stratejisinin gerçek Binance Futures piyasa verisiyle, fakat gerçek emir göndermeden çalıştırılması içindir.

## V2'de düzeltilen kritik konu: kalıcı state

Railway container dosya sistemi kalıcı değildir. Bu nedenle paper pozisyonu ve işlem geçmişi **Railway Volume** üzerinde `/data` altında tutulmalıdır.

Kullanılacak environment variable:

```text
PAPER_DATA_DIR=/data
```

Bu durumda:
- `/data/paper_state.json` = bakiye + açık pozisyon + bot state
- `/data/paper_trades.csv` = kapanan paper işlemler

Redeploy/restart sonrası state yeniden yüklenir.

## Railway Volume kurulumu

1. Railway projesini açın.
2. İlgili Service'i seçin.
3. **Volumes** bölümünden yeni Volume oluşturun.
4. Mount Path olarak tam olarak:

```text
/data
```

5. Variables bölümüne ekleyin:

```text
PAPER_DATA_DIR=/data
```

6. Telegram için:

```text
TELEGRAM_BOT_TOKEN=<BotFather yeni token>
TELEGRAM_CHAT_ID=<Telegram chat id>
TELEGRAM_VERIFY_ON_START=true
```

7. Start Command:

```bash
python paper_trading.py
```

## Telegram

Bot başlangıçta Telegram tokenını ve sohbet yapılandırmasını doğrular; başlangıçta mesaj göndermez. Böylece Railway restartlarında Telegram spam oluşmaz.

Bildirimler:
- Yeni LONG/SHORT açılışı
- Pozisyon kapanışı
- Her gün 09:00 Europe/Istanbul günlük raporu

Telegram mesajları plain text gönderilir; HTML/Markdown parse hataları nedeniyle oluşabilecek 400 hataları engellenmiştir. API hata gövdesi loglanır ancak bot tokenı loglanmaz.

## TEST32 kilitli strateji

- 4H
- Signal: ETHUSDT
- Long execution: ETHUSD_PERP
- Short execution: ETHUSDT
- Fixed 1 ETH
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
- Trailing +2 ATR / 2 ATR
- EMA exit OFF
- Supertrend exit OFF
- Stop sonrası özel re-entry OFF

## Güvenlik

- Bu paket gerçek Binance emirleri göndermez.
- Binance API key/secret kullanmaz.
- Telegram tokenı kaynak koda konulmamalıdır.
- Daha önce sızmış BotFather tokenlarını revoke edip yeni token kullanın.

## Telegram V3 güvenlik davranışı

- Startup doğrulaması `getMe` ile yapılır; Telegram sohbetine startup mesajı gönderilmez.
- Railway/container restartları Telegram mesajı üretmez.
- Sadece yeni pozisyon, pozisyon kapanışı ve günlük 09:00 raporu mesaj gönderir.
