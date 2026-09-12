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
from game.limits import Limits
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


def _clean_room_id(room_id: str | None) -> str:
    raw = str(room_id or "").strip()
    if any(ch in raw for ch in "./\\?&#"):
        return ""
    text = "".join(ch for ch in raw.upper() if ch.isalnum())
    return text if len(text) == 4 else ""


def _clean_token(token: str | None) -> str:
    return str(token or "").strip()


SCORE_BY_ATTEMPT = {
    1: 100,
    2: 50,
    3: 40,
    4: 30,
    5: 20,
    6: 10,
}


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
    total_score: int = 0
    round_score: int = 0
    total_time: float = 0.0
    round_time: float = 0.0
    last_reaction_at: float = 0.0

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "attempts": self.attempts,
            "solved": self.solved,
            "disconnected": self.disconnected,
            "total_score": self.total_score,
            "round_score": self.round_score,
            "total_time": round(self.total_time, 2),
            "round_time": round(self.round_time, 2),
            "marks": [list(m) for m in self.marks_list],
        }

    def own_board(self) -> dict[str, Any]:
        return {"guesses": list(self.guesses), "marksList": [list(m) for m in self.marks_list]}


ALLOWED_REACTIONS: set[str] = {"👏", "🔥", "🤣", "💀", "😱", "❤️"}


