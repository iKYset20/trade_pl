"""Filter sesi (killzone). XAUUSD paling likuid di sesi London & New York."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def session_mask(index: pd.DatetimeIndex, sessions_utc: dict[str, list[str]],
                 server_utc_offset_hours: float = 0) -> np.ndarray:
    """True jika waktu bar (waktu server) jatuh di salah satu sesi (jam UTC)."""
    utc = index - pd.Timedelta(hours=server_utc_offset_hours)
    minutes = (utc.hour * 60 + utc.minute).to_numpy()
    mask = np.zeros(len(index), dtype=bool)
    for start, end in sessions_utc.values():
        s, e = _to_minutes(start), _to_minutes(end)
        mask |= (minutes >= s) & (minutes < e) if s < e else (minutes >= s) | (minutes < e)
    return mask


def session_name(ts: pd.Timestamp, sessions_utc: dict[str, list[str]],
                 server_utc_offset_hours: float = 0) -> str | None:
    utc = ts - pd.Timedelta(hours=server_utc_offset_hours)
    minutes = utc.hour * 60 + utc.minute
    for name, (start, end) in sessions_utc.items():
        s, e = _to_minutes(start), _to_minutes(end)
        if (s <= minutes < e) if s < e else (minutes >= s or minutes < e):
            return name
    return None
