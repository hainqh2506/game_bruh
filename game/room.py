"""In-memory rooms: create/join/start/guess. Answer never appears in public payloads."""

from __future__ import annotations

import secrets
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from game.engine import (
    MAX_ATTEMPTS,
    is_playable,
    mark_guess,
    normalize_settings,
    pick_answer,
    puzzle_meta,
)
from game.protocol import Server

MAX_PLAYERS = 8
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
HEARTBEAT_TIMEOUT = 45.0


def _now() -> float:
    return time.time()


def _new_code(n: int = 4) -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(n))


def _new_id() -> str:
    return secrets.token_hex(8)


def _clean_name(name: str | None) -> str:
    text = unicodedata.normalize("NFC", str(name or "")).strip()
    text = "".join(ch for ch in text if ch.isprintable())
    if not text:
        text = "Khách"
    return text[:20]


@dataclass
class Player:
    id: str
    name: str
    token: str
    attempts: int = 0
    solved: bool = False
    solved_at: float | None = None
    disconnected: bool = False
    guesses: list[str] = field(default_factory=list)
    marks_list: list[list[str | None]] = field(default_factory=list)
    last_seen: float = field(default_factory=_now)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "attempts": self.attempts,
            "solved": self.solved,
            "disconnected": self.disconnected,
        }

    def own_board(self) -> dict[str, Any]:
        return {"guesses": list(self.guesses), "marksList": [list(m) for m in self.marks_list]}


@dataclass
class RoomSession:
    id: str
    host_id: str
    settings: dict[str, Any]
    answer: str = ""
    status: str = "lobby"
    players: dict[str, Player] = field(default_factory=dict)
    started_at: float | None = None
    finished_at: float | None = None

    def _player_by_token(self, token: str) -> Player | None:
        for player in self.players.values():
            if player.token == token:
                return player
        return None

    def roster(self) -> list[dict[str, Any]]:
        return [p.public() for p in self.players.values()]

    def ranking(self) -> list[dict[str, Any]]:
        solved = [p for p in self.players.values() if p.solved and p.solved_at is not None]
        solved.sort(key=lambda p: p.solved_at or 0)
        out = []
        for i, player in enumerate(solved, start=1):
            row = player.public()
            row["rank"] = i
            out.append(row)
        return out

    def public(self, player: Player | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": Server.ROOM,
            "room_id": self.id,
            "status": self.status,
            "host_id": self.host_id,
            "settings": self.settings,
            "players": self.roster(),
            "max_guesses": MAX_ATTEMPTS,
            "max_players": MAX_PLAYERS,
        }
        if self.status in {"playing", "finished"} and self.answer:
            payload.update(puzzle_meta(self.answer))
            payload["started_at"] = int(self.started_at or 0)
        if self.status == "finished":
            payload["ranking"] = self.ranking()
        if player:
            payload["you"] = player.public()
            payload["board"] = player.own_board()
        return payload

    def public_no_board(self) -> dict[str, Any]:
        return self.public(player=None)

    def _maybe_finish(self) -> bool:
        if self.status != "playing":
            return False
        if any(p.solved for p in self.players.values()):
            if all(p.solved or p.attempts >= MAX_ATTEMPTS for p in self.players.values()):
                self.status = "finished"
                self.finished_at = _now()
                return True
        if all(p.attempts >= MAX_ATTEMPTS or p.solved for p in self.players.values()) and self.players:
            self.status = "finished"
            self.finished_at = _now()
            return True
        return False

    def start(self, player: Player) -> dict[str, Any]:
        if player.id != self.host_id:
            raise PermissionError("Chỉ chủ phòng được bắt đầu")
        if self.status == "playing":
            raise ValueError("Ván đang chạy")
        if len(self.players) < 2:
            raise ValueError("Cần ít nhất 2 người")
        self.answer = pick_answer(self.settings)
        self.status = "playing"
        self.started_at = _now()
        self.finished_at = None
        for p in self.players.values():
            p.attempts = 0
            p.solved = False
            p.solved_at = None
            p.guesses.clear()
            p.marks_list.clear()
        meta = puzzle_meta(self.answer)
        return {
            "type": Server.STARTED,
            "room_id": self.id,
            "length": meta["length"],
            "spaceIndex": meta["spaceIndex"],
            "started_at": int(self.started_at or 0),
            "max_guesses": MAX_ATTEMPTS,
            "players": self.roster(),
        }

    def rematch(self, player: Player) -> dict[str, Any]:
        if player.id != self.host_id:
            raise PermissionError("Chỉ chủ phòng được chơi lại")
        if self.status != "finished":
            raise ValueError("Ván chưa kết thúc")
        return self.start(player)

    def submit_guess(self, player: Player, guess: str) -> dict[str, Any]:
        if self.status != "playing":
            raise ValueError("Chưa bắt đầu")
        if player.solved:
            raise ValueError("Bạn đã đoán đúng")
        if player.attempts >= MAX_ATTEMPTS:
            raise ValueError("Hết lượt")
        guess = unicodedata.normalize("NFC", str(guess or "")).lower()
        if not is_playable(guess, self.answer):
            raise ValueError("Từ không hợp lệ.")
        marks = mark_guess(guess, self.answer)
        player.attempts += 1
        player.guesses.append(guess)
        player.marks_list.append(marks)
        won = guess == self.answer
        if won:
            player.solved = True
            player.solved_at = _now()
        finished = self._maybe_finish()
        # First solver also finishes the race for ranking display; others may continue
        # until they solve or exhaust. If someone solved, we still wait for others
        # unless we want instant finish — plan: first correct wins, others can continue.
        result: dict[str, Any] = {
            "type": Server.GUESS_RESULT,
            "status": "success",
            "marks": marks,
            "won": won,
            "attempt": player.attempts,
            "max_guesses": MAX_ATTEMPTS,
        }
        peer = {
            "type": Server.PEER_UPDATE,
            "player": player.public(),
            "players": self.roster(),
        }
        if won:
            peer["type"] = Server.PEER_SOLVED
            peer["rank"] = next(
                (i for i, row in enumerate(self.ranking(), start=1) if row["id"] == player.id),
                None,
            )
        finished_event = None
        if finished:
            finished_event = {
                "type": Server.FINISHED,
                "ranking": self.ranking(),
                "players": self.roster(),
            }
        return {"to_player": result, "broadcast": peer, "finished": finished_event}


