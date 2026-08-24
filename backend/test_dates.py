from datetime import date

from app.business_days import (
    is_business_day,
    previous_business_day,
    subtract_business_days,
)

print(
    "Monday:",
    is_business_day(date(2026, 8, 24)),
)

print(
    "Previous business day from Monday:",
    previous_business_day(date(2026, 8, 24)),
)

print(
    "Two business days before Monday:",
    subtract_business_days(date(2026, 8, 24), 2),
)