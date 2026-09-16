# TEST32 RSI72 — XUTUM / TradingView Screener Scanner

Bu sürüm BIST 100 veya BIST Tüm-100 listesini birleştirmez.

## Evren

Scanner, her tarama öncesinde TradingView Turkey Screener API üzerinden:
- `is_primary = true`
- `typespecs = common`
- `type = stock`
- `exchange = BIST`
- `active_symbols_only = true`

filtreleriyle Borsa İstanbul'daki aktif, ana kotasyonlu, adi payları alır. Bu evren XUTUM/BIST Tüm için kullanılır.

TradingView'ın XUTUM bileşen sayfası BIST Tüm endeksinin şirket listesini sağlar. XUTUM endeksinde dönemsel bileşen değişiklikleri olduğu için liste ZIP içine sabitlenmek yerine runtime'da çekilir.

## Fallback

TradingView Screener erişilemezse CNBC-E XUTUM sayfası ikinci kaynak olarak denenir. Fallback de 500'den az sembol döndürürse tarama hata verir; BIST 100'e düşmez.

## Veri ve strateji

- Fiyat verisi: Yahoo Finance `.IS`
- 1H veri → BIST seansına göre 4H bar
- Sadece kapanmış 4H mum
- TEST32 RSI72 koşulları
- Gerçek emir yok
- SHORT sonucu yalnızca teknik sinyaldir.

## Önemli

Yaklaşık 650 hisse olduğundan ilk XUTUM taraması BIST100 taramasından daha uzun sürebilir. `BIST_SCANNER_WORKERS` varsayılan 6'dır.
