from calendar import monthrange
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from app.business_days import (
    business_days_between,
    is_business_day,
    previous_business_day,
    subtract_business_days,
)


def adjust_pay_date(pay_date: date) -> date:
    adjusted_date = pay_date

    while not is_business_day(adjusted_date):
        adjusted_date = previous_business_day(adjusted_date)

    return adjusted_date


def generate_weekly_payroll_dates(
    anchor_pay_date: date,
    anchor_process_date: date,
    occurrences: int,
) -> list[tuple[date, date]]:
    process_lead_days = business_days_between(
        anchor_process_date,
        anchor_pay_date,
    )

    payroll_dates = []

    for occurrence in range(occurrences):
        scheduled_pay_date = anchor_pay_date + timedelta(
            days=7 * occurrence,
        )

        pay_date = adjust_pay_date(scheduled_pay_date)

        process_date = subtract_business_days(
            pay_date,
            process_lead_days,
        )

        payroll_dates.append(
            (process_date, pay_date),
        )

    return payroll_dates

def generate_biweekly_payroll_dates(
    anchor_pay_date: date,
    anchor_process_date: date,
    occurrences: int,
) -> list[tuple[date, date]]:
    process_lead_days = business_days_between(
        anchor_process_date,
        anchor_pay_date,
    )

    payroll_dates = []

    for occurrence in range(occurrences):
        scheduled_pay_date = anchor_pay_date + timedelta(
            days=14 * occurrence,
        )

        pay_date = adjust_pay_date(scheduled_pay_date)

        process_date = subtract_business_days(
            pay_date,
            process_lead_days,
        )

        payroll_dates.append(
            (process_date, pay_date),
        )

    return payroll_dates

def generate_monthly_payroll_dates(
    anchor_pay_date: date,
    anchor_process_date: date,
    occurrences: int,
) -> list[tuple[date, date]]:
    process_lead_days = business_days_between(
        anchor_process_date,
        anchor_pay_date,
    )

    payroll_dates = []

    for occurrence in range(occurrences):
        scheduled_pay_date = anchor_pay_date + relativedelta(
            months=occurrence,
        )

        pay_date = adjust_pay_date(scheduled_pay_date)

        process_date = subtract_business_days(
            pay_date,
            process_lead_days,
        )

        payroll_dates.append(
            (process_date, pay_date),
        )

    return payroll_dates

def generate_semi_monthly_payroll_dates(
    start_date: date,
    anchor_process_date: date,
    day_1: int,
    day_2: int,
    occurrences: int,
) -> list[tuple[date, date]]:
    process_lead_days = business_days_between(
        anchor_process_date,
        start_date,
    )

    payroll_dates = []
    current_month = date(start_date.year, start_date.month, 1)

    while len(payroll_dates) < occurrences:
        year = current_month.year
        month = current_month.month
        last_day = monthrange(year, month)[1]

        for scheduled_day in (day_1, day_2):
            safe_day = min(scheduled_day, last_day)

            scheduled_pay_date = date(
                year,
                month,
                safe_day,
            )

            if scheduled_pay_date < start_date:
                continue

            pay_date = adjust_pay_date(scheduled_pay_date)

            process_date = subtract_business_days(
                pay_date,
                process_lead_days,
            )

            payroll_dates.append(
                (process_date, pay_date),
            )

            if len(payroll_dates) == occurrences:
                break

        current_month += relativedelta(months=1)

    return payroll_dates