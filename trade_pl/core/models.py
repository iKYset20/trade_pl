"""Model data inti yang dipakai bersama oleh backtest dan live scanner."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import pandas as pd


class Direction(IntEnum):
    LONG = 1
    SHORT = -1

    @property
    def label(self) -> str:
        return "BUY" if self is Direction.LONG else "SELL"


@dataclass
class Setup:
    """Rencana trade (pending limit order) hasil strategi.

    `created_index` adalah indeks bar LTF (sudah close) saat setup diketahui.
    Order baru boleh terisi mulai bar `created_index + 1`.
    """

    created_index: int
    created_time: pd.Timestamp
    direction: Direction
    entry: float
    sl: float
    tp: float
    expiry_index: int
    invalidation: float          # close melewati level ini -> setup batal
    score: int
    reasons: list[str] = field(default_factory=list)
    zone_low: float = 0.0
    zone_high: float = 0.0

    @property
    def risk(self) -> float:
        return abs(self.entry - self.sl)

    @property
    def rr(self) -> float:
        return abs(self.tp - self.entry) / self.risk if self.risk > 0 else 0.0


@dataclass
class Trade:
    setup: Setup
    entry_index: int
    entry_time: pd.Timestamp
    entry_price: float
    lots: float
    exit_index: int | None = None
    exit_time: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str = ""
    pnl: float = 0.0
    r_multiple: float = 0.0

    @property
    def direction(self) -> Direction:
        return self.setup.direction
