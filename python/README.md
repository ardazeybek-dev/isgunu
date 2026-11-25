# isgunu

[![CI](https://github.com/ardazeybek-dev/isgunu/actions/workflows/ci.yml/badge.svg)](https://github.com/ardazeybek-dev/isgunu/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/isgunu.svg)](https://pypi.org/project/isgunu/)

Turkish public holidays and working-day arithmetic. Bayram dates follow the
Diyanet calendar, arife and 28 October afternoons are known half days, and
everything from "5 working days later" to "how many working days in March" is
one call. No dependencies, no network calls. Also on npm as
[`@ardazeybek-dev/isgunu`](https://www.npmjs.com/package/@ardazeybek-dev/isgunu)
with the same table.

```bash
pip install isgunu
```

```python
>>> import isgunu
>>> isgunu.is_business_day("2026-03-20")           # Ramazan Bayramı
False
>>> isgunu.add_business_days("2026-03-18", 2)      # Thu arife counts, Fri is bayram
datetime.date(2026, 3, 23)
>>> isgunu.business_days_between("2026-03-01", "2026-04-01")
21
>>> isgunu.deadline("2026-03-13", 7)               # 7 days, moved past the bayram
datetime.date(2026, 3, 23)
>>> isgunu.holiday("2026-05-27").name
'Kurban Bayramı 1. gün'
>>> [d.isoformat() for d in isgunu.bridge_days(2026)]   # köprü days
['2026-01-02', '2026-04-24', '2026-05-18', '2026-10-30']

```

## Your own rules

```python
>>> from isgunu import Calendar
>>> cal = Calendar(
...     saturday_is_workday=True,                  # six-day week
...     half_days="half",                          # arife counts 0.5
...     extra_holidays=["2026-05-25"],             # idari izin, company holiday
... )
>>> cal.business_days_between("2026-05-18", "2026-06-01")
5.5

```

| Option | Default | Meaning |
| --- | --- | --- |
| `saturday_is_workday` | `False` | count Saturdays as working days |
| `half_days` | `"workday"` | arife afternoons: `"workday"`, `"holiday"` or `"half"` (0.5) |
| `extra_holidays` | `()` | more days off, e.g. the yearly *idari izin* |
| `extra_workdays` | `()` | days worked although off, e.g. a make-up Saturday |
| `allow_estimated` | `False` | allow 2033-2050, where bayram dates are estimates |

The administrative leave the government adds around some bayrams (*idari
izin*) is decided every year and is not built in: pass it as `extra_holidays`.

## Command line

```console
$ isgunu 2026
2026-01-01 Perşembe  Yılbaşı
2026-03-19 Perşembe  Ramazan Bayramı arifesi (13:00'ten)
2026-03-20 Cuma  Ramazan Bayramı 1. gün
...
$ isgunu add 2026-03-18 5
2026-03-26 Perşembe
$ isgunu --half-days half between 2026-01-01 2027-01-01
249.5
$ isgunu check 2026-10-29
2026-10-29 Perşembe: tatil (Cumhuriyet Bayramı)
```

Also `deadline DATE DAYS`, `bridges YEAR`, `--saturday`, `--off DATE`, `--json`.

## Rules

* Dates accept `date`, `datetime` (its date part) or an ISO string.
* `business_days_between(start, end)` counts `[start, end)`, like numpy's
  `busday_count`; negative when `end` is earlier.
* `add_business_days(day, 0)` returns the day itself if it is a working day,
  otherwise the next one.
* `deadline(start, days)` adds calendar days and moves a weekend or holiday to
  the next working day. Check the rule that applies to your own case.
* Years 2010-2032 are supported out of the box. Earlier or later years raise
  `ValueError` instead of guessing.

Sources, the full holiday table and the JavaScript package:
<https://github.com/ardazeybek-dev/isgunu>

MIT licence.
