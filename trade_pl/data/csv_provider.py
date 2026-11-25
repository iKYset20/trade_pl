"""Provider dari file CSV.

Mendukung:
* Ekspor History Center MT5 (tab-separated: <DATE> <TIME> <OPEN> ... )
* CSV umum dengan kolom time/datetime, open, high, low, close[, volume]
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import DataProvider, validate_ohlcv


def load_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    with open(path, encoding="utf-8-sig") as f:
        head = f.readline()
    sep = "\t" if "\t" in head else ","
    raw = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
    raw.columns = [c.strip().strip("<>").lower() for c in raw.columns]

    if "date" in raw.columns and "time" in raw.columns:
        ts = pd.to_datetime(raw["date"].astype(str) + " " + raw["time"].astype(str))
    else:
        tcol = next((c for c in ("time", "datetime", "timestamp", "date") if c in raw.columns), None)
        if tcol is None:
            raise ValueError("Kolom waktu tidak ditemukan di CSV")
        col = raw[tcol]
        ts = pd.to_datetime(col, unit="s") if pd.api.types.is_numeric_dtype(col) else pd.to_datetime(col)

    if "volume" not in raw.columns:
        raw["volume"] = raw.get("tickvol", raw.get("tick_volume", 0.0))
    df = raw.set_index(pd.DatetimeIndex(ts, name="time"))
    return validate_ohlcv(df)


class CSVProvider(DataProvider):
    def __init__(self, path: str | Path):
        self.df = load_csv(path)

    def get_ohlcv(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        return self.df.tail(bars).copy()
