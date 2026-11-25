from trade_pl.risk.position import SymbolSpec, position_size, risk_money


def test_position_size_xauusd():
    spec = SymbolSpec(spread=0.0, commission_per_lot=0.0)
    # equity 1000, risk 1% = $10, SL $5 -> 5*100 = $500/lot -> 0.02 lot
    assert position_size(1000, 1.0, 2650.0, 2645.0, spec) == 0.02


def test_position_size_includes_costs_and_never_exceeds_risk():
    spec = SymbolSpec(spread=0.3, commission_per_lot=7.0)
    lots = position_size(10_000, 1.0, 2650.0, 2647.0, spec)
    assert lots > 0
    assert risk_money(lots, 2650.0, 2647.0, spec) <= 100.0 + 1e-9


def test_position_size_zero_when_min_lot_too_risky():
    spec = SymbolSpec()
    assert position_size(100, 1.0, 2650.0, 2640.0, spec) == 0.0
