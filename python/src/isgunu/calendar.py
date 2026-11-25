"""Turkish public holidays and business-day arithmetic."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from ._data import CONFIRMED_UNTIL, FIRST_YEAR, HOLIDAYS, LAST_YEAR

DateLike = dt.date | str
HalfDays = Literal["workday", "holiday", "half"]

_ONE = dt.timedelta(days=1)


@dataclass(frozen=True)
class Holiday:
    """One holiday day. ``half`` days (arife, 28 October) start at 13:00."""

    date: dt.date
    key: str
    name: str
    name_en: str
    half: bool
    estimated: bool

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "key": self.key,
            "name": self.name,
            "name_en": self.name_en,
            "half": self.half,
            "estimated": self.estimated,
        }


_BY_DATE: dict[dt.date, list[Holiday]] = {}
for _row in HOLIDAYS:
    _h = Holiday(dt.date.fromisoformat(_row[0]), *_row[1:])
    _BY_DATE.setdefault(_h.date, []).append(_h)
# Full days first, so the most important holiday of an overlapping date leads.
for _list in _BY_DATE.values():
    _list.sort(key=lambda h: h.half)


def to_date(value: DateLike) -> dt.date:
    """Accept a ``date``, a ``datetime`` (its date part) or an ISO ``YYYY-MM-DD`` string."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        return dt.date.fromisoformat(value.strip()[:10])
    raise TypeError(f"expected a date or 'YYYY-MM-DD' string, got {type(value).__name__}")


