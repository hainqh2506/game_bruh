from __future__ import annotations

from game.limits import Limits
from game.room import RoomHub


def _room_two() -> tuple[RoomHub, dict, dict]:
    hub = RoomHub()
    a = hub.create("Hải", {"words": 2, "lengths": [None, None]})
    b = hub.join(a["room_id"], "Minh")
    return hub, a, b


def test_create_join_no_answer_leak() -> None:
    hub, a, b = _room_two()
    assert a["room_id"] == b["room_id"]
    assert "answer" not in a and "answer" not in b
    assert a["token"] != b["token"]
    room = hub.get(a["room_id"])
    assert room is not None
    pub = room.public_no_board()
    assert "answer" not in pub
    assert len(pub["players"]) == 2


def test_start_and_guess() -> None:
    hub, a, b = _room_two()
    room, host = hub.player_for(a["room_id"], a["token"])
    started = room.start(host)
    assert started["type"] == "started"
    assert "answer" not in started
    assert started["length"] == len(room.answer)
    assert started["spaceIndex"] == room.answer.find(" ")

    _, guest = hub.player_for(b["room_id"], b["token"])
    out = room.submit_guess(guest, room.answer)
    assert out["to_player"]["won"] is True
    assert out["broadcast"]["type"] == "peer_solved"
    assert "marks" not in out["broadcast"]
    assert "guess" not in out["broadcast"]
    pub = room.public_no_board()
    assert "answer" not in pub


def test_invalid_guess_rejected() -> None:
    hub, a, _b = _room_two()
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)
    try:
        room.submit_guess(host, "xxx")
        raise AssertionError("should fail")
    except ValueError as exc:
        assert "hợp lệ" in str(exc)


def test_max_rooms_and_party_caps() -> None:
    hub = RoomHub(Limits(max_rooms=1, max_players=2, max_party=2, room_ttl=3600))
    hub.create("A")
    try:
        hub.create("B")
        raise AssertionError("should fail")
    except ValueError as exc:
        assert "phòng" in str(exc).lower() or "slot" in str(exc).lower()


def test_max_players_per_room() -> None:
    hub = RoomHub(Limits(max_rooms=3, max_players=2, max_party=8, room_ttl=3600))
    a = hub.create("A")
    hub.join(a["room_id"], "B")
    try:
        hub.join(a["room_id"], "C")
        raise AssertionError("should fail")
    except ValueError as exc:
        assert "đầy" in str(exc)


def test_need_two_players() -> None:
    hub = RoomHub()
    a = hub.create("Solo")
    room, host = hub.player_for(a["room_id"], a["token"])
    try:
        room.start(host)
        raise AssertionError("should fail")
    except ValueError:
        pass


def test_reconnect_same_token() -> None:
    hub, a, _b = _room_two()
    again = hub.join(a["room_id"], "Hải mới", a["token"])
    assert again["player_id"] == a["player_id"]
    assert again["token"] == a["token"]
    room = hub.get(a["room_id"])
    assert room is not None
    assert len(room.players) == 2


def test_sweep_marks_stale_disconnected() -> None:
    hub, a, _b = _room_two()
    room = hub.get(a["room_id"])
    assert room is not None
    player = room._player_by_token(a["token"])
    assert player is not None
    player.last_seen = 0
    events = hub.sweep_stale()
    assert events
    assert player.disconnected
    assert events[0][1]["type"] == "peer_update"
    assert "answer" not in events[0][1]


def test_rematch_keeps_roster_new_answer() -> None:
    hub, a, b = _room_two()
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)
    first = room.answer
    _, guest = hub.player_for(b["room_id"], b["token"])
    room.submit_guess(host, first)
    room.submit_guess(guest, first)
    assert room.status == "finished"
    ids = set(room.players)
    room.rematch(host)
    assert room.status == "playing"
    assert set(room.players) == ids
    assert "answer" not in room.public_no_board()
    assert room.answer
    assert all(p.attempts == 0 and not p.solved for p in room.players.values())
