# @ardazeybek-dev/isgunu

[![CI](https://github.com/ardazeybek-dev/isgunu/actions/workflows/ci.yml/badge.svg)](https://github.com/ardazeybek-dev/isgunu/actions/workflows/ci.yml)
[![npm](https://img.shields.io/npm/v/@ardazeybek-dev/isgunu.svg)](https://www.npmjs.com/package/@ardazeybek-dev/isgunu)

Turkish public holidays and working-day arithmetic for JavaScript and
TypeScript. Bayram dates follow the Diyanet calendar, arife and 28 October
afternoons are known half days. No dependencies, ESM and CommonJS, works in
Node and the browser. Also on PyPI as [`isgunu`](https://pypi.org/project/isgunu/)
with the same table.

```bash
npm install @ardazeybek-dev/isgunu
```

```ts
import {
  isBusinessDay,
  addBusinessDays,
  businessDaysBetween,
  deadline,
  holiday,
  bridgeDays,
} from "@ardazeybek-dev/isgunu";

isBusinessDay("2026-03-20");                    // false - Ramazan Bayramı
addBusinessDays("2026-03-18", 2);               // "2026-03-23"
businessDaysBetween("2026-03-01", "2026-04-01"); // 21
deadline("2026-03-13", 7);                      // "2026-03-23"
holiday("2026-05-27")?.name;                    // "Kurban Bayramı 1. gün"
bridgeDays(2026);   // ["2026-01-02", "2026-04-24", "2026-05-18", "2026-10-30"]
isBusinessDay(new Date());                      // today, in Türkiye
```

## Your own rules

```ts
import { Calendar } from "@ardazeybek-dev/isgunu";

const cal = new Calendar({
  saturdayIsWorkday: true,          // six-day week
  halfDays: "half",                 // arife counts 0.5
  extraHolidays: ["2026-05-25"],    // idari izin, company holiday
});
cal.businessDaysBetween("2026-05-18", "2026-06-01"); // 5.5
```

| Option | Default | Meaning |
| --- | --- | --- |
| `saturdayIsWorkday` | `false` | count Saturdays as working days |
| `halfDays` | `"workday"` | arife afternoons: `"workday"`, `"holiday"` or `"half"` (0.5) |
| `extraHolidays` | `[]` | more days off, e.g. the yearly *idari izin* |
| `extraWorkdays` | `[]` | days worked although off, e.g. a make-up Saturday |
| `allowEstimated` | `false` | allow 2033-2050, where bayram dates are estimates |

## Dates

* Strings are read as written: `"2026-03-20"`, or the date part of
  `"2026-03-20T09:30:00+03:00"`. Results are `YYYY-MM-DD` strings.
* A `Date` is read as **the calendar day in Türkiye** (Europe/Istanbul), so
  `isBusinessDay(new Date())` on a UTC server answers for Türkiye. Pass strings
  when you mean a calendar date, not a moment.
* `businessDaysBetween(start, end)` counts `[start, end)`; negative when `end`
  is earlier.
* Years 2010-2032 are supported out of the box. Earlier or later years throw a
  `RangeError` instead of guessing.

Sources, the full holiday table and the Python package with a command line:
<https://github.com/ardazeybek-dev/isgunu>

MIT licence.