class RoomHub:
    def __init__(self) -> None:
        self._rooms: dict[str, RoomSession] = {}
        self._lock = threading.RLock()

    def create(self, name: str, settings: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            room_id = _new_code()
            while room_id in self._rooms:
                room_id = _new_code()
            host = Player(id=_new_id(), name=_clean_name(name), token=secrets.token_urlsafe(16))
            room = RoomSession(
                id=room_id,
                host_id=host.id,
                settings=normalize_settings(settings),
            )
            room.players[host.id] = host
            self._rooms[room_id] = room
            return self._auth_payload(room, host)

    def join(self, room_id: str, name: str, token: str | None = None) -> dict[str, Any]:
        with self._lock:
            room = self._rooms.get(room_id.upper())
            if not room:
                raise KeyError("Không có phòng này")
            if token:
                player = room._player_by_token(token)
                if player:
                    player.disconnected = False
                    player.last_seen = _now()
                    if name:
                        player.name = _clean_name(name)
                    return self._auth_payload(room, player)
            if len(room.players) >= MAX_PLAYERS:
                raise ValueError("Phòng đầy")
            if room.status == "finished":
                raise ValueError("Ván đã kết thúc")
            player = Player(id=_new_id(), name=_clean_name(name), token=secrets.token_urlsafe(16))
            room.players[player.id] = player
            return self._auth_payload(room, player)

    def get(self, room_id: str) -> RoomSession | None:
        with self._lock:
            return self._rooms.get(room_id.upper())

    def player_for(self, room_id: str, token: str) -> tuple[RoomSession, Player]:
        with self._lock:
            room = self._rooms.get(room_id.upper())
            if not room:
                raise KeyError("Không có phòng này")
            player = room._player_by_token(token)
            if not player:
                raise PermissionError("Token không hợp lệ")
            player.last_seen = _now()
            player.disconnected = False
            return room, player

    def mark_disconnected(self, room_id: str, token: str) -> dict[str, Any] | None:
        with self._lock:
            room = self._rooms.get(room_id.upper())
            if not room:
                return None
            player = room._player_by_token(token)
            if not player:
                return None
            player.disconnected = True
            return {"type": Server.PEER_UPDATE, "player": player.public(), "players": room.roster()}

    def sweep_stale(self) -> list[tuple[str, dict[str, Any]]]:
        events: list[tuple[str, dict[str, Any]]] = []
        cutoff = _now() - HEARTBEAT_TIMEOUT
        with self._lock:
            for room in self._rooms.values():
                for player in room.players.values():
                    if not player.disconnected and player.last_seen < cutoff:
                        player.disconnected = True
                        events.append(
                            (
                                room.id,
                                {"type": Server.PEER_UPDATE, "player": player.public(), "players": room.roster()},
                            )
                        )
        return events

    def _auth_payload(self, room: RoomSession, player: Player) -> dict[str, Any]:
        payload = room.public(player)
        payload["player_id"] = player.id
        payload["token"] = player.token
        payload["name"] = player.name
        return payload


HUB = RoomHub()
