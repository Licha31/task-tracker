from datetime import date, timedelta

import holidays

US_HOLIDAYS = holidays.US()


def is_business_day(day: date) -> bool:
    is_weekend = day.weekday() >= 5
    is_holiday = day in US_HOLIDAYS

    return not is_weekend and not is_holiday


def previous_business_day(day: date) -> date:
    current_day = day - timedelta(days=1)

    while not is_business_day(current_day):
        current_day -= timedelta(days=1)

    return current_day


def subtract_business_days(day: date, days: int) -> date:
    current_day = day

    for _ in range(days):
        current_day = previous_business_day(current_day)

    return current_day

def business_days_between(start: date, end: date) -> int:
    current_day = start
    business_days = 0

    while current_day < end:
        current_day += timedelta(days=1)

        if is_business_day(current_day):
            business_days += 1

    return business_days