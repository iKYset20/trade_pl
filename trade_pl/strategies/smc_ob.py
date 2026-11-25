"""Strategi SMC: Order Block searah bias HTF dengan confluence.

Alur (contoh BUY):
1. Bias HTF (mis. H1) bullish berdasarkan market structure  -> WAJIB
2. LTF (mis. M5) membentuk BOS/CHoCH bullish                -> skor +1
3. Order block = candle bearish terakhir sebelum impuls
4. Confluence tambahan:
   * impuls diawali liquidity sweep (stop hunt)              -> +1
   * impuls meninggalkan FVG (displacement)                  -> +1
   * entry berada di area discount range impuls              -> +1
5. Pending BUY LIMIT di tepi OB (atau 50%), SL di bawah OB + buffer ATR,
   TP di ujung impuls (likuiditas), R:R minimal `min_rr`.
6. Batal jika: kedaluwarsa, close menembus SL, atau harga sudah mencapai TP
   sebelum entry terisi.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..analysis.indicators import atr
from ..analysis.sessions import session_mask
from ..analysis.smc import find_fvgs, has_fvg_in_leg, in_discount, order_block_from_break, swept_liquidity
from ..analysis.structure import analyze_structure
from ..core.models import Direction, Setup
from ..core.timeframes import resample_ohlc, tf_timedelta
from .base import Strategy


def htf_trend_on_ltf(ltf: pd.DataFrame, htf_tf: str, ltf_tf: str, left: int, right: int) -> np.ndarray:
    """Tren HTF yang SUDAH diketahui saat setiap bar LTF close."""
    htf = resample_ohlc(ltf, htf_tf)
    trend, _, _ = analyze_structure(htf, left, right)
    htf_known = pd.DataFrame({"available_time": htf["available_time"].to_numpy(), "trend": trend})
    ltf_close = pd.DataFrame({"close_time": ltf.index + tf_timedelta(ltf_tf)})
    merged = pd.merge_asof(
        ltf_close, htf_known.sort_values("available_time"),
        left_on="close_time", right_on="available_time", direction="backward",
    )
    return merged["trend"].fillna(0).astype(int).to_numpy()


class SMCOrderBlockStrategy(Strategy):
    name = "smc_ob"

    def __init__(self, cfg: dict[str, Any], ltf_tf: str = "M5", htf_tf: str = "H1",
                 server_utc_offset_hours: float = 0):
        self.cfg = cfg
        self.ltf_tf = ltf_tf
        self.htf_tf = htf_tf
        self.utc_offset = server_utc_offset_hours

    def generate_setups(self, ltf: pd.DataFrame) -> list[Setup]:
        c = self.cfg
        if len(ltf) < 100:
            return []
        htf_trend = htf_trend_on_ltf(ltf, self.htf_tf, self.ltf_tf,
                                     c["htf_swing_left"], c["htf_swing_right"])
        _, breaks, swings = analyze_structure(ltf, c["swing_left"], c["swing_right"])
        fvgs = find_fvgs(ltf)
        atr_v = atr(ltf, c["atr_period"]).to_numpy()
        in_session = (session_mask(ltf.index, c["sessions_utc"], self.utc_offset)
                      if c.get("use_sessions", True) else np.ones(len(ltf), dtype=bool))
        close = ltf["close"].to_numpy()

        setups: list[Setup] = []
        used_ob: set[int] = set()
        for brk in breaks:
            t = brk.index
            d = brk.direction
            if htf_trend[t] != int(d) or not in_session[t] or np.isnan(atr_v[t]):
                continue
            ob = order_block_from_break(ltf, brk, c["ob_lookback"])
            if ob is None or ob.index in used_ob:
                continue

            if c.get("entry_mode", "proximal") == "mid":
                entry = (ob.low + ob.high) / 2
            else:
                entry = ob.high if d is Direction.LONG else ob.low
            buffer = c["sl_atr_buffer"] * atr_v[t]
            sl = ob.low - buffer if d is Direction.LONG else ob.high + buffer
            risk = abs(entry - sl)
            if not (c["min_sl"] <= risk <= c["max_sl"]):
                continue
            # harga saat setup terbentuk harus masih di sisi yang benar dari entry
            if (close[t] - entry) * int(d) <= 0:
                continue

            tp = ob.leg_extreme
            rr = (tp - entry) * int(d) / risk
            if rr < c["min_rr"]:
                continue
            if rr > c["max_rr"]:
                tp = entry + int(d) * c["max_rr"] * risk

            reasons = [f"HTF {self.htf_tf} {'bullish' if d is Direction.LONG else 'bearish'}",
                       f"{brk.kind} {self.ltf_tf} @ {brk.level:.2f}"]
            score = 1
            if swept_liquidity(ltf, swings, ob):
                score += 1
                reasons.append("Liquidity sweep")
            if has_fvg_in_leg(fvgs, ob):
                score += 1
                reasons.append("FVG/displacement")
            if in_discount(entry, ob):
                score += 1
                reasons.append("Discount zone" if d is Direction.LONG else "Premium zone")
            if score < c["min_score"]:
                continue

            used_ob.add(ob.index)
            setups.append(Setup(
                created_index=t,
                created_time=ltf.index[t],
                direction=d,
                entry=round(entry, 2),
                sl=round(sl, 2),
                tp=round(tp, 2),
                expiry_index=t + c["order_expiry_bars"],
                invalidation=round(sl, 2),
                score=score,
                reasons=reasons,
                zone_low=round(ob.low, 2),
                zone_high=round(ob.high, 2),
            ))
        return setups


def build_strategy(cfg: dict[str, Any]) -> Strategy:
    name = cfg["strategy"]["name"]
    if name == "smc_ob":
        return SMCOrderBlockStrategy(
            cfg["strategy"], cfg["timeframes"]["ltf"], cfg["timeframes"]["htf"],
            cfg["broker"]["server_utc_offset_hours"],
        )
    raise ValueError(f"Strategi tidak dikenal: {name}")
