"""Command line.

isgunu 2026                        holidays of a year
isgunu check 2026-03-19            is it a working day?
isgunu add 2026-03-18 5            5 working days later
isgunu between 2026-03-01 2026-04-01
isgunu deadline 2026-03-13 7       7 days later, moved past holidays
isgunu bridges 2026                köprü days
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from . import __version__
from .calendar import Calendar, to_date

_DAYS_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def _fmt(d: dt.date) -> str:
    return f"{d.isoformat()} {_DAYS_TR[d.weekday()]}"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="isgunu",
        description="Turkish public holidays and working-day arithmetic.",
    )
    p.add_argument("--version", action="version", version=f"isgunu {__version__}")
    p.add_argument("--saturday", action="store_true", help="count Saturdays as working days")
    p.add_argument(
        "--half-days",
        choices=["workday", "holiday", "half"],
        default="workday",
        help="how arife / 28 October afternoons count (default: workday)",
    )
    p.add_argument(
        "--off", action="append", default=[], metavar="DATE", help="extra day off (repeatable)"
    )
    p.add_argument("--estimated", action="store_true", help="allow estimated years after 2032")
    p.add_argument("--json", action="store_true", help="print JSON")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("list", help="holidays of a year").add_argument("year", type=int)
    sub.add_parser("check", help="is a date a working day").add_argument("date")
    a = sub.add_parser("add", help="add working days to a date")
    a.add_argument("date")
    a.add_argument("n", type=int)
    b = sub.add_parser("between", help="working days in [start, end)")
    b.add_argument("start")
    b.add_argument("end")
    d = sub.add_parser("deadline", help="add calendar days, roll to the next working day")
    d.add_argument("date")
    d.add_argument("days", type=int)
    sub.add_parser("bridges", help="köprü days of a year").add_argument("year", type=int)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # `isgunu 2026` is short for `isgunu list 2026`.
    commands = {"list", "check", "add", "between", "deadline", "bridges"}
    if argv and argv[-1].isdigit() and not commands.intersection(argv):
        argv.insert(len(argv) - 1, "list")
    parser = _build_parser()
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not args.cmd:
        parser.print_usage(sys.stderr)
        return 2

    try:
        cal = Calendar(
            saturday_is_workday=args.saturday,
            half_days=args.half_days,
            extra_holidays=args.off,
            allow_estimated=args.estimated,
        )
        result = _run(cal, args)
    except ValueError as e:
        print(f"isgunu: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.cmd == "list":
        for h in result:
            tag = " (13:00'ten)" if h["half"] else ""
            est = " ~tahmini" if h["estimated"] else ""
            print(f"{_fmt(to_date(h['date']))}  {h['name']}{tag}{est}")
    elif args.cmd == "check":
        h = result["holiday"]
        state = "iş günü" if result["business_day"] else "tatil"
        print(f"{_fmt(to_date(result['date']))}: {state}" + (f" ({h})" if h else ""))
    elif args.cmd == "between":
        print(result)
    elif args.cmd == "bridges":
        for day in result:
            print(_fmt(to_date(day)))
    else:
        print(_fmt(to_date(result)))
    return 0


def _run(cal: Calendar, args: argparse.Namespace):
    if args.cmd == "list":
        return [h.to_dict() for h in cal.holidays(args.year)]
    if args.cmd == "check":
        h = cal.holiday(args.date)
        return {
            "date": to_date(args.date).isoformat(),
            "business_day": cal.is_business_day(args.date),
            "holiday": h.name if h else None,
        }
    if args.cmd == "add":
        return cal.add_business_days(args.date, args.n).isoformat()
    if args.cmd == "between":
        return cal.business_days_between(args.start, args.end)
    if args.cmd == "deadline":
        return cal.deadline(args.date, args.days).isoformat()
    return [d.isoformat() for d in cal.bridge_days(args.year)]


if __name__ == "__main__":
    raise SystemExit(main())
