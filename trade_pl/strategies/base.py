"""Interface strategi. Strategi menerima data LTF yang sudah close dan
mengembalikan daftar Setup. Setup di indeks t WAJIB hanya memakai data <= t,
sehingga kode yang sama dipakai untuk backtest dan live scanner."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from ..core.models import Setup


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def generate_setups(self, ltf: pd.DataFrame) -> list[Setup]:
        ...
