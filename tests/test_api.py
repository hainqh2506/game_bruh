from __future__ import annotations

from fastapi.testclient import TestClient

from game.room import HUB
from server.app import create_app


class _Reload:
    def wait_after(self, seen: int, timeout: float = 25.0) -> int:
        return seen


def _client() -> TestClient:
    app = create_app(reload=False, debug=False, reload_state=_Reload())
    return TestClient(app)


def test_create_join_rest_no_answer() -> None:
    with _client() as client:
        created = client.post("/api/rooms", json={"name": "Hải"}).json()
        assert created["room_id"]
        assert created["token"]
        assert "answer" not in created
        joined = client.post(
            f"/api/rooms/{created['room_id']}/join",
            json={"name": "Minh"},
        ).json()
        assert joined["room_id"] == created["room_id"]
        assert "answer" not in joined
        got = client.get(
            f"/api/rooms/{created['room_id']}",
            params={"token": created["token"]},
        ).json()
        assert "answer" not in got
        assert len(got["players"]) == 2
        HUB._rooms.pop(created["room_id"], None)


def test_config_exposes_limits() -> None:
    with _client() as client:
        cfg = client.get("/api/config").json()
        assert cfg["rooms"] is True
        assert cfg["limits"]["max_rooms"] >= 1
        assert cfg["limits"]["max_players"] >= 2
        assert "solo" in cfg["limits"]


def test_presence_caps_solo() -> None:
    from game.limits import Limits
    from server.presence import SoloPresence

    slot = SoloPresence(Limits(max_solo=1, presence_ttl=60))
    first = slot.touch(None)
    again = slot.touch(first["token"])
    assert again["token"] == first["token"]
    try:
        slot.touch(None)
        raise AssertionError("should fail")
    except ValueError:
        pass


def test_ws_room_payload_hides_answer() -> None:
    with _client() as client:
        created = client.post("/api/rooms", json={"name": "Hải"}).json()
        room_id = created["room_id"]
        with client.websocket_connect(f"/ws?room={room_id}&token={created['token']}") as ws:
            first = ws.receive_json()
            assert first["type"] == "room"
            assert "answer" not in first
            assert first["room_id"] == room_id
        HUB._rooms.pop(room_id, None)


def _drain_until(ws, typ: str, limit: int = 8) -> dict:
    last = {}
    for _ in range(limit):
        last = ws.receive_json()
        if last.get("type") == typ:
            return last
    raise AssertionError(f"no {typ} in last messages: {last}")


def test_ws_start_guess_peer_sees_status_only() -> None:
    with _client() as client:
        a = client.post("/api/rooms", json={"name": "Hải"}).json()
        b = client.post(f"/api/rooms/{a['room_id']}/join", json={"name": "Minh"}).json()
        with (
            client.websocket_connect(f"/ws?room={a['room_id']}&token={a['token']}") as ws_a,
            client.websocket_connect(f"/ws?room={b['room_id']}&token={b['token']}") as ws_b,
        ):
            _drain_until(ws_a, "room")
            _drain_until(ws_b, "room")
            ws_a.send_json({"type": "start"})
            started_a = _drain_until(ws_a, "started")
            started_b = _drain_until(ws_b, "started")
            assert "answer" not in started_a and "answer" not in started_b
            room = HUB.get(a["room_id"])
            assert room is not None
            ws_b.send_json({"type": "guess", "guess": room.answer})
            result = _drain_until(ws_b, "guess_result")
            assert result["won"] is True
            assert result["marks"]
            peer = _drain_until(ws_a, "peer_solved")
            assert "marks" not in peer
            assert "guess" not in peer
            assert peer["player"]["solved"] is True
            assert "answer" not in peer
            assert "solution" not in peer
        HUB._rooms.pop(a["room_id"], None)


def _wrong(answer: str) -> str:
    parts = answer.split()
    guess = ("z" * len(parts[0])) + " " + ("z" * len(parts[1]))
    if guess == answer:
        guess = ("y" * len(parts[0])) + " " + ("y" * len(parts[1]))
    return guess


