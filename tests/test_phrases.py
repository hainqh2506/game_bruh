from __future__ import annotations

import db
from game.phrases import parse_import_lines
from fastapi.testclient import TestClient

from server.app import create_app


class _Reload:
    def wait_after(self, seen: int, timeout: float = 25.0) -> int:
        return seen


def test_parse_import_lines() -> None:
    parsed = parse_import_lines(
        "# ghi chú\n"
        "học sinh\n"
        "Cà Phê\n"
        "học sinh\n"
        "bánh,mì\n"
        "xxx\n"
        "phrase\n"
    )
    assert parsed["valid"] == ["học sinh", "cà phê", "bánh mì"]
    assert "xxx" in parsed["invalid"]


def test_bulk_add_move_delete(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "words.sqlite")
    out = db.add_phrases(["học sinh", "cà phê"], pool="raw", source="import")
    assert out["added"] == ["học sinh", "cà phê"]
    again = db.add_phrases(["học sinh", "bánh mì"], pool="raw", source="import")
    assert again["existed"] == ["học sinh"]
    assert again["added"] == ["bánh mì"]
    moved = db.set_pools(["học sinh", "cà phê"], "play")
    assert set(moved["moved"]) == {"học sinh", "cà phê"}
    assert "học sinh" in db.all_phrases("play")
    assert "học sinh" in db.all_phrases("raw")
    gone = db.remove_phrases(["bánh mì"], "raw")
    assert gone["removed"] == ["bánh mì"]
    assert "bánh mì" not in db.all_phrases("raw")
    soft = db.discard_phrases(["học sinh"], "play")
    assert soft["soft"] is True
    assert "học sinh" in db.all_phrases("rejected")
    assert "học sinh" not in db.all_phrases("play")
    hard = db.discard_phrases(["học sinh"], "rejected")
    assert hard["removed"] == ["học sinh"]
    assert "học sinh" not in db.all_phrases("rejected")


def test_api_import_export_bulk(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "words.sqlite")
    monkeypatch.setattr(db, "export_artifacts", lambda: {"ok": True})
    app = create_app(reload=False, debug=True, reload_state=_Reload())
    with TestClient(app) as client:
        posted = client.post(
            "/api/phrases",
            json={"pool": "raw", "text": "học sinh\ncà phê\nxxx"},
        ).json()
        assert posted["added"] == ["học sinh", "cà phê"]
        assert posted["invalid"] == ["xxx"]
        moved = client.patch(
            "/api/phrases",
            json={"pool": "play", "phrases": ["học sinh", "cà phê"]},
        ).json()
        assert set(moved["moved"]) == {"học sinh", "cà phê"}
        exported = client.get("/api/phrases/export", params={"pool": "play"})
        assert exported.status_code == 200
        assert "học sinh" in exported.text
        assert "cà phê" in exported.text
        deleted = client.request(
            "DELETE",
            "/api/phrases",
            json={"pool": "play", "phrases": ["học sinh"]},
        ).json()
        assert deleted["soft"] is True
        assert deleted["discarded"] == ["học sinh"]
        assert "học sinh" not in client.get("/api/phrases/export", params={"pool": "play"}).text
        assert "học sinh" in client.get("/api/phrases/export", params={"pool": "rejected"}).text
        purged = client.request(
            "DELETE",
            "/api/phrases",
            json={"pool": "rejected", "phrases": ["học sinh"]},
        ).json()
        assert purged["soft"] is False
        assert purged["removed"] == ["học sinh"]
        assert "học sinh" not in client.get("/api/phrases/export", params={"pool": "rejected"}).text


def test_import_vdict(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "words.sqlite")
    words = tmp_path / "words.txt"
    words.write_text("học sinh\ncà phê\nxyz\nmột hai ba\nA-đam\n", encoding="utf-8")
    out = db.import_vdict(words)
    assert out["two_word"] == 2
    assert db.has_vdict("học sinh")
    assert "học sinh" in db.all_phrases("raw")
    assert "cà phê" in db.all_phrases("play")
    assert "một hai ba" not in db.all_phrases("raw")
    again = db.import_vdict(words)
    assert again["raw"] == 2
    assert again["play"] == 2


def test_drop_short_play(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "words.sqlite")
    db.add_phrases(["học sinh", "a ha", "ô tô"], pool="raw", source="test")
    db.add_phrases(["học sinh"], pool="play", source="test")
    db.set_pools(["a ha", "ô tô"], "play")
    out = db.drop_short_play()
    assert set(out["removed"]) == {"a ha", "ô tô"}
    assert db.all_phrases("play") == ["học sinh"]
    assert "a ha" in db.all_phrases("raw")
