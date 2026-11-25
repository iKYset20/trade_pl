"""Live scanner: memantau candle baru dan mengirim alert setup (eksekusi manual)."""

from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd

from .core.models import Direction, Setup
from .data.base import DataProvider
from .notify.telegram import TelegramNotifier, format_setup
from .risk.position import SymbolSpec, position_size
from .strategies.base import Strategy

log = logging.getLogger(__name__)


def setup_status(df: pd.DataFrame, s: Setup, spread: float) -> str:
    """Status setup berdasarkan bar setelah dibuat: pending / filled / cancelled / expired."""
    for t in range(s.created_index + 1, len(df)):
        if t > s.expiry_index:
            return "expired"
        hi, lo, cl = df["high"].iat[t], df["low"].iat[t], df["close"].iat[t]
        long = s.direction is Direction.LONG
        if (lo + spread <= s.entry) if long else (hi >= s.entry):
            return "filled"
        if ((hi >= s.tp) if long else (lo + spread <= s.tp)) or \
           ((cl < s.invalidation) if long else (cl > s.invalidation)):
            return "cancelled"
    return "pending"


class Scanner:
    def __init__(self, provider: DataProvider, strategy: Strategy, cfg: dict[str, Any],
                 notifier: TelegramNotifier | None = None, equity: float | None = None):
        self.provider = provider
        self.strategy = strategy
        self.cfg = cfg
        self.notifier = notifier or TelegramNotifier()
        self.spec = SymbolSpec.from_config(cfg)
        self.equity = equity or cfg["risk"]["initial_equity"]
        self.symbol = cfg["symbol"]["name"]
        self.ltf = cfg["timeframes"]["ltf"]
        self.htf = cfg["timeframes"]["htf"]
        self._seen: set[tuple] = set()
        self._last_bar: pd.Timestamp | None = None

    def _emit(self, s: Setup, prefix: str = "") -> None:
        key = (s.created_time, int(s.direction), s.entry)
        if key in self._seen:
            return
        self._seen.add(key)
        lots = position_size(self.equity, self.cfg["risk"]["risk_per_trade_pct"], s.entry, s.sl, self.spec)
        msg = prefix + format_setup(s, self.symbol, lots, self.ltf, self.htf)
        print(msg + "\n" + "-" * 40, flush=True)
        self.notifier.send(msg)

    def scan_once(self, include_active: bool = False) -> list[Setup]:
        df = self.provider.get_ohlcv(self.symbol, self.ltf, self.cfg["scanner"]["bars"])
        last = df.index[-1]
        if self._last_bar is not None and last == self._last_bar and not include_active:
            return []
        self._last_bar = last
        setups = self.strategy.generate_setups(df)
        out = []
        for s in setups:
            if s.created_index == len(df) - 1:
                self._emit(s)
                out.append(s)
            elif include_active and setup_status(df, s, self.spec.spread) == "pending":
                self._emit(s, prefix="[MASIH AKTIF] ")
                out.append(s)
        return out

    def run(self) -> None:
        poll = self.cfg["scanner"]["poll_seconds"]
        log.info("Scanner %s %s/%s berjalan (Ctrl+C untuk berhenti)", self.symbol, self.ltf, self.htf)
        self.scan_once(include_active=True)
        while True:
            try:
                self.scan_once()
            except Exception as exc:  # jaga agar loop tetap hidup
                log.exception("Scan gagal: %s", exc)
            time.sleep(poll)
