"""CLI trade_pl.

Contoh:
  python -m trade_pl backtest --source synthetic
  python -m trade_pl backtest --source csv --csv data/XAUUSD_M5.csv
  python -m trade_pl backtest --source mt5 --bars 50000
  python -m trade_pl fetch --bars 100000 --out data/XAUUSD_M5.csv
  python -m trade_pl scan            # live alert (MT5)
  python -m trade_pl scan --once
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .backtest.engine import RiskRules, run_backtest
from .backtest.metrics import format_metrics
from .core.config import load_config, load_dotenv
from .core.timeframes import tf_minutes
from .risk.position import SymbolSpec
from .strategies.smc_ob import build_strategy


def _load_data(args, cfg):
    ltf = cfg["timeframes"]["ltf"]
    if args.source == "synthetic":
        from .data.synthetic import generate_ohlcv
        return generate_ohlcv(bars=args.bars or 30_000, timeframe_minutes=tf_minutes(ltf), seed=args.seed)
    if args.source == "csv":
        from .data.csv_provider import load_csv
        if not args.csv:
            raise SystemExit("--csv wajib untuk source csv")
        df = load_csv(args.csv)
        return df.tail(args.bars) if args.bars else df
    from .data.mt5_provider import MT5Provider
    return MT5Provider().get_ohlcv(cfg["symbol"]["name"], ltf, args.bars or 50_000)


def cmd_backtest(args, cfg) -> None:
    df = _load_data(args, cfg)
    strategy = build_strategy(cfg)
    setups = strategy.generate_setups(df)
    result = run_backtest(df, setups, SymbolSpec.from_config(cfg), RiskRules.from_config(cfg))
    print(f"\nBacktest {cfg['symbol']['name']} {cfg['timeframes']['ltf']}/{cfg['timeframes']['htf']} "
          f"| {df.index[0]} -> {df.index[-1]} | {len(df)} bar | sumber: {args.source}")
    if args.source == "synthetic":
        print("  (DATA SINTETIS - hanya uji pipeline, bukan penilaian strategi)")
    print(f"  Setup terdeteksi : {len(setups)}")
    print(format_metrics(result.metrics))
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        result.trades_frame().to_csv(out / "trades.csv", index=False)
        result.equity_curve.to_csv(out / "equity.csv")
        print(f"\nHasil disimpan di {out}/trades.csv dan {out}/equity.csv")


def cmd_fetch(args, cfg) -> None:
    from .data.mt5_provider import MT5Provider
    tf = args.timeframe or cfg["timeframes"]["ltf"]
    df = MT5Provider().get_ohlcv(cfg["symbol"]["name"], tf, args.bars)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index_label="time")
    print(f"{len(df)} bar {tf} disimpan ke {args.out}")


def cmd_scan(args, cfg) -> None:
    from .data.mt5_provider import MT5Provider
    from .scanner import Scanner
    scanner = Scanner(MT5Provider(), build_strategy(cfg), cfg, equity=args.equity)
    if args.once:
        found = scanner.scan_once(include_active=True)
        if not found:
            print("Tidak ada setup aktif saat ini.")
    else:
        scanner.run()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="trade_pl", description="Asisten analisis XAUUSD (SMC)")
    parser.add_argument("--config", default=None, help="path settings.yaml")
    sub = parser.add_subparsers(dest="cmd", required=True)

    bt = sub.add_parser("backtest", help="uji strategi di data historis")
    bt.add_argument("--source", choices=["synthetic", "csv", "mt5"], default="synthetic")
    bt.add_argument("--csv")
    bt.add_argument("--bars", type=int, default=0)
    bt.add_argument("--seed", type=int, default=42)
    bt.add_argument("--out", help="folder output trades.csv & equity.csv")

    fe = sub.add_parser("fetch", help="unduh data historis dari MT5 ke CSV")
    fe.add_argument("--bars", type=int, default=100_000)
    fe.add_argument("--timeframe")
    fe.add_argument("--out", default="data/XAUUSD_M5.csv")

    sc = sub.add_parser("scan", help="live scanner + alert")
    sc.add_argument("--once", action="store_true")
    sc.add_argument("--equity", type=float, default=None, help="equity untuk saran lot")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    cfg = load_config(args.config)
    {"backtest": cmd_backtest, "fetch": cmd_fetch, "scan": cmd_scan}[args.cmd](args, cfg)


if __name__ == "__main__":
    main()
