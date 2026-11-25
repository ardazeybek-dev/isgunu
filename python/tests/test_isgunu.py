import datetime as dt
import json
from pathlib import Path

import pytest

import isgunu
from isgunu import Calendar
from isgunu.cli import main

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "cases.json"


def D(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


# -- official dates, written out by hand from the Diyanet calendar -----------

BAYRAMS = {
    # year: (Ramazan Bayramı day 1, Kurban Bayramı day 1)
    2023: ("2023-04-21", "2023-06-28"),
    2024: ("2024-04-10", "2024-06-16"),
    2025: ("2025-03-30", "2025-06-06"),
    2026: ("2026-03-20", "2026-05-27"),
    2027: ("2027-03-09", "2027-05-16"),
}


@pytest.mark.parametrize("year", sorted(BAYRAMS))
def test_bayram_dates_and_lengths(year):
    ramazan, kurban = (D(s) for s in BAYRAMS[year])
    for start, key, days in ((ramazan, "ramazan", 3), (kurban, "kurban", 4)):
        eve = isgunu.holiday(start - dt.timedelta(days=1))
        assert eve.key == f"{key}_arifesi" and eve.half
        for i in range(days):
            h = isgunu.holiday(start + dt.timedelta(days=i))
            assert h.key == f"{key}_{i + 1}" and not h.half
        after = isgunu.holiday(start + dt.timedelta(days=days))
        assert after is None or not after.key.startswith(key)


def test_fixed_holidays_2026():
    names = {h.date.isoformat(): h.name for h in isgunu.holidays(2026) if not h.half}
    assert names["2026-01-01"] == "Yılbaşı"
    assert names["2026-04-23"] == "Ulusal Egemenlik ve Çocuk Bayramı"
    assert names["2026-05-01"] == "Emek ve Dayanışma Günü"
    assert names["2026-05-19"] == "Atatürk'ü Anma, Gençlik ve Spor Bayramı"
    assert names["2026-07-15"] == "Demokrasi ve Millî Birlik Günü"
    assert names["2026-08-30"] == "Zafer Bayramı"
    assert names["2026-10-29"] == "Cumhuriyet Bayramı"


def test_fifteen_july_starts_2017():
    assert isgunu.holiday("2016-07-15") is None
    assert isgunu.holiday("2017-07-15").key == "demokrasi"


def test_half_days_are_the_three_eves():
    half = [h for h in isgunu.holidays(2026) if h.half]
    assert [(h.date.isoformat(), h.key) for h in half] == [
        ("2026-03-19", "ramazan_arifesi"),
        ("2026-05-26", "kurban_arifesi"),
        ("2026-10-28", "cumhuriyet_arifesi"),
    ]


def test_confirmed_years_are_not_estimated():
    for year in range(isgunu.FIRST_YEAR, isgunu.CONFIRMED_UNTIL + 1):
        assert not any(h.estimated for h in isgunu.holidays(year))
    cal = Calendar(allow_estimated=True)
    assert all(h.estimated for h in cal.holidays(2040) if h.key.startswith(("ramazan", "kurban")))


# -- shared fixtures (also run by the JavaScript tests) -----------------------

CASES = json.loads(FIXTURES.read_text(encoding="utf-8")) if FIXTURES.exists() else {}
needs_fixtures = pytest.mark.skipif(not CASES, reason="fixtures/ is outside the sdist")


def cal(case) -> Calendar:
    return Calendar(**case.get("options", {}))


def cases(name):
    return CASES.get(name, [])


@needs_fixtures
@pytest.mark.parametrize("case", cases("is_business_day"))
def test_fixture_is_business_day(case):
    assert cal(case).is_business_day(case["date"]) is case["expect"]


@needs_fixtures
@pytest.mark.parametrize("case", cases("holiday_key"))
def test_fixture_holiday_key(case):
    h = cal(case).holiday(case["date"])
    assert (h.key if h else None) == case["expect"]


@needs_fixtures
@pytest.mark.parametrize("case", cases("add_business_days"))
def test_fixture_add_business_days(case):
    got = cal(case).add_business_days(case["date"], case["n"])
    assert got.isoformat() == case["expect"]


@needs_fixtures
@pytest.mark.parametrize("case", cases("business_days_between"))
def test_fixture_business_days_between(case):
    assert cal(case).business_days_between(case["start"], case["end"]) == case["expect"]


@needs_fixtures
@pytest.mark.parametrize("case", cases("deadline"))
def test_fixture_deadline(case):
    assert cal(case).deadline(case["date"], case["days"]).isoformat() == case["expect"]


@needs_fixtures
@pytest.mark.parametrize("case", cases("bridge_days"))
def test_fixture_bridge_days(case):
    got = [d.isoformat() for d in cal(case).bridge_days(case["year"])]
    assert got == case["expect"]


@needs_fixtures
@pytest.mark.parametrize("case", cases("holiday_count"))
def test_fixture_holiday_count(case):
    assert len(cal(case).holidays(case["year"])) == case["expect"]


@needs_fixtures
@pytest.mark.parametrize("case", cases("out_of_range"))
def test_fixture_out_of_range(case):
    with pytest.raises(ValueError):
        cal(case).is_business_day(case["date"])


# -- inputs and API details ---------------------------------------------------


def test_accepts_datetime_and_string():
    assert isgunu.is_business_day(dt.datetime(2026, 3, 20, 9, 30)) is False
    assert isgunu.is_business_day("2026-03-20T09:30:00+03:00") is False
    with pytest.raises(TypeError):
        isgunu.is_business_day(20260320)


def test_estimated_year_error_mentions_the_option():
    with pytest.raises(ValueError, match="allow_estimated"):
        isgunu.holidays(2040)


def test_invalid_half_days():
    with pytest.raises(ValueError):
        Calendar(half_days="sometimes")


def test_versions_match_js():
    pkg = Path(__file__).resolve().parents[2] / "js" / "package.json"
    if not pkg.exists():
        pytest.skip("js/ is outside the sdist")
    assert json.loads(pkg.read_text(encoding="utf-8"))["version"] == isgunu.__version__


# -- command line -------------------------------------------------------------


def test_cli_year_shortcut(capsys):
    assert main(["2026"]) == 0
    out = capsys.readouterr().out
    assert "2026-03-20 Cuma  Ramazan Bayramı 1. gün" in out
    assert "2026-10-28 Çarşamba  Cumhuriyet Bayramı arifesi (13:00'ten)" in out


def test_cli_commands(capsys):
    assert main(["add", "2026-03-18", "2"]) == 0
    assert main(["deadline", "2026-03-13", "7"]) == 0
    assert main(["between", "2026-03-01", "2026-04-01"]) == 0
    assert main(["check", "2026-03-20"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "2026-03-23 Pazartesi",
        "2026-03-23 Pazartesi",
        "21",
        "2026-03-20 Cuma: tatil (Ramazan Bayramı 1. gün)",
    ]


def test_cli_json_and_errors(capsys):
    assert main(["--json", "bridges", "2026"]) == 0
    assert json.loads(capsys.readouterr().out)[0] == "2026-01-02"
    assert main(["2040"]) == 1
    assert "allow_estimated" in capsys.readouterr().err
