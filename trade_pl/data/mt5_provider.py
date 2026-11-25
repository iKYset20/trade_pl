"""Adapter MetaTrader 5.

Library `MetaTrader5` hanya berjalan di Windows dan butuh terminal MT5 yang
terpasang serta login. Kredensial dibaca dari environment variable:
MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH (opsional).
"""

from __future__ import annotations

import os

import pandas as pd

from .base import DataProvider, validate_ohlcv


class MT5Provider(DataProvider):
    def __init__(self) -> None:
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError as exc:  # pragma: no cover - tergantung OS
            raise RuntimeError(
                "Paket MetaTrader5 tidak tersedia. Jalankan di Windows: pip install MetaTrader5"
            ) from exc
        self.mt5 = mt5
        self._connected = False

    def connect(self) -> None:
        if self._connected:
            return
        kwargs = {}
        if os.getenv("MT5_PATH"):
            kwargs["path"] = os.environ["MT5_PATH"]
        if os.getenv("MT5_LOGIN"):
            kwargs.update(
                login=int(os.environ["MT5_LOGIN"]),
                password=os.getenv("MT5_PASSWORD", ""),
                server=os.getenv("MT5_SERVER", ""),
            )
        if not self.mt5.initialize(**kwargs):
            raise RuntimeError(f"Gagal inisialisasi MT5: {self.mt5.last_error()}")
        self._connected = True

    def shutdown(self) -> None:
        if self._connected:
            self.mt5.shutdown()
            self._connected = False

    def _tf(self, timeframe: str):
        name = f"TIMEFRAME_{timeframe.upper()}"
        if not hasattr(self.mt5, name):
            raise ValueError(f"Timeframe MT5 tidak dikenal: {timeframe}")
        return getattr(self.mt5, name)

    def get_ohlcv(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        self.connect()
        if not self.mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Simbol {symbol} tidak ditemukan di Market Watch")
        # start_pos=1 -> lewati bar yang sedang berjalan (belum close)
        rates = self.mt5.copy_rates_from_pos(symbol, self._tf(timeframe), 1, bars)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"Data kosong untuk {symbol} {timeframe}: {self.mt5.last_error()}")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time").rename(columns={"tick_volume": "volume"})
        return validate_ohlcv(df)

    def symbol_spec(self, symbol: str) -> dict:
        self.connect()
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"symbol_info gagal untuk {symbol}")
        return {
            "contract_size": info.trade_contract_size,
            "lot_step": info.volume_step,
            "min_lot": info.volume_min,
            "max_lot": info.volume_max,
            "spread": info.spread * info.point,
            "digits": info.digits,
        }
