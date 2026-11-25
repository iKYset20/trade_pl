import numpy as np
import pandas as pd

from trade_pl.analysis.smc import find_fvgs
from trade_pl.analysis.structure import analyze_structure, find_swings
from trade_pl.core.models import Direction
from trade_pl.data.synthetic import generate_ohlcv


def _frame(highs, lows):
    idx = pd.date_range("2025-01-06", periods=len(highs), freq="5min")
    highs, lows = np.array(highs, float), np.array(lows, float)
    mid = (highs + lows) / 2
    return pd.DataFrame({"open": mid, "high": highs, "low": lows, "close": mid, "volume": 1.0}, index=idx)


def test_swing_confirmed_only_after_right_bars():
    df = _frame([1, 2, 3, 9, 3, 2, 1, 2], [0, 1, 2, 8, 2, 1, 0, 1])
    sw = [s for s in find_swings(df, 2, 2) if s.kind == "high"]
    assert sw and sw[0].index == 3 and sw[0].confirmed_index == 5


def test_bullish_bos_detected():
    # swing high 10 di indeks 3, lalu close menembus ke atas
    highs = [5, 6, 7, 10, 7, 6, 5, 6, 8, 11, 12]
    lows = [4, 5, 6, 9, 6, 5, 4, 5, 7, 10.5, 11]
    df = _frame(highs, lows)
    df["close"] = df["high"] - 0.2
    _, breaks, _ = analyze_structure(df, 2, 2)
    ups = [b for b in breaks if b.direction is Direction.LONG]
    assert ups and ups[0].level == 10 and ups[0].index == 9


def test_fvg():
    df = _frame([10, 12, 15], [9, 10, 13])
    f = find_fvgs(df)
    assert len(f) == 1 and f[0].direction is Direction.LONG and (f[0].low, f[0].high) == (10, 13)


def test_structure_has_no_lookahead():
    df = generate_ohlcv(3000, seed=1)
    trend_full, breaks_full, _ = analyze_structure(df)
    k = 2000
    trend_cut, breaks_cut, _ = analyze_structure(df.iloc[:k])
    assert np.array_equal(trend_full[:k], trend_cut)
    assert [(b.index, b.level) for b in breaks_full if b.index < k] == [(b.index, b.level) for b in breaks_cut]