@dataclass
class RoomSession:
    id: str
    host_id: str
    settings: dict[str, Any]
    max_players: int = MAX_PLAYERS
    answer: str = ""
    status: str = "lobby"
    players: dict[str, Player] = field(default_factory=dict)
    started_at: float | None = None
    finished_at: float | None = None
    updated_at: float = field(default_factory=_now)
    total_rounds: int = 1
    current_round: int = 1
    time_limit: int = 0
    round_started_at: float | None = None

    def touch(self) -> None:
        self.updated_at = _now()

    def _player_by_token(self, token: str) -> Player | None:
        token = _clean_token(token)
        if not token:
            return None
        for player in self.players.values():
            if player.token == token:
                return player
        return None

    def roster(self) -> list[dict[str, Any]]:
        return [p.public() for p in self.players.values()]

    def ranking(self) -> list[dict[str, Any]]:
        def sort_key(p: Player):
            return (-p.total_score, p.total_time if p.total_score > 0 else 999999.0, p.attempts)

        ranked = sorted(self.players.values(), key=sort_key)
        out = []
        for i, player in enumerate(ranked, start=1):
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
            "max_players": self.max_players,
            "round": self.current_round,
            "total_rounds": self.total_rounds,
            "time_limit": self.time_limit,
        }
        if self.status in {"playing", "round_summary", "finished"} and self.answer:
            payload.update(puzzle_meta(self.answer))
            payload["started_at"] = int(self.round_started_at or self.started_at or 0)
        if self.status in {"round_summary", "finished"}:
            payload["ranking"] = self.ranking()
        if player:
            payload["you"] = player.public()
            payload["board"] = player.own_board()
            if self.answer and (
                player.solved
                or player.attempts >= MAX_ATTEMPTS
                or self.status in {"round_summary", "finished"}
            ):
                payload["solution"] = self.answer
        return payload

    def public_no_board(self) -> dict[str, Any]:
        return self.public(player=None)

    def _round_over(self) -> bool:
        if self.status != "playing":
            return False
        active = [p for p in self.players.values() if not p.disconnected]
        if not active:
            return False
        return all(p.solved or p.attempts >= MAX_ATTEMPTS for p in active)

    def start(self, player: Player) -> dict[str, Any]:
        if player.id != self.host_id:
            raise PermissionError("Chỉ chủ phòng được bắt đầu")
        if self.status == "playing":
            raise ValueError("Ván đang chạy")
        if len(self.players) < 2:
            raise ValueError("Cần ít nhất 2 người")
        self.touch()
        self.current_round = 1
        self.answer = pick_answer(self.settings)
        self.status = "playing"
        self.started_at = _now()
        self.round_started_at = self.started_at
        self.finished_at = None
        for p in self.players.values():
            p.attempts = 0
            p.solved = False
            p.solved_at = None
            p.guesses.clear()
            p.marks_list.clear()
            p.total_score = 0
            p.round_score = 0
            p.total_time = 0.0
            p.round_time = 0.0
        meta = puzzle_meta(self.answer)
        return {
            "type": Server.STARTED,
            "room_id": self.id,
            "round": self.current_round,
            "total_rounds": self.total_rounds,
            "time_limit": self.time_limit,
            "length": meta["length"],
            "spaceIndex": meta["spaceIndex"],
            "started_at": int(self.round_started_at or 0),
            "max_guesses": MAX_ATTEMPTS,
            "players": self.roster(),
        }

    def next_round(self, player: Player | None = None) -> dict[str, Any]:
        if player and player.id != self.host_id:
            raise PermissionError("Chỉ chủ phòng được chuyển câu")
        if self.status not in {"round_summary", "playing"}:
            raise ValueError("Ván chưa thể qua câu tiếp theo")
        if self.current_round >= self.total_rounds:
            raise ValueError("Đã là câu cuối cùng")
        self.touch()
        self.current_round += 1
        self.answer = pick_answer(self.settings)
        self.status = "playing"
        self.round_started_at = _now()
        for p in self.players.values():
            p.attempts = 0
            p.solved = False
            p.solved_at = None
            p.guesses.clear()
            p.marks_list.clear()
            p.round_score = 0
            p.round_time = 0.0
        meta = puzzle_meta(self.answer)
        return {
            "type": Server.STARTED,
            "room_id": self.id,
            "round": self.current_round,
            "total_rounds": self.total_rounds,
            "time_limit": self.time_limit,
            "length": meta["length"],
            "spaceIndex": meta["spaceIndex"],
            "started_at": int(self.round_started_at or 0),
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
        self.touch()
        marks = mark_guess(guess, self.answer)
        player.attempts += 1
        player.guesses.append(guess)
        player.marks_list.append(marks)
        won = guess == self.answer
        if won:
            player.solved = True
            player.solved_at = _now()
            start_ref = self.round_started_at or self.started_at or player.solved_at
            player.round_time = max(0.1, round(player.solved_at - start_ref, 2))
            player.total_time = round(player.total_time + player.round_time, 2)
            player.round_score = SCORE_BY_ATTEMPT.get(player.attempts, 10)
            player.total_score += player.round_score

        round_done = self._round_over()
        round_event = None
        finished_event = None
        if round_done:
            if self.current_round < self.total_rounds:
                self.status = "round_summary"
                self.finished_at = _now()
                round_event = {
                    "type": Server.ROUND_FINISHED,
                    "round": self.current_round,
                    "total_rounds": self.total_rounds,
                    "ranking": self.ranking(),
                    "players": self.roster(),
                    "solution": self.answer,
                }
            else:
                self.status = "finished"
                self.finished_at = _now()
                finished_event = {
                    "type": Server.FINISHED,
                    "round": self.current_round,
                    "total_rounds": self.total_rounds,
                    "ranking": self.ranking(),
                    "players": self.roster(),
                    "solution": self.answer,
                }

        result: dict[str, Any] = {
            "type": Server.GUESS_RESULT,
            "status": "success",
            "marks": marks,
            "won": won,
            "attempt": player.attempts,
            "max_guesses": MAX_ATTEMPTS,
            "round_score": player.round_score,
            "total_score": player.total_score,
        }
        if won or player.attempts >= MAX_ATTEMPTS:
            result["solution"] = self.answer
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
        return {
            "to_player": result,
            "broadcast": peer,
            "round_finished": round_event,
            "finished": finished_event,
        }


class RoomHub:
    def __init__(self, limits: Limits | None = None) -> None:
        self.limits = limits or Limits.from_env()
        self._rooms: dict[str, RoomSession] = {}
        self._lock = threading.RLock()

    def party_count(self) -> int:
        return sum(len(room.players) for room in self._rooms.values())

    def usage(self) -> dict[str, int]:
        with self._lock:
            return {
                **self.limits.public(),
                "rooms": len(self._rooms),
                "party": self.party_count(),
            }

    def _drop_idle_rooms(self) -> list[str]:
        now = _now()
        dead: list[str] = []
        for room_id, room in list(self._rooms.items()):
            connected = any(not p.disconnected for p in room.players.values())
            if connected:
                continue
            if now - room.updated_at >= self.limits.room_ttl:
                dead.append(room_id)
        for room_id in dead:
            self._rooms.pop(room_id, None)
        return dead

    def create(self, name: str, settings: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            self._drop_idle_rooms()
            if len(self._rooms) >= self.limits.max_rooms:
                raise ValueError(f"Hết slot phòng ({self.limits.max_rooms}). Thử lại sau.")
            if self.party_count() >= self.limits.max_party:
                raise ValueError(f"Máy chủ đông ({self.limits.max_party} người phòng). Thử lại sau.")
            room_id = _new_code()
            while room_id in self._rooms:
                room_id = _new_code()
            host = Player(id=_new_id(), name=_clean_name(name), token=secrets.token_urlsafe(16))
            cfg = normalize_settings(settings)
            room = RoomSession(
                id=room_id,
                host_id=host.id,
                settings=cfg,
                max_players=self.limits.max_players,
                total_rounds=cfg.get("rounds", 1),
                time_limit=cfg.get("time_limit", 0),
            )
            room.players[host.id] = host
            self._rooms[room_id] = room
            return self._auth_payload(room, host)

    def _room(self, room_id: str | None) -> RoomSession | None:
        key = _clean_room_id(room_id)
        if not key:
            return None
        return self._rooms.get(key)

    def join(self, room_id: str, name: str, token: str | None = None) -> dict[str, Any]:
        with self._lock:
            room = self._room(room_id)
            if not room:
                raise KeyError("Không có phòng này")
            token = _clean_token(token)
            if token:
                player = room._player_by_token(token)
                if not player:
                    raise PermissionError("Token không hợp lệ")
                player.disconnected = False
                player.last_seen = _now()
                room.touch()
                if name:
                    player.name = _clean_name(name)
                return self._auth_payload(room, player)
            clean_n = _clean_name(name)
            # Reconnect matching disconnected player if user lost token
            if clean_n and clean_n != "Khách":
                for p in room.players.values():
                    if p.disconnected and p.name.strip().lower() == clean_n.strip().lower():
                        p.disconnected = False
                        p.last_seen = _now()
                        room.touch()
                        return self._auth_payload(room, p)

            if room.status != "lobby":
                raise ValueError("Ván đang chạy. Chỉ vào lại được từ máy đã chơi.")
            if len(room.players) >= room.max_players:
                raise ValueError(f"Phòng đầy ({room.max_players} người)")
            if self.party_count() >= self.limits.max_party:
                raise ValueError(f"Máy chủ đông ({self.limits.max_party} người phòng). Thử lại sau.")
            player = Player(id=_new_id(), name=clean_n or "Khách", token=secrets.token_urlsafe(16))
            room.players[player.id] = player
            room.touch()
            return self._auth_payload(room, player)

    def get(self, room_id: str) -> RoomSession | None:
        with self._lock:
            return self._room(room_id)

    def player_for(self, room_id: str, token: str) -> tuple[RoomSession, Player]:
        with self._lock:
            room = self._room(room_id)
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
            room = self._room(room_id)
            if not room:
                return None
            player = room._player_by_token(token)
            if not player:
                return None
            player.disconnected = True
            return {"type": Server.PEER_UPDATE, "player": player.public(), "players": room.roster()}

    def sweep_stale(self) -> list[tuple[str, dict[str, Any]]]:
        events: list[tuple[str, dict[str, Any]]] = []
        now = _now()
        cutoff = now - HEARTBEAT_TIMEOUT
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
                # Check round time limit expiry
                if room.status == "playing" and room.time_limit > 0 and room.round_started_at:
                    if now - room.round_started_at >= room.time_limit:
                        for p in room.players.values():
                            if not p.solved and p.attempts < MAX_ATTEMPTS:
                                p.attempts = MAX_ATTEMPTS
                                p.round_score = 0
                                p.round_time = float(room.time_limit)
                        if room.current_round < room.total_rounds:
                            room.status = "round_summary"
                            room.finished_at = now
                            events.append(
                                (
                                    room.id,
                                    {
                                        "type": Server.ROUND_FINISHED,
                                        "round": room.current_round,
                                        "total_rounds": room.total_rounds,
                                        "ranking": room.ranking(),
                                        "players": room.roster(),
                                        "solution": room.answer,
                                    },
                                )
                            )
                        else:
                            room.status = "finished"
                            room.finished_at = now
                            events.append(
                                (
                                    room.id,
                                    {
                                        "type": Server.FINISHED,
                                        "round": room.current_round,
                                        "total_rounds": room.total_rounds,
                                        "ranking": room.ranking(),
                                        "players": room.roster(),
                                        "solution": room.answer,
                                    },
                                )
                            )
            self._drop_idle_rooms()
        return events

    def _auth_payload(self, room: RoomSession, player: Player) -> dict[str, Any]:
        payload = room.public(player)
        payload["player_id"] = player.id
        payload["token"] = player.token
        payload["name"] = player.name
        return payload


HUB = RoomHub()
