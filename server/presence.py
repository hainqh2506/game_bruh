"""Concurrent solo slots on this process (Pages/static hosts skip this)."""

from __future__ import annotations

import secrets
import threading
import time

from game.limits import Limits


class SoloPresence:
    def __init__(self, limits: Limits | None = None) -> None:
        self.limits = limits or Limits.from_env()
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def _sweep(self, now: float) -> None:
        cutoff = now - self.limits.presence_ttl
        dead = [token for token, ts in self._seen.items() if ts < cutoff]
        for token in dead:
            self._seen.pop(token, None)

    def touch(self, token: str | None) -> dict[str, int | str]:
        now = time.time()
        with self._lock:
            self._sweep(now)
            key = str(token or "").strip()
            if key and key in self._seen:
                self._seen[key] = now
            elif len(self._seen) >= self.limits.max_solo:
                raise ValueError(
                    f"Hết slot chơi đơn trên máy này ({self.limits.max_solo}). "
                    "Thử lại sau, hoặc mở bản Pages (không tốn slot server)."
                )
            else:
                key = key or secrets.token_urlsafe(12)
                self._seen[key] = now
            return {"token": key, **self.usage_unlocked()}

    def usage(self) -> dict[str, int]:
        with self._lock:
            self._sweep(time.time())
            return self.usage_unlocked()

    def usage_unlocked(self) -> dict[str, int]:
        return {"solo": len(self._seen), "max_solo": self.limits.max_solo}


SOLO = SoloPresence()
