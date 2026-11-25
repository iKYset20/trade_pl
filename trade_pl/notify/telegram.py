"""Notifikasi sinyal: format pesan + pengiriman Telegram."""

from __future__ import annotations

import logging
import os

import requests

from ..core.models import Direction, Setup

log = logging.getLogger(__name__)


def format_setup(s: Setup, symbol: str, lots: float | None = None, ltf: str = "", htf: str = "") -> str:
    side = "BUY LIMIT" if s.direction is Direction.LONG else "SELL LIMIT"
    lines = [
        f"{'🟢' if s.direction is Direction.LONG else '🔴'} {symbol} {side} ({ltf}/{htf})",
        f"Waktu setup : {s.created_time:%Y-%m-%d %H:%M} (server)",
        f"Entry       : {s.entry:.2f}",
        f"Stop Loss   : {s.sl:.2f}  ({s.risk:.2f})",
        f"Take Profit : {s.tp:.2f}  (R:R 1:{s.rr:.1f})",
        f"Zona OB     : {s.zone_low:.2f} - {s.zone_high:.2f}",
        f"Skor        : {s.score}/4",
        "Confluence  : " + ", ".join(s.reasons),
    ]
    if lots is not None:
        lines.append(f"Lot saran   : {lots:.2f}")
    lines.append(f"Kedaluwarsa : setelah {s.expiry_index - s.created_index} bar")
    return "\n".join(lines)


class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> bool:
        if not self.enabled:
            return False
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text},
                timeout=10,
            )
            r.raise_for_status()
            return True
        except requests.RequestException as exc:
            log.warning("Gagal kirim Telegram: %s", exc)
            return False
