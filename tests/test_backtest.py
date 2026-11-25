import pandas as pd

from trade_pl.backtest.engine import RiskRules, run_backtest
from trade_pl.core.models import Direction, Setup
from trade_pl.risk.position import SymbolSpec

SPEC = SymbolSpec(spread=0.0, commission_per_lot=0.0)
RULES = RiskRules(initial_equity=10_000, risk_per_trade_pct=1.0)


def _df(bars):
    idx = pd.date_range("2025-01-06 08:00", periods=len(bars), freq="5min")
    return pd.DataFrame(bars, columns=["open", "high", "low", "close"], index=idx).assign(volume=1.0)


def _long(created=0):
    return Setup(created, pd.Timestamp("2025-01-06 08:00"), Direction.LONG,
                 entry=100.0, sl=98.0, tp=106.0, expiry_index=created + 10,
                 invalidation=98.0, score=3)


def test_long_hits_tp():
    df = _df([(103, 104, 102, 103), (102, 102.5, 99.5, 101), (101, 107, 100.5, 106)])
    res = run_backtest(df, [_long()], SPEC, RULES)
    assert len(res.trades) == 1
    t = res.trades[0]
    assert t.exit_reason == "TP" and abs(t.r_multiple - 3.0) < 1e-6


def test_same_bar_sl_and_tp_counts_as_sl():
    df = _df([(103, 104, 102, 103), (102, 102.5, 99.5, 101), (101, 107, 97, 100)])
    res = run_backtest(df, [_long()], SPEC, RULES)
    assert res.trades[0].exit_reason == "SL"


def test_cancel_when_tp_reached_before_fill():
    df = _df([(103, 104, 102, 103), (103, 107, 102, 106), (106, 106, 99, 100)])
    res = run_backtest(df, [_long()], SPEC, RULES)
    assert res.trades == []


def test_no_fill_on_creation_bar():
    df = _df([(103, 104, 99, 103), (103, 104, 102, 103)])
    res = run_backtest(df, [_long()], SPEC, RULES)
    assert res.trades == []


def test_spread_applies_to_buy_fill():
    spec = SymbolSpec(spread=0.5, commission_per_lot=0.0)
    # bid low 99.6 -> ask low 100.1 > entry 100 -> tidak terisi
    df = _df([(103, 104, 102, 103), (101, 102, 99.6, 101), (101, 102, 100.5, 101)])
    assert run_backtest(df, [_long()], spec, RULES).trades == []