def test_ws_lose_reconnect_sees_own_solution_only() -> None:
    with _client() as client:
        a = client.post("/api/rooms", json={"name": "Hải"}).json()
        b = client.post(f"/api/rooms/{a['room_id']}/join", json={"name": "Minh"}).json()
        room = HUB.get(a["room_id"])
        assert room is not None
        with (
            client.websocket_connect(f"/ws?room={a['room_id']}&token={a['token']}") as ws_a,
            client.websocket_connect(f"/ws?room={b['room_id']}&token={b['token']}") as ws_b,
        ):
            _drain_until(ws_a, "room")
            _drain_until(ws_b, "room")
            ws_a.send_json({"type": "start"})
            _drain_until(ws_a, "started")
            _drain_until(ws_b, "started")
            wrong = _wrong(room.answer)
            last = {}
            for _ in range(6):
                ws_a.send_json({"type": "guess", "guess": wrong})
                last = _drain_until(ws_a, "guess_result")
            assert last["won"] is False
            assert last["solution"] == room.answer
            peer = _drain_until(ws_b, "peer_update")
            assert "solution" not in peer
            assert "answer" not in peer
        with client.websocket_connect(f"/ws?room={a['room_id']}&token={a['token']}") as ws_a:
            snap = _drain_until(ws_a, "room")
            assert snap["solution"] == room.answer
            assert len(snap["board"]["guesses"]) == 6
        with client.websocket_connect(f"/ws?room={b['room_id']}&token={b['token']}") as ws_b:
            snap = _drain_until(ws_b, "room")
            assert "solution" not in snap
            assert snap["board"]["guesses"] == []
        late = client.post(f"/api/rooms/{a['room_id']}/join", json={"name": "Người lạ"})
        assert late.status_code >= 400
        assert "đang chạy" in late.json()["error"]
        HUB._rooms.pop(a["room_id"], None)


def test_rest_rejoin_after_both_lose() -> None:
    with _client() as client:
        a = client.post("/api/rooms", json={"name": "Hải"}).json()
        b = client.post(f"/api/rooms/{a['room_id']}/join", json={"name": "Minh"}).json()
        room = HUB.get(a["room_id"])
        assert room is not None
        host = room._player_by_token(a["token"])
        guest = room._player_by_token(b["token"])
        assert host is not None and guest is not None
        room.start(host)
        answer = room.answer
        wrong = _wrong(answer)
        for _ in range(6):
            room.submit_guess(host, wrong)
        for _ in range(6):
            room.submit_guess(guest, wrong)
        assert room.status == "finished"
        back = client.post(
            f"/api/rooms/{a['room_id']}/join",
            json={"name": "Hải", "token": a["token"]},
        ).json()
        assert back["status"] == "finished"
        assert back["solution"] == answer
        assert len(back["board"]["guesses"]) == 6
        got = client.get(f"/api/rooms/{a['room_id']}", params={"token": a["token"]}).json()
        assert got["solution"] == answer
        stranger = client.post(f"/api/rooms/{a['room_id']}/join", json={"name": "Khách"})
        assert stranger.status_code >= 400
        HUB._rooms.pop(a["room_id"], None)


def test_url_tamper_token_and_room_rejected() -> None:
    with _client() as client:
        a = client.post("/api/rooms", json={"name": "Hải"}).json()
        b = client.post(f"/api/rooms/{a['room_id']}/join", json={"name": "Minh"}).json()
        other = client.post("/api/rooms", json={"name": "Khác"}).json()
        stolen = client.post(
            f"/api/rooms/{a['room_id']}/join",
            json={"name": "Kẻ gian", "token": other["token"]},
        )
        assert stolen.status_code == 403
        junk = client.post(
            f"/api/rooms/{a['room_id']}/join",
            json={"name": "Kẻ gian", "token": "stolen-from-url"},
        )
        assert junk.status_code == 403
        no_token = client.get(f"/api/rooms/{a['room_id']}")
        assert no_token.status_code == 403
        wrong = client.get(
            f"/api/rooms/{a['room_id']}",
            params={"token": other["token"], "answer": "bố mẹ", "player": b["player_id"]},
        )
        assert wrong.status_code == 403
        lower = client.post(
            f"/api/rooms/{a['room_id'].lower()}/join",
            json={"name": "Minh", "token": b["token"]},
        )
        assert lower.status_code == 200
        assert lower.json()["player_id"] == b["player_id"]
        padded = client.post(f"/api/rooms/{a['room_id']}ZZ/join", json={"name": "X"})
        assert padded.status_code == 404
        try:
            with client.websocket_connect(
                f"/ws?room={a['room_id']}&token={other['token']}"
            ) as ws:
                ws.receive_json()
                raise AssertionError("foreign token must not open ws")
        except Exception as exc:
            code = getattr(exc, "code", None)
            assert code == 4401 or "4401" in str(exc)
        finally:
            HUB._rooms.pop(a["room_id"], None)
            HUB._rooms.pop(other["room_id"], None)
