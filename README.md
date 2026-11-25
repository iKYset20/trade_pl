# trade_pl — Asisten Analisis XAUUSD (SMC + Price Action)

Aplikasi untuk menganalisis XAUUSD secara otomatis dari MetaTrader 5, mendeteksi setup
Smart Money Concept (Order Block + confluence), dan mengirim **alert entry / SL / TP / lot**
untuk dieksekusi **manual**. Strategi yang sama dipakai untuk backtest dan live, jadi hasil
uji historis mencerminkan sinyal yang akan diterima.

> ⚠️ Alat bantu analisis, bukan jaminan profit. Selalu backtest dengan data broker Anda
> dan uji di akun demo sebelum memakai uang sungguhan.

## Arsitektur

```
MT5 / CSV ──► data/ ──► analysis/ ──► strategies/ ──► risk/ ──► notify/ (Telegram + konsol)
                         │ struktur      │ setup        │ lot        ▲
                         │ OB, FVG       │ confluence   │ batas      │
                         │ sweep, sesi   ▼              ▼ harian     │
                         └──────────► backtest/ (engine + metrik)    scanner.py (live)
```

| Folder | Isi |
|---|---|
| `trade_pl/core` | Model (`Setup`, `Trade`), konfigurasi, utilitas timeframe |
| `trade_pl/data` | Provider MT5, CSV (ekspor MT5), data sintetis untuk tes |
| `trade_pl/analysis` | Indikator (ATR, EMA, RSI), swing/BOS/CHoCH, Order Block, FVG, liquidity sweep, filter sesi |
| `trade_pl/strategies` | Strategi plugin; `smc_ob.py` = strategi pertama |
| `trade_pl/risk` | Position sizing XAUUSD (1 lot = 100 oz), termasuk spread & komisi |
| `trade_pl/backtest` | Engine bar-per-bar + metrik (win rate, PF, expectancy R, drawdown) |
| `trade_pl/notify` | Format sinyal & bot Telegram |
| `trade_pl/scanner.py` | Live scanner untuk alert |

## Strategi `smc_ob`

Contoh untuk BUY (SELL kebalikannya):

1. **Bias HTF** (default H1) bullish berdasarkan market structure (**wajib**)
2. **BOS/CHoCH bullish** di LTF (default M5), +1 skor
3. **Order Block** = candle bearish terakhir sebelum impuls yang menembus struktur
4. Confluence:
   - **Liquidity sweep** (impuls diawali stop hunt di bawah swing low), +1
   - **FVG / displacement** di dalam impuls, +1
   - **Entry di discount zone** (di bawah 50% range impuls), +1
5. Hanya di **killzone London & New York** (bisa diubah)
6. **BUY LIMIT** di tepi OB, **SL** di bawah OB + buffer ATR, **TP** di ujung impuls
   (likuiditas). Setup dengan R:R < 1:2 ditolak.
7. Order dibatalkan kalau kedaluwarsa, close menembus SL, atau TP tersentuh sebelum entry terisi.

Semua parameter ada di `config/settings.yaml`. Contohnya `ltf: M1/M5` untuk scalping,
`M15` + `htf: H4` untuk intraday, atau `entry_mode: mid` untuk SL lebih kecil.

### Anti look-ahead bias
Swing baru dianggap ada setelah `swing_right` bar berikutnya close, dan tren HTF baru
dipakai setelah candle HTF-nya close. Tes `test_strategy_has_no_lookahead` memastikan
setup di masa lalu tidak berubah ketika data masa depan ditambahkan.

### Asumsi backtest (konservatif)
Data = harga BID, BUY terisi di ASK (bid + spread). Order tidak bisa terisi di bar
pembentuknya. Kalau SL dan TP tersentuh di bar yang sama, dihitung SL. Komisi dan spread
ikut diperhitungkan.

## Instalasi

`MetaTrader5` (library Python) **hanya berjalan di Windows**, dengan terminal MT5
terpasang dan sudah login.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # lalu isi login MT5 & token Telegram
```

Sesuaikan `config/settings.yaml`:
- `symbol.name`: nama simbol emas di broker Anda (`XAUUSD`, `XAUUSDm`, `GOLD`, ...)
- `broker.server_utc_offset_hours`: zona waktu server broker (umumnya 2, atau 3 saat DST)
- `symbol.spread` / `commission_per_lot`: sesuai akun Anda

## Pemakaian

```bash
# 1. Unduh data historis dari MT5
python -m trade_pl fetch --bars 100000 --out data/XAUUSD_M5.csv

# 2. Backtest
python -m trade_pl backtest --source csv --csv data/XAUUSD_M5.csv --out output/bt1
#    (tanpa MT5: --source synthetic hanya untuk menguji pipeline)

# 3. Cek setup yang aktif saat ini
python -m trade_pl scan --once --equity 1000

# 4. Scanner live + alert Telegram
python -m trade_pl scan --equity 1000

# Tes
pytest -q
```

Contoh alert:
```
🟢 XAUUSD BUY LIMIT (M5/H1)
Entry       : 2651.40
Stop Loss   : 2648.90  (2.50)
Take Profit : 2658.90  (R:R 1:3.0)
Zona OB     : 2649.60 - 2651.40
Skor        : 4/4
Confluence  : HTF H1 bullish, CHoCH M5 @ 2652.10, Liquidity sweep, FVG/displacement, Discount zone
Lot saran   : 0.03
```

### Bot Telegram
1. Chat ke `@BotFather` → `/newbot` → salin token ke `TELEGRAM_BOT_TOKEN`
2. Kirim pesan apa saja ke bot Anda, lalu buka
   `https://api.telegram.org/bot<TOKEN>/getUpdates` untuk melihat `chat.id` → `TELEGRAM_CHAT_ID`

## Roadmap

- [x] **Fase 1–2**: data MT5/CSV, struktur SMC, strategi OB, risk sizing, backtest, scanner + Telegram
- [ ] **Fase 3**: laporan backtest HTML + chart (zona OB/FVG di grafik), walk-forward & optimasi parameter, statistik per sesi/hari
- [ ] **Fase 4**: dashboard web (FastAPI + TradingView Lightweight Charts), multi-timeframe sekaligus (M1/M5/M15)
- [ ] **Fase 5**: jurnal trading (catat eksekusi manual, bandingkan live dan backtest), filter berita high-impact (NFP, CPI, FOMC)
- [ ] **Fase 6**: semi-auto (konfirmasi satu klik → order ke MT5) dengan kill-switch & batas kerugian harian
- [ ] **Fase 7**: model ML sebagai filter kualitas setup (probabilitas berhasil per setup)
