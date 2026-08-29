from datetime import date

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import Task
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
    return (end.year - start.year) * 12 + end.month - start.month


def insert_task_if_missing(db: Session, values: dict[str, object]) -> None:
    dialect_name = db.get_bind().dialect.name
    if dialect_name == "sqlite":
        statement = sqlite_insert(Task).values(**values).on_conflict_do_nothing()
    elif dialect_name == "postgresql":
        statement = postgresql_insert(Task).values(**values).on_conflict_do_nothing()
    else:
        raise RuntimeError(f"Unsupported database dialect: {dialect_name}")
    db.execute(statement)


def generate_payroll_tasks(
    db: Session,
    week_end: date,
    payroll_schedule_id: int | None = None,
    process_date_after: date | None = None,
) -> None:
    schedule_filter = ""
    params: dict[str, object] = {}
    if payroll_schedule_id is not None:
        schedule_filter = " AND payroll_schedules.id = :payroll_schedule_id"
        params["payroll_schedule_id"] = payroll_schedule_id

    profiles = (
        db.execute(
            text(
                f"""
            SELECT
                payroll_schedules.id,
                payroll_schedules.company_id,
                payroll_schedules.frequency,
                payroll_schedules.next_pay_date,
                payroll_schedules.next_process_date,
                payroll_schedules.semi_monthly_day_1,
                payroll_schedules.semi_monthly_day_2
            FROM payroll_schedules
            WHERE payroll_schedules.active = TRUE
            {schedule_filter}
            """
            ),
            params,
        )
        .mappings()
        .all()
    )

    for profile in profiles:
        anchor_pay_date = parse_date(profile["next_pay_date"])
        anchor_process_date = parse_date(profile["next_process_date"])

        if anchor_process_date > week_end:
            continue

        frequency = profile["frequency"]

        if frequency == "weekly":
            occurrences = ((week_end - anchor_process_date).days // 7) + 2

            dates = generate_weekly_payroll_dates(
                anchor_pay_date,
                anchor_process_date,
                occurrences,
            )

        elif frequency == "biweekly":
            occurrences = ((week_end - anchor_process_date).days // 14) + 2

            dates = generate_biweekly_payroll_dates(
                anchor_pay_date,
                anchor_process_date,
                occurrences,
            )

        elif frequency == "monthly":
            occurrences = months_between(anchor_pay_date, week_end) + 2

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

            occurrences = months_between(anchor_pay_date, week_end) * 2 + 4

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
            if process_date_after is not None and process_date <= process_date_after:
                continue

            insert_task_if_missing(
                db,
                {
                    "company_id": profile["company_id"],
                    "payroll_schedule_id": profile["id"],
                    "task_type": "payroll",
                    "process_date": process_date,
                    "pay_date": pay_date,
                    "status": "pending",
                },
            )


def generate_sales_tax_tasks(
    db: Session,
    week_end: date,
) -> None:
    profiles = (
        db.execute(
            text(
                """
            SELECT
                id,
                company_id,
                frequency,
                next_due_date
            FROM sales_tax_registrations
            WHERE active = TRUE
            """
            )
        )
        .mappings()
        .all()
    )

    for profile in profiles:
        anchor_due_date = parse_date(profile["next_due_date"])

        if anchor_due_date > week_end:
            continue

        if profile["frequency"] == "monthly":
            occurrences = months_between(anchor_due_date, week_end) + 2

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

            insert_task_if_missing(
                db,
                {
                    "company_id": profile["company_id"],
                    "sales_tax_registration_id": profile["id"],
                    "task_type": "sales_tax",
                    "due_date": due_date,
                    "status": "pending",
                },
            )


def ensure_tasks_until(
    db: Session,
    week_end: date,
) -> None:
    generate_payroll_tasks(db, week_end)
    generate_sales_tax_tasks(db, week_end)

    db.commit()