class Calendar:
    """A working calendar: Turkish public holidays plus your own rules.

    >>> cal = Calendar(saturday_is_workday=True)
    >>> cal.is_business_day("2026-03-07")      # a Saturday
    True

    Args:
        saturday_is_workday: count Saturdays as working days (six-day week).
        half_days: how arife and 28 October afternoons count. ``"workday"``
            (default) treats them as working days, ``"holiday"`` as days off,
            ``"half"`` as working days that count 0.5 in
            :meth:`business_days_between`.
        extra_holidays: more days off, such as the yearly administrative
            leave (idari izin) or a company holiday.
        extra_workdays: days that are worked although they would be off, such
            as a Saturday worked to make up for administrative leave.
        allow_estimated: allow years after the last year confirmed against the
            Diyanet calendar. Bayram dates there may be off by a day.
    """

    def __init__(
        self,
        *,
        saturday_is_workday: bool = False,
        half_days: HalfDays = "workday",
        extra_holidays: Iterable[DateLike] = (),
        extra_workdays: Iterable[DateLike] = (),
        allow_estimated: bool = False,
    ) -> None:
        if half_days not in ("workday", "holiday", "half"):
            raise ValueError("half_days must be 'workday', 'holiday' or 'half'")
        self.saturday_is_workday = saturday_is_workday
        self.half_days = half_days
        self.extra_holidays = frozenset(to_date(d) for d in extra_holidays)
        self.extra_workdays = frozenset(to_date(d) for d in extra_workdays)
        self.allow_estimated = allow_estimated
        self._last = LAST_YEAR if allow_estimated else CONFIRMED_UNTIL

    # -- holidays ---------------------------------------------------------

    def _check(self, d: dt.date) -> dt.date:
        if not FIRST_YEAR <= d.year <= self._last:
            hint = (
                f"; years {CONFIRMED_UNTIL + 1}-{LAST_YEAR} need allow_estimated=True"
                if not self.allow_estimated and d.year <= LAST_YEAR and d.year > CONFIRMED_UNTIL
                else ""
            )
            supported = f"{FIRST_YEAR}-{self._last}"
            raise ValueError(f"{d.year} is outside the supported years {supported}{hint}")
        return d

    def holidays(self, year: int) -> list[Holiday]:
        """Every holiday day of ``year`` in date order, half days included.

        >>> [h.name for h in holidays(2026)][:3]
        ['Yılbaşı', 'Ramazan Bayramı arifesi', 'Ramazan Bayramı 1. gün']
        """
        self._check(dt.date(year, 1, 1))
        return [h for d in sorted(_BY_DATE) if d.year == year for h in _BY_DATE[d]]

    def holiday(self, day: DateLike) -> Holiday | None:
        """The holiday on ``day``, or ``None``.

        When two fall on the same date, a full day wins over a half day and a
        bayram over a fixed holiday; :meth:`holidays` lists both.

        >>> holiday("2026-10-29").name
        'Cumhuriyet Bayramı'
        """
        found = _BY_DATE.get(self._check(to_date(day)))
        return found[0] if found else None

    def is_holiday(self, day: DateLike) -> bool:
        """True for a full-day public holiday (not arife afternoons).

        >>> is_holiday("2026-03-20"), is_holiday("2026-03-19")
        (True, False)
        """
        h = self.holiday(day)
        return h is not None and not h.half

    # -- business days ----------------------------------------------------

    def _weight(self, d: dt.date) -> float:
        """1 for a working day, 0 for a day off, 0.5 for a half day in 'half' mode."""
        self._check(d)
        if d in self.extra_workdays:
            return 1.0
        if d in self.extra_holidays:
            return 0.0
        if d.weekday() == 6 or (d.weekday() == 5 and not self.saturday_is_workday):
            return 0.0
        found = _BY_DATE.get(d)
        if not found:
            return 1.0
        if not found[0].half:
            return 0.0
        return {"workday": 1.0, "holiday": 0.0, "half": 0.5}[self.half_days]

    def is_business_day(self, day: DateLike) -> bool:
        """True when ``day`` is a working day.

        >>> is_business_day("2026-03-18"), is_business_day("2026-03-20")
        (True, False)
        """
        return self._weight(to_date(day)) > 0

    def next_business_day(self, day: DateLike) -> dt.date:
        """The first working day strictly after ``day``.

        >>> next_business_day("2026-03-19")         # bayram + weekend follow
        datetime.date(2026, 3, 23)
        """
        d = to_date(day) + _ONE
        while not self.is_business_day(d):
            d += _ONE
        return d

    def previous_business_day(self, day: DateLike) -> dt.date:
        """The last working day strictly before ``day``."""
        d = to_date(day) - _ONE
        while not self.is_business_day(d):
            d -= _ONE
        return d

    def add_business_days(self, day: DateLike, n: int) -> dt.date:
        """Move ``n`` working days from ``day``; negative ``n`` goes back.

        ``day`` itself is not counted. With ``n == 0`` the day is returned if
        it is a working day, otherwise the next working day.

        >>> add_business_days("2026-03-18", 2)      # Thu arife counts, Fri is bayram
        datetime.date(2026, 3, 23)
        """
        d = to_date(day)
        if n == 0:
            return d if self.is_business_day(d) else self.next_business_day(d)
        step = self.next_business_day if n > 0 else self.previous_business_day
        for _ in range(abs(n)):
            d = step(d)
        return d

    def business_days_between(self, start: DateLike, end: DateLike) -> float:
        """Working days in ``[start, end)``: start counted, end not.

        Negative when ``end`` is before ``start``. Returns a whole number unless
        ``half_days="half"``.

        >>> business_days_between("2026-03-01", "2026-04-01")
        21
        """
        a, b = to_date(start), to_date(end)
        sign = 1
        if b < a:
            a, b, sign = b, a, -1
        total = 0.0
        d = a
        while d < b:
            total += self._weight(d)
            d += _ONE
        return sign * (int(total) if total.is_integer() else total)

    def deadline(self, start: DateLike, days: int) -> dt.date:
        """``start`` plus ``days`` calendar days, moved to the next working day
        when it falls on a weekend or holiday.

        This is how most Turkish legal and contractual periods expressed in
        days end. Check the rule that applies to your case.

        >>> deadline("2026-03-12", 7)               # lands on Thu arife: a workday
        datetime.date(2026, 3, 19)
        >>> deadline("2026-03-13", 7)
        datetime.date(2026, 3, 23)
        """
        d = to_date(start) + dt.timedelta(days=days)
        return d if self.is_business_day(d) else self.next_business_day(d)

    def bridge_days(self, year: int) -> list[dt.date]:
        """Single working days stuck between a holiday and a weekend (köprü).

        Taking these off joins the holiday to the weekend.

        >>> [d.isoformat() for d in bridge_days(2026)]
        ['2026-01-02', '2026-04-24', '2026-05-18', '2026-10-30']
        """
        out = []
        d = dt.date(year, 1, 1)
        while d.year == year:
            prev, nxt = d - _ONE, d + _ONE
            if (
                self.is_business_day(d)
                and prev.year >= FIRST_YEAR
                and nxt.year <= self._last
                and not self.is_business_day(prev)
                and not self.is_business_day(nxt)
                and (self._is_off_holiday(prev) or self._is_off_holiday(nxt))
            ):
                out.append(d)
            d += _ONE
        return out

    def _is_off_holiday(self, d: dt.date) -> bool:
        # Only called for days that are already off, so an arife counts here
        # exactly when half_days='holiday'.
        return d in self.extra_holidays or self.holiday(d) is not None


DEFAULT = Calendar()

holidays = DEFAULT.holidays
holiday = DEFAULT.holiday
is_holiday = DEFAULT.is_holiday
is_business_day = DEFAULT.is_business_day
next_business_day = DEFAULT.next_business_day
previous_business_day = DEFAULT.previous_business_day
add_business_days = DEFAULT.add_business_days
business_days_between = DEFAULT.business_days_between
deadline = DEFAULT.deadline
bridge_days = DEFAULT.bridge_days
