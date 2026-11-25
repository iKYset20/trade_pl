import pandas as pd

from trade_pl.analysis.sessions import session_mask
from trade_pl.data.csv_provider import load_csv


def test_load_mt5_export(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text(
        "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
        "2025.01.06\t08:00:00\t2650.1\t2651.0\t2649.5\t2650.8\t120\t0\t20\n"
        "2025.01.06\t08:05:00\t2650.8\t2652.0\t2650.2\t2651.6\t98\t0\t20\n"
    )
    df = load_csv(p)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index[1] == pd.Timestamp("2025-01-06 08:05") and df["volume"].iat[0] == 120


def test_session_mask_with_server_offset():
    idx = pd.DatetimeIndex(["2025-01-06 09:00", "2025-01-06 13:00"])  # waktu server GMT+2
    mask = session_mask(idx, {"london": ["07:00", "11:00"]}, server_utc_offset_hours=2)
    assert mask.tolist() == [True, False]  # 07:00 UTC & 11:00 UTC
