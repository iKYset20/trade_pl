"""Metrik performa strategi."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..core.models import Trade


def compute_metrics(trades: list[Trade], equity: pd.Series, initial_equity: float) -> dict[str, float]:
    n = len(trades)
    pnl = np.array([t.pnl for t in trades]) if n else np.array([])
    r = np.array([t.r_multiple for t in trades]) if n else np.array([])
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    gross_win, gross_loss = wins.sum(), -losses.sum()
    peak = equity.cummax() if len(equity) else equity
    dd = ((equity - peak) / peak).min() if len(equity) else 0.0

    # maksimum kekalahan beruntun
    streak = max_streak = 0
    for p in pnl:
        streak = streak + 1 if p <= 0 else 0
        max_streak = max(max_streak, streak)

    final = float(equity.iloc[-1]) if len(equity) else initial_equity
    return {
        "trades": n,
        "win_rate_pct": round(100 * len(wins) / n, 2) if n else 0.0,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else float("inf") if n else 0.0,
        "expectancy_r": round(float(r.mean()), 3) if n else 0.0,
        "avg_win_r": round(float(r[r > 0].mean()), 2) if (r > 0).any() else 0.0,
        "avg_loss_r": round(float(r[r <= 0].mean()), 2) if (r <= 0).any() else 0.0,
        "net_profit": round(float(pnl.sum()), 2),
        "return_pct": round(100 * (final / initial_equity - 1), 2),
        "max_drawdown_pct": round(100 * float(dd), 2),
        "max_losing_streak": int(max_streak),
        "final_equity": round(final, 2),
    }


def format_metrics(m: dict[str, float]) -> str:
    labels = {
        "trades": "Jumlah trade",
        "win_rate_pct": "Win rate (%)",
        "profit_factor": "Profit factor",
        "expectancy_r": "Expectancy (R/trade)",
        "avg_win_r": "Rata-rata win (R)",
        "avg_loss_r": "Rata-rata loss (R)",
        "net_profit": "Net profit ($)",
        "return_pct": "Return (%)",
        "max_drawdown_pct": "Max drawdown (%)",
        "max_losing_streak": "Loss beruntun maks",
        "final_equity": "Equity akhir ($)",
    }
    width = max(len(v) for v in labels.values())
    return "\n".join(f"  {labels[k]:<{width}} : {m[k]}" for k in labels if k in m)
