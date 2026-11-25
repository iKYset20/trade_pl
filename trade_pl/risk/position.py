"""Manajemen risiko: ukuran lot dan batas kerugian."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class SymbolSpec:
    contract_size: float = 100.0
    lot_step: float = 0.01
    min_lot: float = 0.01
    max_lot: float = 50.0
    spread: float = 0.25
    commission_per_lot: float = 7.0

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "SymbolSpec":
        s = cfg["symbol"]
        return cls(s["contract_size"], s["lot_step"], s["min_lot"], s["max_lot"],
                   s["spread"], s["commission_per_lot"])


def position_size(equity: float, risk_pct: float, entry: float, sl: float, spec: SymbolSpec) -> float:
    """Lot sehingga kerugian di SL (termasuk spread & komisi) ~= risk_pct% equity.

    XAUUSD: 1 lot = 100 oz -> pergerakan $1 = $100 per lot.
    Mengembalikan 0 jika lot minimum pun melebihi risiko yang diizinkan.
    """
    risk_money = equity * risk_pct / 100
    loss_per_lot = (abs(entry - sl) + spec.spread) * spec.contract_size + spec.commission_per_lot
    if loss_per_lot <= 0:
        return 0.0
    raw = risk_money / loss_per_lot
    lots = math.floor(raw / spec.lot_step + 1e-9) * spec.lot_step
    lots = min(round(lots, 2), spec.max_lot)
    return lots if lots >= spec.min_lot else 0.0


def risk_money(lots: float, entry: float, sl: float, spec: SymbolSpec) -> float:
    return lots * ((abs(entry - sl) + spec.spread) * spec.contract_size + spec.commission_per_lot)
