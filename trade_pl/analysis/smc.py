"""Konsep Smart Money: Order Block, Fair Value Gap, Liquidity Sweep, Premium/Discount."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..core.models import Direction
from .structure import StructureBreak, Swing


@dataclass
class OrderBlock:
    index: int            # candle OB
    created_index: int    # bar break structure (OB baru valid sejak sini)
    direction: Direction  # LONG = bullish OB (demand)
    low: float
    high: float
    leg_extreme: float    # ujung impuls (high untuk bullish) - target likuiditas awal
    origin: float         # ujung awal impuls (low untuk bullish)


@dataclass
class FVG:
    index: int            # candle ketiga (gap diketahui saat bar ini close)
    direction: Direction
    low: float
    high: float


def find_fvgs(df: pd.DataFrame, min_size: float = 0.0) -> list[FVG]:
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    out: list[FVG] = []
    for i in range(2, len(df)):
        if low[i] - high[i - 2] > min_size:
            out.append(FVG(i, Direction.LONG, float(high[i - 2]), float(low[i])))
        elif low[i - 2] - high[i] > min_size:
            out.append(FVG(i, Direction.SHORT, float(high[i]), float(low[i - 2])))
    return out


def order_block_from_break(
    df: pd.DataFrame, brk: StructureBreak, lookback: int = 10
) -> OrderBlock | None:
    """OB = candle berlawanan terakhir sebelum impuls yang menembus struktur.

    Bullish: cari titik terendah antara swing yang ditembus dan bar break,
    lalu candle bearish terakhir di sekitar titik itu.
    """
    o = df["open"].to_numpy()
    c = df["close"].to_numpy()
    h = df["high"].to_numpy()
    lo = df["low"].to_numpy()
    start = max(brk.swing_index, brk.index - lookback * 3, 0)
    end = brk.index
    if end - start < 1:
        return None
    seg = slice(start, end + 1)

    if brk.direction is Direction.LONG:
        pivot = start + int(np.argmin(lo[seg]))
        for j in range(pivot, max(pivot - lookback, start - 1), -1):
            if c[j] < o[j]:
                return OrderBlock(j, brk.index, Direction.LONG, float(lo[j]), float(h[j]),
                                  float(h[pivot:end + 1].max()), float(lo[pivot]))
        return None
    pivot = start + int(np.argmax(h[seg]))
    for j in range(pivot, max(pivot - lookback, start - 1), -1):
        if c[j] > o[j]:
            return OrderBlock(j, brk.index, Direction.SHORT, float(lo[j]), float(h[j]),
                              float(lo[pivot:end + 1].min()), float(h[pivot]))
    return None


def swept_liquidity(
    df: pd.DataFrame, swings: list[Swing], ob: OrderBlock, lookback_swings: int = 5
) -> bool:
    """True jika impuls diawali sapuan likuiditas: ujung awal impuls menembus
    swing sebelumnya (yang sudah terkonfirmasi) lalu harga berbalik."""
    close = df["close"].to_numpy()
    kind = "low" if ob.direction is Direction.LONG else "high"
    prior = [s for s in swings if s.kind == kind and s.confirmed_index < ob.index][-lookback_swings:]
    for s in prior:
        if ob.direction is Direction.LONG and ob.origin < s.price and close[ob.created_index] > s.price:
            return True
        if ob.direction is Direction.SHORT and ob.origin > s.price and close[ob.created_index] < s.price:
            return True
    return False


def has_fvg_in_leg(fvgs: list[FVG], ob: OrderBlock) -> bool:
    """Displacement: ada FVG searah di antara candle OB dan bar break."""
    return any(f.direction is ob.direction and ob.index < f.index <= ob.created_index for f in fvgs)


def in_discount(price: float, ob: OrderBlock) -> bool:
    """Entry di area discount (bullish) / premium (bearish) dari range impuls."""
    eq = (ob.origin + ob.leg_extreme) / 2
    return price <= eq if ob.direction is Direction.LONG else price >= eq
