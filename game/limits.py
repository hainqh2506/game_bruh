"""Caps so a small host (laptop + tunnel, free VPS) does not keep unbounded state."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int, *, lo: int, hi: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(lo, min(hi, int(raw)))
    except ValueError:
        return default


def _env_float(name: str, default: float, *, lo: float, hi: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(lo, min(hi, float(raw)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Limits:
    max_rooms: int = 12
    max_players: int = 8
    max_party: int = 40
    max_solo: int = 40
    room_ttl: float = 45 * 60
    presence_ttl: float = 45.0

    @classmethod
    def from_env(cls) -> Limits:
        max_players = _env_int("DOANCHU_MAX_PLAYERS", 8, lo=2, hi=8)
        max_rooms = _env_int("DOANCHU_MAX_ROOMS", 12, lo=1, hi=200)
        return cls(
            max_rooms=max_rooms,
            max_players=max_players,
            max_party=_env_int("DOANCHU_MAX_PARTY", max_rooms * max_players, lo=2, hi=400),
            max_solo=_env_int("DOANCHU_MAX_SOLO", 40, lo=1, hi=500),
            room_ttl=_env_float("DOANCHU_ROOM_TTL", 45 * 60, lo=60, hi=24 * 3600),
            presence_ttl=_env_float("DOANCHU_SOLO_TTL", 45.0, lo=15, hi=300),
        )

    def public(self) -> dict[str, int]:
        return {
            "max_rooms": self.max_rooms,
            "max_players": self.max_players,
            "max_party": self.max_party,
            "max_solo": self.max_solo,
        }
