"""Market structure: swing high/low, BOS (Break of Structure), CHoCH (Change of Character).

Anti look-ahead: swing di indeks i baru DIKETAHUI pada bar i + right
(`confirmed_index`). Break structure hanya dievaluasi terhadap swing yang
sudah terkonfirmasi, memakai harga CLOSE bar berjalan.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..core.models import Direction


@dataclass
class Swing:
    index: int
    confirmed_index: int
    price: float
    kind: str  # "high" | "low"


@dataclass
class StructureBreak:
    index: int              # bar yang close menembus level
    direction: Direction    # LONG = break ke atas
    kind: str               # "BOS" | "CHoCH"
    level: float            # harga swing yang ditembus
    swing_index: int        # indeks swing yang ditembus
    opposite_swing: Swing | None  # swing berlawanan terakhir (asal impuls)


def find_swings(df: pd.DataFrame, left: int = 3, right: int = 3) -> list[Swing]:
    """Fraktal: high[i] adalah maksimum ketat di jendela [i-left, i+right]."""
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    n = len(df)
    swings: list[Swing] = []
    for i in range(left, n - right):
        h_win = high[i - left : i + right + 1]
        l_win = low[i - left : i + right + 1]
        if high[i] == h_win.max() and np.count_nonzero(h_win == high[i]) == 1:
            swings.append(Swing(i, i + right, float(high[i]), "high"))
        if low[i] == l_win.min() and np.count_nonzero(l_win == low[i]) == 1:
            swings.append(Swing(i, i + right, float(low[i]), "low"))
    swings.sort(key=lambda s: (s.confirmed_index, s.index))
    return swings


def analyze_structure(
    df: pd.DataFrame, left: int = 3, right: int = 3
) -> tuple[np.ndarray, list[StructureBreak], list[Swing]]:
    """Kembalikan (trend per bar, daftar break, daftar swing).

    trend: +1 bullish, -1 bearish, 0 belum diketahui. Nilai di bar t memakai
    data <= t saja.
    """
    close = df["close"].to_numpy()
    n = len(df)
    swings = find_swings(df, left, right)
    trend = np.zeros(n, dtype=int)
    breaks: list[StructureBreak] = []

    last_high: Swing | None = None
    last_low: Swing | None = None
    high_broken = low_broken = True
    state = 0
    si = 0
    for t in range(n):
        while si < len(swings) and swings[si].confirmed_index <= t:
            s = swings[si]
            if s.kind == "high":
                last_high, high_broken = s, False
            else:
                last_low, low_broken = s, False
            si += 1

        if last_high is not None and not high_broken and close[t] > last_high.price:
            kind = "CHoCH" if state == -1 else "BOS"
            breaks.append(StructureBreak(t, Direction.LONG, kind, last_high.price, last_high.index, last_low))
            high_broken = True
            state = 1
        elif last_low is not None and not low_broken and close[t] < last_low.price:
            kind = "CHoCH" if state == 1 else "BOS"
            breaks.append(StructureBreak(t, Direction.SHORT, kind, last_low.price, last_low.index, last_high))
            low_broken = True
            state = -1
        trend[t] = state
    return trend, breaks, swings
