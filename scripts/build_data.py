"""Regenerate the holiday tables of both packages.

    pip install holidays==0.109
    python scripts/build_data.py

Writes ``python/src/isgunu/_data.py`` and ``js/src/data.ts`` from the same list,
so the Python and JavaScript packages can never disagree on a date.

Sources
-------
* Fixed-date holidays: Law 2429 (Ulusal Bayram ve Genel Tatiller Hakkında
  Kanun) as amended - 1 May since 2009, 15 July since 2017. Half days (arife,
  28 October) start at 13:00.
* Ramazan and Kurban Bayramı dates: the Diyanet calendar, taken from the
  ``holidays`` package (MIT), whose Turkish table is checked against Diyanet's
  Hijri-to-Gregorian converter up to ``CONFIRMED_UNTIL``. Later years are
  astronomical estimates and are flagged ``estimated``.

The fixed rules are written out here and the result is compared with the full
``holidays`` list, so a mistake in either side stops the build.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import holidays

FIRST_YEAR = 2010
CONFIRMED_UNTIL = 2032
LAST_YEAR = 2050

ROOT = Path(__file__).resolve().parent.parent
PY_OUT = ROOT / "python" / "src" / "isgunu" / "_data.py"
JS_OUT = ROOT / "js" / "src" / "data.ts"

# key, Turkish name, English name
FIXED = [
    ((1, 1), "yilbasi", "Yılbaşı", "New Year's Day"),
    (
        (4, 23),
        "ulusal_egemenlik",
        "Ulusal Egemenlik ve Çocuk Bayramı",
        "National Sovereignty and Children's Day",
    ),
    ((5, 1), "emek", "Emek ve Dayanışma Günü", "Labour and Solidarity Day"),
    (
        (5, 19),
        "genclik",
        "Atatürk'ü Anma, Gençlik ve Spor Bayramı",
        "Commemoration of Atatürk, Youth and Sports Day",
    ),
    ((7, 15), "demokrasi", "Demokrasi ve Millî Birlik Günü", "Democracy and National Unity Day"),
    ((8, 30), "zafer", "Zafer Bayramı", "Victory Day"),
    ((10, 29), "cumhuriyet", "Cumhuriyet Bayramı", "Republic Day"),
]


YEARS = range(FIRST_YEAR - 1, LAST_YEAR + 2)  # one spare year each side for bayrams


def bayram_starts(name: str) -> list[dt.date]:
    """First days of every Ramazan or Kurban Bayramı around the covered years.

    A Hijri year is about 11 days shorter than a Gregorian one, so a bayram can
    fall twice in one year (Ramazan Bayramı in January and December 2033) or
    run across New Year. Days are therefore grouped into runs over the whole
    range instead of being read year by year.
    """
    lib = holidays.Turkey(years=YEARS, categories=("public",), islamic_show_estimated=False)
    days = sorted(d for d, n in lib.items() if name in n.split("; "))
    day_set = set(days)
    return [d for d in days if d - dt.timedelta(days=1) not in day_set]


def build_entries() -> list[tuple]:
    out = []
    for year in YEARS:
        for (m, d), key, name, name_en in FIXED:
            if key == "demokrasi" and year < 2017:
                continue
            out.append((dt.date(year, m, d), key, name, name_en, False, False))
        out.append(
            (
                dt.date(year, 10, 28),
                "cumhuriyet_arifesi",
                "Cumhuriyet Bayramı arifesi",
                "Republic Day Eve",
                True,
                False,
            )
        )
    for key, name, name_en, length in (
        ("ramazan", "Ramazan Bayramı", "Eid al-Fitr", 3),
        ("kurban", "Kurban Bayramı", "Eid al-Adha", 4),
    ):
        for start in bayram_starts(name):
            est = start.year > CONFIRMED_UNTIL
            eve = start - dt.timedelta(days=1)
            out.append((eve, f"{key}_arifesi", f"{name} arifesi", f"{name_en} Eve", True, est))
            for i in range(length):
                day = start + dt.timedelta(days=i)
                out.append(
                    (
                        day,
                        f"{key}_{i + 1}",
                        f"{name} {i + 1}. gün",
                        f"{name_en}, day {i + 1}",
                        False,
                        est,
                    )
                )
    covered = [e for e in out if FIRST_YEAR <= e[0].year <= LAST_YEAR]

    # On a shared date: full days first, then the bayram, then the fixed holiday.
    def order(e: tuple) -> tuple:
        return (e[0], e[4], not e[1].startswith(("ramazan", "kurban")), e[1])

    return sorted(covered, key=order)


def check_against_library(entries: list[tuple]) -> None:
    def lib_days(category: str) -> set[dt.date]:
        lib = holidays.Turkey(years=YEARS, categories=(category,))
        return {d for d in lib if FIRST_YEAR <= d.year <= LAST_YEAR}

    for half, category in ((False, "public"), (True, "half_day")):
        ours = {e[0] for e in entries if e[4] is half}
        theirs = lib_days(category)
        assert ours == theirs, (category, sorted(ours ^ theirs))
    for name, length in (("Ramazan Bayramı", 3), ("Kurban Bayramı", 4)):
        lib = holidays.Turkey(years=YEARS, categories=("public",))
        days = {d for d, n in lib.items() if any(name in part for part in n.split("; "))}
        for start in bayram_starts(name):
            run = {start + dt.timedelta(days=i) for i in range(length)}
            assert run <= days and start + dt.timedelta(days=length) not in days, (name, start)


def main() -> None:
    entries = build_entries()
    check_against_library(entries)

    header = (
        f"Generated by scripts/build_data.py from holidays {holidays.__version__}. "
        "Do not edit by hand."
    )

    rows = "\n".join(
        f'    ("{e[0].isoformat()}", "{e[1]}", {json.dumps(e[2], ensure_ascii=False)}, '
        f"{json.dumps(e[3], ensure_ascii=False)}, {e[4]}, {e[5]}),"
        for e in entries
    )
    PY_OUT.write_text(
        f'"""{header}"""\n\n'
        f"FIRST_YEAR = {FIRST_YEAR}\n"
        f"CONFIRMED_UNTIL = {CONFIRMED_UNTIL}\n"
        f"LAST_YEAR = {LAST_YEAR}\n\n"
        "# (date, key, name, English name, half day, estimated)\n"
        f"HOLIDAYS = (\n{rows}\n)\n",
        encoding="utf-8",
        newline="\n",
    )

    js_rows = "\n".join(
        f'  ["{e[0].isoformat()}", "{e[1]}", {json.dumps(e[2], ensure_ascii=False)}, '
        f"{json.dumps(e[3], ensure_ascii=False)}, {str(e[4]).lower()}, {str(e[5]).lower()}],"
        for e in entries
    )
    JS_OUT.write_text(
        f"// {header}\n\n"
        f"export const FIRST_YEAR = {FIRST_YEAR};\n"
        f"export const CONFIRMED_UNTIL = {CONFIRMED_UNTIL};\n"
        f"export const LAST_YEAR = {LAST_YEAR};\n\n"
        "// [date, key, name, English name, half day, estimated]\n"
        "export const HOLIDAYS: ReadonlyArray<\n"
        "  readonly [string, string, string, string, boolean, boolean]\n"
        f"> = [\n{js_rows}\n];\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{len(entries)} entries, {FIRST_YEAR}-{LAST_YEAR} (confirmed until {CONFIRMED_UNTIL})")


if __name__ == "__main__":
    main()
