from datetime import date

from dateutil.relativedelta import relativedelta


def generate_monthly_sales_tax_dates(
    anchor_due_date: date,
    occurrences: int,
) -> list[date]:
    return [
        anchor_due_date + relativedelta(months=occurrence)
        for occurrence in range(occurrences)
    ]


def generate_quarterly_sales_tax_dates(
    anchor_due_date: date,
    occurrences: int,
) -> list[date]:
    return [
        anchor_due_date + relativedelta(months=3 * occurrence)
        for occurrence in range(occurrences)
    ]