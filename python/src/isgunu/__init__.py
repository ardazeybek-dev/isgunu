"""Turkish public holidays, arife half days and business-day arithmetic.

>>> import isgunu
>>> isgunu.is_business_day("2026-03-20")       # Ramazan Bayramı
False
>>> isgunu.add_business_days("2026-03-18", 2)
datetime.date(2026, 3, 23)
"""

from ._data import CONFIRMED_UNTIL, FIRST_YEAR, LAST_YEAR
from .calendar import (
    DEFAULT,
    Calendar,
    Holiday,
    add_business_days,
    bridge_days,
    business_days_between,
    deadline,
    holiday,
    holidays,
    is_business_day,
    is_holiday,
    next_business_day,
    previous_business_day,
    to_date,
)

__version__ = "0.1.0"

__all__ = [
    "CONFIRMED_UNTIL",
    "DEFAULT",
    "FIRST_YEAR",
    "LAST_YEAR",
    "Calendar",
    "Holiday",
    "add_business_days",
    "bridge_days",
    "business_days_between",
    "deadline",
    "holiday",
    "holidays",
    "is_business_day",
    "is_holiday",
    "next_business_day",
    "previous_business_day",
    "to_date",
]
