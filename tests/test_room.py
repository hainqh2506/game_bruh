from __future__ import annotations

import pytest

from game.limits import Limits
from game.room import RoomHub


def _room_two() -> tuple[RoomHub, dict, dict]:
    hub = RoomHub()
    a = hub.create("Hải", {"words": 2, "lengths": [None, None]})
    b = hub.join(a["room_id"], "Minh")
    return hub, a, b


def _wrong(answer: str) -> str:
    parts = answer.split()
    guess = ("z" * len(parts[0])) + " " + ("z" * len(parts[1]))
    if guess == answer:
        guess = ("y" * len(parts[0])) + " " + ("y" * len(parts[1]))
    return guess


def _lose(room, player) -> dict:
    last = None
    wrong = _wrong(room.answer)
    for _ in range(6):
        last = room.submit_guess(player, wrong)
    assert last is not None
    return last


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
    assert out["to_player"]["solution"] == room.answer
    assert out["broadcast"]["type"] == "peer_solved"
    assert "marks" not in out["broadcast"]
    assert "guess" not in out["broadcast"]
    assert "solution" not in out["broadcast"]
    pub = room.public_no_board()
    assert "answer" not in pub
    assert "solution" not in pub
    assert room.public(guest)["solution"] == room.answer
    assert "solution" not in room.public(host)


def test_lose_sends_solution_only_to_player() -> None:
    hub, a, b = _room_two()
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)
    last = _lose(room, host)
    assert last["to_player"]["won"] is False
    assert last["to_player"]["solution"] == room.answer
    assert "solution" not in last["broadcast"]
    assert room.public(host)["solution"] == room.answer
    assert last["finished"] is None
    _, guest = hub.player_for(b["room_id"], b["token"])
    assert "solution" not in room.public(guest)


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
    last = room.submit_guess(guest, first)
    assert room.status == "finished"
    assert last["finished"]["solution"] == first
    assert room.public(host)["solution"] == first
    assert room.public(guest)["solution"] == first
    assert "solution" not in room.public_no_board()
    ids = set(room.players)
    room.rematch(host)
    assert room.status == "playing"
    assert set(room.players) == ids
    assert "answer" not in room.public_no_board()
    assert "solution" not in room.public(host)
    assert "solution" not in room.public(guest)
    assert room.answer
    assert all(p.attempts == 0 and not p.solved for p in room.players.values())


def test_lose_reconnect_same_token_keeps_board_and_answer() -> None:
    hub, a, b = _room_two()
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)
    _lose(room, host)
    hub.mark_disconnected(a["room_id"], a["token"])
    again = hub.join(a["room_id"], "Hải", a["token"])
    assert again["player_id"] == a["player_id"]
    assert again["solution"] == room.answer
    assert len(again["board"]["guesses"]) == 6
    assert again["you"]["solved"] is False
    assert again["you"]["attempts"] == 6
    assert again["you"]["disconnected"] is False
    _, guest = hub.player_for(b["room_id"], b["token"])
    assert "solution" not in room.public(guest)


def test_lose_leave_without_token_cannot_rejoin_as_new_player() -> None:
    hub, a, _b = _room_two()
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)
    _lose(room, host)
    with pytest.raises(ValueError, match="đang chạy"):
        hub.join(a["room_id"], "Hải khác")


def test_cannot_guess_after_lose_or_win() -> None:
    hub, a, b = _room_two()
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)
    _, guest = hub.player_for(b["room_id"], b["token"])
    room.submit_guess(guest, room.answer)
    with pytest.raises(ValueError, match="đoán đúng"):
        room.submit_guess(guest, room.answer)
    assert room.status == "playing"
    _lose(room, host)
    assert room.status == "finished"
    with pytest.raises(ValueError, match="Chưa bắt đầu"):
        room.submit_guess(host, _wrong(room.answer))

    hub2, c, d = _room_two()
    room2, host2 = hub2.player_for(c["room_id"], c["token"])
    room2.start(host2)
    _lose(room2, host2)
    with pytest.raises(ValueError, match="Hết lượt"):
        room2.submit_guess(host2, _wrong(room2.answer))
    assert room2.status == "playing"


def test_both_lose_then_reconnect_and_rematch() -> None:
    hub, a, b = _room_two()
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)
    first = room.answer
    _, guest = hub.player_for(b["room_id"], b["token"])
    _lose(room, host)
    last = _lose(room, guest)
    assert room.status == "finished"
    assert last["finished"]["solution"] == first
    back = hub.join(a["room_id"], "Hải", a["token"])
    assert back["status"] == "finished"
    assert back["solution"] == first
    assert len(back["board"]["guesses"]) == 6
    with pytest.raises(ValueError, match="kết thúc|đang chạy"):
        hub.join(a["room_id"], "Người lạ")
    with pytest.raises(PermissionError):
        room.rematch(guest)
    room.rematch(host)
    assert room.status == "playing"
    assert room.answer
    assert "solution" not in room.public(host)
    assert all(p.attempts == 0 for p in room.players.values())


def test_midgame_reconnect_has_board_but_no_solution() -> None:
    hub, a, _b = _room_two()
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)
    room.submit_guess(host, _wrong(room.answer))
    hub.mark_disconnected(a["room_id"], a["token"])
    again = hub.join(a["room_id"], "Hải", a["token"])
    assert "solution" not in again
    assert len(again["board"]["guesses"]) == 1
    assert again["you"]["attempts"] == 1


