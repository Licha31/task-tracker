from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

TASKS_FOR_RANGE_SQL = text(
    """
    SELECT
        tasks.id,
        companies.name AS company_name,
        tasks.task_type,
        payroll_schedules.label AS source_label,
        COALESCE(
            payroll_schedules.jurisdiction,
            sales_tax_registrations.jurisdiction
        ) AS source_jurisdiction,
        tasks.process_date,
        tasks.pay_date,
        tasks.due_date,
        tasks.status
    FROM tasks
    JOIN companies ON tasks.company_id = companies.id
    LEFT JOIN payroll_schedules ON tasks.payroll_schedule_id = payroll_schedules.id
    LEFT JOIN sales_tax_registrations
        ON tasks.sales_tax_registration_id = sales_tax_registrations.id
    WHERE
        (tasks.task_type = 'payroll' AND tasks.process_date BETWEEN :range_start AND :range_end)
        OR
        (tasks.task_type = 'sales_tax' AND tasks.due_date BETWEEN :range_start AND :range_end)
    ORDER BY
        COALESCE(tasks.process_date, tasks.due_date),
        tasks.id
    """
)


def get_tasks_for_range(db: Session, range_start: date, range_end: date):
    """Return the task API's source-of-truth rows for an inclusive operational range."""
    return (
        db.execute(
            TASKS_FOR_RANGE_SQL,
            {"range_start": range_start, "range_end": range_end},
        )
        .mappings()
        .all()
    )
