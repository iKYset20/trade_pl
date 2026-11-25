"""Backtest event-driven bar-per-bar untuk pending limit order.

Asumsi (konservatif):
* Data OHLC adalah harga BID (standar MT5). BUY terisi di ASK = BID + spread.
* Order hanya bisa terisi mulai bar setelah setup dibuat.
* Pada bar terisinya order, hanya SL yang dicek (TP baru dari bar berikutnya).
* Jika SL dan TP tersentuh di bar yang sama -> dianggap kena SL.
* Setup batal jika TP tersentuh sebelum terisi, close menembus invalidasi,
  atau kedaluwarsa.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..core.models import Direction, Setup, Trade
from ..risk.position import SymbolSpec, position_size, risk_money
from .metrics import compute_metrics


@dataclass
class RiskRules:
    initial_equity: float = 1000.0
    risk_per_trade_pct: float = 1.0
    max_daily_loss_pct: float = 3.0
    max_trades_per_day: int = 4
    max_open_positions: int = 1

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "RiskRules":
        r = cfg["risk"]
        return cls(r["initial_equity"], r["risk_per_trade_pct"], r["max_daily_loss_pct"],
                   r["max_trades_per_day"], r["max_open_positions"])


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: pd.Series
    metrics: dict[str, float]
    setups: list[Setup] = field(default_factory=list)

    def trades_frame(self) -> pd.DataFrame:
        rows = []
        for t in self.trades:
            rows.append({
                "setup_time": t.setup.created_time,
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "side": t.direction.label,
                "entry": t.entry_price,
                "sl": t.setup.sl,
                "tp": t.setup.tp,
                "exit": t.exit_price,
                "lots": t.lots,
                "reason": t.exit_reason,
                "pnl": round(t.pnl, 2),
                "r": round(t.r_multiple, 2),
                "score": t.setup.score,
                "confluence": "; ".join(t.setup.reasons),
            })
        return pd.DataFrame(rows)


def run_backtest(df: pd.DataFrame, setups: list[Setup], spec: SymbolSpec, rules: RiskRules) -> BacktestResult:
    o_high = df["high"].to_numpy()
    o_low = df["low"].to_numpy()
    o_close = df["close"].to_numpy()
    times = df.index
    days = times.normalize()
    spread = spec.spread

    by_created: dict[int, list[Setup]] = defaultdict(list)
    for s in setups:
        by_created[s.created_index].append(s)

    equity = rules.initial_equity
    equity_curve = []
    pending: list[Setup] = []
    open_trades: list[Trade] = []
    closed: list[Trade] = []
    day_pnl: dict[pd.Timestamp, float] = defaultdict(float)
    day_count: dict[pd.Timestamp, int] = defaultdict(int)
    day_start_equity: dict[pd.Timestamp, float] = {}

    def close_trade(tr: Trade, t: int, price: float, reason: str) -> None:
        nonlocal equity
        d = int(tr.direction)
        tr.exit_index, tr.exit_time, tr.exit_price, tr.exit_reason = t, times[t], price, reason
        tr.pnl = (price - tr.entry_price) * d * tr.lots * spec.contract_size - spec.commission_per_lot * tr.lots
        planned = risk_money(tr.lots, tr.entry_price, tr.setup.sl, spec)
        tr.r_multiple = tr.pnl / planned if planned > 0 else 0.0
        equity += tr.pnl
        day_pnl[days[t]] += tr.pnl
        closed.append(tr)

    for t in range(len(df)):
        day = days[t]
        day_start_equity.setdefault(day, equity)
        hi, lo, cl = o_high[t], o_low[t], o_close[t]

        # 1) kelola posisi terbuka
        for tr in list(open_trades):
            s = tr.setup
            if s.direction is Direction.LONG:
                hit_sl, hit_tp = lo <= s.sl, hi >= s.tp
            else:
                hit_sl, hit_tp = hi + spread >= s.sl, lo + spread <= s.tp
            if hit_sl:
                close_trade(tr, t, s.sl, "SL")
                open_trades.remove(tr)
            elif hit_tp:
                close_trade(tr, t, s.tp, "TP")
                open_trades.remove(tr)

        # 2) setup yang dibuat di bar sebelumnya menjadi aktif
        pending.extend(by_created.get(t - 1, []))

        # 3) proses pending order
        still: list[Setup] = []
        for s in pending:
            if t > s.expiry_index:
                continue
            long = s.direction is Direction.LONG
            touched = (lo + spread <= s.entry) if long else (hi >= s.entry)
            daily_loss_hit = -day_pnl[day] >= day_start_equity[day] * rules.max_daily_loss_pct / 100
            can_trade = (len(open_trades) < rules.max_open_positions
                         and day_count[day] < rules.max_trades_per_day and not daily_loss_hit)

            if touched and can_trade:
                lots = position_size(equity, rules.risk_per_trade_pct, s.entry, s.sl, spec)
                if lots <= 0:
                    continue
                tr = Trade(s, t, times[t], s.entry, lots)
                day_count[day] += 1
                stop_now = (lo <= s.sl) if long else (hi + spread >= s.sl)
                if stop_now:
                    close_trade(tr, t, s.sl, "SL")
                else:
                    open_trades.append(tr)
                continue

            tp_reached = (hi >= s.tp) if long else (lo + spread <= s.tp)
            invalid = (cl < s.invalidation) if long else (cl > s.invalidation)
            if tp_reached or invalid:
                continue
            still.append(s)
        pending = still
        equity_curve.append(equity)

    # tutup posisi yang masih terbuka di harga close terakhir
    for tr in open_trades:
        close_trade(tr, len(df) - 1, float(o_close[-1]), "EOD")

    curve = pd.Series(equity_curve, index=times, name="equity")
    return BacktestResult(closed, curve, compute_metrics(closed, curve, rules.initial_equity), setups)
