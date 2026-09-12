from __future__ import annotations

from game.engine import decompose, is_playable, mark_guess, matches_settings, normalize_settings


def compact(marks: list[str | None]) -> str:
    code = {"green": "G", "yellow": "Y", "blue": "B", "grey": "X"}
    return "".join("·" if m is None else code.get(m, "?") for m in marks)


def assert_marks(guess: str, answer: str, expected: str) -> None:
    got = compact(mark_guess(guess, answer))
    assert got == expected, f"{guess!r} vs {answer!r}: {got} != {expected}"


def test_green_exact() -> None:
    assert_marks("cà phê", "cà phê", "GG·GGG")
    assert_marks("bánh mì", "bánh mì", "GGGG·GG")
    assert_marks("cá ba", "cá ba", "GG·GG")


def test_yellow_wrong_place() -> None:
    assert_marks("ba dc", "ab cd", "YY·YY")
    assert_marks("ba má", "má ba", "YY·YY")
    assert_marks("hac ba", "abc ha", "YYG·YG")


def test_blue_same_and_other_slot() -> None:
    assert_marks("cà ba", "cá ba", "GB·GG")
    assert_marks("xy cà", "cá xy", "YY·YB")
    assert_marks("hà xy", "ha xy", "GB·GG")


def test_grey_and_priority() -> None:
    assert_marks("cớ de", "cá ba", "GX·XX")
    assert_marks("cá ca", "cá ba", "GG·XG")
    assert_marks("cà ca", "cá ba", "GB·XG")


def test_vowel_bases_differ() -> None:
    assert_marks("cắ xy", "cá xy", "GX·GG")
    assert_marks("câ xy", "cá xy", "GX·GG")
    assert_marks("cê xy", "cé xy", "GX·GG")
    assert_marks("cô xy", "có xy", "GX·GG")
    assert_marks("cơ xy", "có xy", "GX·GG")
    assert_marks("cư xy", "cú xy", "GX·GG")
    assert_marks("cắ xy", "cằ xy", "GB·GG")
    assert_marks("cố xy", "cồ xy", "GB·GG")


def test_consonant_not_blue() -> None:
    assert_marks("đi xa", "đi xa", "GG·GG")
    assert_marks("di xa", "đi xa", "XG·GG")
    assert_marks("kó ba", "có ba", "XG·GG")


def test_space_is_null() -> None:
    marks = mark_guess("cà phê", "cà phê")
    assert marks[2] is None


def test_each_answer_letter_once() -> None:
    assert_marks("hà hà", "ha xy", "GB·XX")
    assert_marks("hà hà", "ha ha", "GB·GB")


def test_probe_nonsense() -> None:
    assert_marks("ae êôơ", "cà phê", "BX·YXX")
    assert_marks("àáạ ăâê", "abc def", "BXX·XXX")
    assert is_playable("ae êôơ", "cà phê")
    assert is_playable("àáạ ăâê", "abc def")
    assert not is_playable("àáạ ăâê", "cà phê")
    assert not is_playable("càphê", "cà phê")


def test_decompose() -> None:
    assert decompose("á") == {"b": "a", "t": "acute"}
    assert decompose("ắ") == {"b": "ă", "t": "acute"}
    assert decompose("đ") == {"b": "đ", "t": "none"}


def test_settings_filter() -> None:
    cfg = normalize_settings({"words": 2, "lengths": [2, 3]})
    assert matches_settings("cà phê", cfg)
    assert not matches_settings("học sinh", cfg)
