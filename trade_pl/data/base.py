"""Interface data provider. Semua provider mengembalikan DataFrame OHLCV
dengan index DatetimeIndex (waktu OPEN bar, waktu server broker) dan kolom
open, high, low, close, volume. Hanya bar yang SUDAH close yang dikembalikan.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

REQUIRED_COLUMNS = ["open", "high", "low", "close"]


class DataProvider(ABC):
    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        """Ambil `bars` candle terakhir yang sudah close."""


def validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom OHLC hilang: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Index harus DatetimeIndex")
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if "volume" not in df.columns:
        df["volume"] = 0.0
    return df[["open", "high", "low", "close", "volume"]].astype(float)
