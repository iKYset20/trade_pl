"""Generator data sintetis mirip XAUUSD untuk demo dan pengujian.

BUKAN data pasar nyata - hasil backtest di data ini tidak bermakna untuk
menilai strategi, hanya untuk memverifikasi bahwa pipeline berjalan.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_ohlcv(
    bars: int = 20_000,
    timeframe_minutes: int = 5,
    start_price: float = 2650.0,
    seed: int = 42,
    start: str = "2025-01-06 00:00",
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    # tren berganti-ganti (regime) + volatilitas berkelompok
    regime_len = rng.integers(150, 600, size=bars // 150 + 2)
    drift = np.concatenate([np.full(n, rng.normal(0, 0.06)) for n in regime_len])[:bars]
    vol = np.abs(rng.normal(0.9, 0.25, size=bars)) * (timeframe_minutes / 5) ** 0.5
    vol = pd.Series(vol).rolling(20, min_periods=1).mean().to_numpy()
    rets = drift + rng.standard_normal(bars) * vol
    close = start_price + np.cumsum(rets)
    open_ = np.concatenate([[start_price], close[:-1]])
    spread_hi = np.abs(rng.normal(0, vol * 0.8))
    spread_lo = np.abs(rng.normal(0, vol * 0.8))
    high = np.maximum(open_, close) + spread_hi
    low = np.minimum(open_, close) - spread_lo

    # indeks hanya hari kerja (pasar emas tutup akhir pekan)
    idx = pd.date_range(start, periods=int(bars * 1.5) + 10, freq=f"{timeframe_minutes}min")
    idx = idx[idx.dayofweek < 5][:bars]
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close,
         "volume": rng.integers(100, 2000, size=bars).astype(float)},
        index=pd.DatetimeIndex(idx, name="time"),
    )