def test_room_code_from_messy_url_still_matches() -> None:
    hub, a, b = _room_two()
    rid = a["room_id"]
    again = hub.join(rid.lower(), "Minh", b["token"])
    assert again["player_id"] == b["player_id"]
    dashed = rid[:2] + "-" + rid[2:]
    again = hub.join(dashed, "Minh", b["token"])
    assert again["player_id"] == b["player_id"]
    with pytest.raises(KeyError):
        hub.join(rid + "ZZ", "X")
    with pytest.raises(KeyError):
        hub.join("../" + rid, "X")
    with pytest.raises(KeyError):
        hub.join("", "X")


def test_wrong_or_foreign_token_does_not_create_seat() -> None:
    hub, a, b = _room_two()
    other = hub.create("Khác")
    with pytest.raises(PermissionError, match="Token"):
        hub.join(a["room_id"], "Kẻ gian", "not-a-real-token")
    with pytest.raises(PermissionError, match="Token"):
        hub.join(a["room_id"], "Kẻ gian", other["token"])
    with pytest.raises(PermissionError):
        hub.player_for(a["room_id"], "")
    with pytest.raises(PermissionError):
        hub.player_for(a["room_id"], b["token"] + "x")
    assert len(hub.get(a["room_id"]).players) == 2
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)
    with pytest.raises(PermissionError, match="Token"):
        hub.join(a["room_id"], "Người lạ", "stolen")
    with pytest.raises(ValueError, match="đang chạy"):
        hub.join(a["room_id"], "Người lạ")


def test_rematch_before_finished_rejected() -> None:
    hub, a, b = _room_two()
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)
    _, guest = hub.player_for(b["room_id"], b["token"])
    room.submit_guess(guest, room.answer)
    assert room.status == "playing"
    with pytest.raises(ValueError, match="kết thúc"):
        room.rematch(host)


def test_multi_round_scoring_and_transitions() -> None:
    hub = RoomHub()
    a = hub.create("Host", {"words": 2, "lengths": [None, None], "rounds": 2, "time_limit": 120})
    b = hub.join(a["room_id"], "Guest")
    room, host = hub.player_for(a["room_id"], a["token"])
    _, guest = hub.player_for(b["room_id"], b["token"])

    assert room.total_rounds == 2
    assert room.time_limit == 120

    # Start match
    started = room.start(host)
    assert started["round"] == 1
    assert started["total_rounds"] == 2
    assert started["time_limit"] == 120

    # Round 1: Host solves on attempt 1 (100 pts), Guest solves on attempt 2 (50 pts)
    r1_ans = room.answer
    out_host = room.submit_guess(host, r1_ans)
    assert out_host["to_player"]["won"] is True
    assert host.round_score == 100
    assert host.total_score == 100
    assert room.status == "playing"  # Guest hasn't finished yet

    # Guest guesses wrong once, then right
    room.submit_guess(guest, _wrong(r1_ans))
    out_guest = room.submit_guess(guest, r1_ans)
    assert guest.round_score == 50
    assert guest.total_score == 50

    # Round 1 completes -> round_summary
    assert room.status == "round_summary"
    assert out_guest["round_finished"] is not None
    assert out_guest["round_finished"]["round"] == 1
    assert out_guest["finished"] is None

    # Host triggers next round
    next_started = room.next_round(host)
    assert next_started["round"] == 2
    assert room.status == "playing"
    assert room.current_round == 2
    assert host.total_score == 100
    assert guest.total_score == 50
    assert host.attempts == 0
    assert guest.attempts == 0

    # Round 2: Guest solves on attempt 1 (100 pts -> 150 total), Host fails 6 times (0 pts -> 100 total)
    r2_ans = room.answer
    room.submit_guess(guest, r2_ans)
    assert guest.round_score == 100
    assert guest.total_score == 150

    last = _lose(room, host)
    assert host.round_score == 0
    assert host.total_score == 100

    # Match finishes
    assert room.status == "finished"
    assert last["finished"] is not None
    assert last["finished"]["round"] == 2
    ranking = room.ranking()
    assert ranking[0]["id"] == guest.id
    assert ranking[0]["total_score"] == 150
    assert ranking[1]["id"] == host.id
    assert ranking[1]["total_score"] == 100


def test_tie_breaker_lower_time_wins() -> None:
    hub = RoomHub()
    a = hub.create("Player1", {"rounds": 1})
    b = hub.join(a["room_id"], "Player2")
    room, p1 = hub.player_for(a["room_id"], a["token"])
    _, p2 = hub.player_for(b["room_id"], b["token"])
    room.start(p1)

    p1.total_score = 50
    p1.total_time = 25.5

    p2.total_score = 50
    p2.total_time = 14.2  # Solved faster

    ranks = room.ranking()
    assert ranks[0]["id"] == p2.id
    assert ranks[1]["id"] == p1.id


def test_sweep_stale_round_time_limit() -> None:
    hub = RoomHub()
    a = hub.create("Host", {"rounds": 2, "time_limit": 60})
    b = hub.join(a["room_id"], "Guest")
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)

    # Fast forward round_started_at to 65 seconds ago
    room.round_started_at = room.round_started_at - 65
    events = hub.sweep_stale()
    assert any(ev[1]["type"] == "round_finished" for ev in events)
    assert room.status == "round_summary"
    assert all(p.attempts == 6 for p in room.players.values())


def test_reconnect_disconnected_player_without_token() -> None:
    hub = RoomHub()
    a = hub.create("Host", {"rounds": 2})
    b = hub.join(a["room_id"], "Guest1")
    room, host = hub.player_for(a["room_id"], a["token"])
    room.start(host)

    # Guest1 disconnects
    hub.mark_disconnected(a["room_id"], b["token"])
    assert room.players[b["player_id"]].disconnected is True

    # Guest1 re-opens tab in new incognito window (token lost)
    rejoin = hub.join(a["room_id"], "Guest1", token="")
    assert rejoin["player_id"] == b["player_id"]
    assert room.players[b["player_id"]].disconnected is False


