"""Utilitas timeframe ala MT5."""

from __future__ import annotations

import pandas as pd

TF_MINUTES = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 60, "H4": 240, "D1": 1440,
}


def tf_minutes(tf: str) -> int:
    try:
        return TF_MINUTES[tf.upper()]
    except KeyError as exc:
        raise ValueError(f"Timeframe tidak dikenal: {tf}") from exc


def tf_timedelta(tf: str) -> pd.Timedelta:
    return pd.Timedelta(minutes=tf_minutes(tf))


def resample_ohlc(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Resample OHLCV (index = waktu open bar) ke timeframe lebih besar.

    Bar terakhir bisa belum lengkap; pemakai wajib memakai kolom
    `available_time` (= open + durasi) agar tidak terjadi look-ahead.
    """
    rule = f"{tf_minutes(tf)}min"
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in df.columns:
        agg["volume"] = "sum"
    out = df.resample(rule, label="left", closed="left").agg(agg).dropna(subset=["open"])
    out["available_time"] = out.index + tf_timedelta(tf)
    return out
