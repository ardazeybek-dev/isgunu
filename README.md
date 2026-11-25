# isgunu

[![CI](https://github.com/ardazeybek-dev/isgunu/actions/workflows/ci.yml/badge.svg)](https://github.com/ardazeybek-dev/isgunu/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/isgunu.svg)](https://pypi.org/project/isgunu/)
[![npm](https://img.shields.io/npm/v/@ardazeybek-dev/isgunu.svg)](https://www.npmjs.com/package/@ardazeybek-dev/isgunu)

Turkish public holidays and working-day arithmetic, for Python and JavaScript.

Payroll, delivery estimates, invoice due dates, SLA timers and legal deadlines
all need the same answer: *is this a working day in Türkiye?* The fixed
holidays are easy. The hard parts are the ones generic holiday lists get wrong
or leave out:

* **Ramazan and Kurban Bayramı** move every year and follow the Diyanet
  calendar, not a generic Hijri calculation.
* **Arife** (the day before each bayram) and **28 October** are half days from
  13:00. Some teams work them, some do not, payroll counts them as half.
* Bayrams collide with fixed holidays (Ramazan Bayramı on 23 April 2023, Kurban
  Bayramı on 19 May 2027) and in 2033 Ramazan Bayramı falls twice in one year.
* Six-day weeks, *idari izin* (administrative leave) and make-up Saturdays.

`isgunu` handles all of these with one table shared by both packages, so
Python and JavaScript never disagree on a date.

```bash
pip install isgunu                    # Python 3.10+, with a command line
npm install @ardazeybek-dev/isgunu    # Node 18+ and browsers, ESM + CJS, typed
```

```python
>>> import isgunu
>>> isgunu.add_business_days("2026-03-18", 2)       # Thu arife counts, Fri is bayram
datetime.date(2026, 3, 23)
>>> isgunu.business_days_between("2026-01-01", "2027-01-01")
251
>>> isgunu.Calendar(half_days="half").business_days_between("2026-01-01", "2027-01-01")
249.5
```

```ts
import { addBusinessDays, Calendar } from "@ardazeybek-dev/isgunu";

addBusinessDays("2026-03-18", 2); // "2026-03-23"
new Calendar({ halfDays: "half" }).businessDaysBetween("2026-01-01", "2027-01-01"); // 249.5
```

```console
$ isgunu bridges 2026
2026-01-02 Cuma
2026-04-24 Cuma
2026-05-18 Pazartesi
2026-10-30 Cuma
```

Full guides: [Python](python/README.md) · [JavaScript](js/README.md)

## API

| Python | JavaScript | Returns |
| --- | --- | --- |
| `holidays(year)` | `holidays(year)` | every holiday day of the year, half days included |
| `holiday(day)` | `holiday(day)` | the holiday on that date, or `None` / `null` |
| `is_holiday(day)` | `isHoliday(day)` | full-day public holiday? |
| `is_business_day(day)` | `isBusinessDay(day)` | working day? |
| `next_business_day(day)` | `nextBusinessDay(day)` | first working day after |
| `previous_business_day(day)` | `previousBusinessDay(day)` | last working day before |
| `add_business_days(day, n)` | `addBusinessDays(day, n)` | `n` working days later (or earlier) |
| `business_days_between(a, b)` | `businessDaysBetween(a, b)` | working days in `[a, b)` |
| `deadline(day, days)` | `deadline(day, days)` | calendar days later, moved past days off |
| `bridge_days(year)` | `bridgeDays(year)` | köprü days: one working day between a holiday and a weekend |

Every function also exists on `Calendar(...)`, which takes the options:
Saturday as a working day, how arife afternoons count (`workday`, `holiday` or
`half`), extra days off, extra working days, and estimated years.

## The holiday table

| Date | Holiday | Since |
| --- | --- | --- |
| 1 January | Yılbaşı | |
| 23 April | Ulusal Egemenlik ve Çocuk Bayramı | |
| 1 May | Emek ve Dayanışma Günü | 2009 |
| 19 May | Atatürk'ü Anma, Gençlik ve Spor Bayramı | |
| 15 July | Demokrasi ve Millî Birlik Günü | 2017 |
| 30 August | Zafer Bayramı | |
| 28 October, from 13:00 | Cumhuriyet Bayramı arifesi | |
| 29 October | Cumhuriyet Bayramı | |
| arife from 13:00 + 3 days | Ramazan Bayramı | Diyanet calendar |
| arife from 13:00 + 4 days | Kurban Bayramı | Diyanet calendar |

**Years:** 2010-2032 by default. Bayram dates in these years are confirmed
against the Diyanet calendar. 2033-2050 are available with `allow_estimated` /
`allowEstimated`; their bayram dates are astronomical estimates and may be off
by a day. Any other year raises an error instead of guessing.

**Not included:** *idari izin*. The government announces it every year, so pass
it as `extra_holidays`, and pass the Saturdays worked in return as
`extra_workdays`.

### Sources

* Law 2429 on national holidays and general holidays, as amended: 1 May since
  2009, 15 July since 2017. Half days start at 13:00.
* Bayram dates come from the Diyanet calendar, through the Turkish table of the
  [`holidays`](https://github.com/vacanza/holidays) package (MIT), version 0.109.
* [`scripts/build_data.py`](scripts/build_data.py) writes the fixed rules
  out by itself and compares the result with the full `holidays` list, so a
  mistake on either side stops the build. CI regenerates both tables on every
  push and fails if they differ from the committed ones.

## Development

```
scripts/build_data.py    generates the two tables below
fixtures/cases.json      hand-checked cases run by both test suites
python/                  PyPI package isgunu (src/isgunu, tests)
js/                      npm package @ardazeybek-dev/isgunu (src, test)
```

```bash
# Python
cd python && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest && .venv/bin/ruff check . && .venv/bin/ruff format --check .

# JavaScript
cd js && npm ci && npm run typecheck && npm test && npm run build

# Holiday table
pip install holidays==0.109 && python scripts/build_data.py
```

No environment variables are needed. Bump the version in both
`python/src/isgunu/__init__.py` and `js/package.json`; a test checks that they
match. Publishing a GitHub release uploads the Python package to PyPI.

### Pitfalls

* Wrong day for a JS `Date` → `new Date("2026-03-20")` is a UTC moment → the
  package reads it in Istanbul time; pass `"YYYY-MM-DD"` strings when you mean
  a calendar date.
* A holiday row seems missing for a date → two holidays share it → `holiday()`
  returns one (full day, then bayram first); `holidays(year)` lists both.

## Related

Part of a small set of Türkiye developer tools:
[trkit](https://github.com/ardazeybek-dev/trkit) /
[trkit-js](https://github.com/ardazeybek-dev/trkit-js) (TCKN, VKN, IBAN, Turkish text) ·
[ekstre](https://github.com/ardazeybek-dev/ekstre) (bank statements) ·
[adres](https://github.com/ardazeybek-dev/adres) (address parsing).

MIT licence.
