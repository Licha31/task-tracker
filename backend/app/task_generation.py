from datetime import date
import profile

from dateutil.relativedelta import relativedelta
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.payroll_schedule import (
    generate_biweekly_payroll_dates,
    generate_monthly_payroll_dates,
    generate_semi_monthly_payroll_dates,
    generate_weekly_payroll_dates,
)
from app.sales_tax_schedule import (
    generate_monthly_sales_tax_dates,
    generate_quarterly_sales_tax_dates,
)


def parse_date(value: date | str) -> date:
    if isinstance(value, date):
        return value

    return date.fromisoformat(value)

def months_between(start: date, end: date) -> int:
    return (
        (end.year - start.year) * 12
        + end.month
        - start.month
    )
    
def generate_payroll_tasks(
    db: Session,
    week_end: date,
) -> None:
    profiles = db.execute(
        text(
            """
            SELECT
                payroll_profiles.company_id,
                payroll_profiles.frequency,
                payroll_profiles.next_pay_date,
                payroll_profiles.next_process_date,
                payroll_profiles.semi_monthly_day_1,
                payroll_profiles.semi_monthly_day_2
            FROM payroll_profiles
            """
        )
    ).mappings().all()

    for profile in profiles:
        anchor_pay_date = parse_date(profile["next_pay_date"])
        anchor_process_date = parse_date(profile["next_process_date"])

        if anchor_process_date > week_end:
            continue

        frequency = profile["frequency"]

        if frequency == "weekly":
            occurrences = (
                (week_end - anchor_process_date).days // 7
            ) + 2

            dates = generate_weekly_payroll_dates(
                anchor_pay_date,
                anchor_process_date,
                occurrences,
            )

        elif frequency == "biweekly":
            occurrences = (
                (week_end - anchor_process_date).days // 14
            ) + 2

            dates = generate_biweekly_payroll_dates(
                anchor_pay_date,
                anchor_process_date,
                occurrences,
            )

        elif frequency == "monthly":
            occurrences = (
                months_between(anchor_pay_date, week_end)
                + 2
            )

            dates = generate_monthly_payroll_dates(
                anchor_pay_date,
                anchor_process_date,
                occurrences,
            )

        elif frequency == "semi_monthly":
            day_1 = profile["semi_monthly_day_1"]
            day_2 = profile["semi_monthly_day_2"]

            if day_1 is None or day_2 is None:
                continue

            occurrences = (
                months_between(anchor_pay_date, week_end) * 2
                + 4
            )

            dates = generate_semi_monthly_payroll_dates(
                start_date=anchor_pay_date,
                anchor_process_date=anchor_process_date,
                day_1=day_1,
                day_2=day_2,
                occurrences=occurrences,
            )

        else:
            continue

        for process_date, pay_date in dates:
            if process_date > week_end:
                continue

            db.execute(
                text(
                    """
                    INSERT OR IGNORE INTO tasks (
                        company_id,
                        task_type,
                        process_date,
                        pay_date,
                        status
                    )
                    VALUES (
                        :company_id,
                        'payroll',
                        :process_date,
                        :pay_date,
                        'pending'
                    )
                    """
                ),
                {
                    "company_id": profile["company_id"],
                    "process_date": process_date,
                    "pay_date": pay_date,
                },
            )
            
def generate_sales_tax_tasks(
    db: Session,
    week_end: date,
) -> None:
    profiles = db.execute(
        text(
            """
            SELECT
                company_id,
                frequency,
                next_due_date
            FROM sales_tax_profiles
            """
        )
    ).mappings().all()

    for profile in profiles:
        anchor_due_date = parse_date(profile["next_due_date"])

        if anchor_due_date > week_end:
            continue

        if profile["frequency"] == "monthly":
            occurrences = (
                months_between(anchor_due_date, week_end)
                + 2
            )

            dates = generate_monthly_sales_tax_dates(
                anchor_due_date,
                occurrences,
            )

        elif profile["frequency"] == "quarterly":
            months = months_between(
                anchor_due_date,
                week_end,
            )

            occurrences = (months // 3) + 2

            dates = generate_quarterly_sales_tax_dates(
                anchor_due_date,
                occurrences,
            )

        else:
            continue

        for due_date in dates:
            if due_date > week_end:
                continue

            db.execute(
                text(
                    """
                    INSERT OR IGNORE INTO tasks (
                        company_id,
                        task_type,
                        due_date,
                        status
                    )
                    VALUES (
                        :company_id,
                        'sales_tax',
                        :due_date,
                        'pending'
                    )
                    """
                ),
                {
                    "company_id": profile["company_id"],
                    "due_date": due_date,
                },
            )

def ensure_tasks_until(
    db: Session,
    week_end: date,
) -> None:
    generate_payroll_tasks(db, week_end)
    generate_sales_tax_tasks(db, week_end)

    db.commit()