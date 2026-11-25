from trade_pl.core.config import load_config
from trade_pl.core.models import Direction
from trade_pl.data.synthetic import generate_ohlcv
from trade_pl.strategies.smc_ob import build_strategy


def _key(s):
    return (s.created_index, int(s.direction), s.entry, s.sl, s.tp)


def test_setups_are_valid_and_respect_rules():
    cfg = load_config()
    df = generate_ohlcv(20_000, seed=3)
    setups = build_strategy(cfg).generate_setups(df)
    assert setups, "harus ada setup di data sintetis"
    sc = cfg["strategy"]
    for s in setups:
        if s.direction is Direction.LONG:
            assert s.sl < s.entry < s.tp
        else:
            assert s.tp < s.entry < s.sl
        assert s.rr >= sc["min_rr"] - 0.01
        assert sc["min_sl"] - 0.01 <= s.risk <= sc["max_sl"] + 0.01
        assert s.score >= sc["min_score"]


def test_strategy_has_no_lookahead():
    """Setup yang dibuat sebelum bar k harus identik walau data setelah k tidak ada."""
    cfg = load_config()
    df = generate_ohlcv(12_000, seed=7)
    strat = build_strategy(cfg)
    k = 9_000
    full = {_key(s) for s in strat.generate_setups(df) if s.created_index < k}
    cut = {_key(s) for s in strat.generate_setups(df.iloc[:k])}
    assert full == cut
