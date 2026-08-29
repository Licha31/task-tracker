from datetime import date

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app import models  # noqa: F401 - registers tables on Base.metadata
from app.database import Base
from app.payroll_schedule import generate_biweekly_payroll_dates
from app.routes import reconcile_payroll_schedules
from app.schemas import PayrollScheduleInput
from app.task_generation import generate_payroll_tasks


def test_biweekly_recurrence_uses_fourteen_day_scheduled_intervals():
    dates = generate_biweekly_payroll_dates(
        anchor_pay_date=date(2026, 8, 28),
        anchor_process_date=date(2026, 8, 26),
        occurrences=3,
    )

    assert dates == [
        (date(2026, 8, 26), date(2026, 8, 28)),
        (date(2026, 9, 9), date(2026, 9, 11)),
        (date(2026, 9, 23), date(2026, 9, 25)),
    ]


def test_biweekly_pay_date_adjusts_for_weekends_and_holidays_with_same_lead_time():
    weekend_dates = generate_biweekly_payroll_dates(
        anchor_pay_date=date(2026, 8, 29),
        anchor_process_date=date(2026, 8, 26),
        occurrences=2,
    )
    holiday_dates = generate_biweekly_payroll_dates(
        anchor_pay_date=date(2026, 12, 11),
        anchor_process_date=date(2026, 12, 9),
        occurrences=2,
    )

    assert weekend_dates == [
        (date(2026, 8, 26), date(2026, 8, 28)),
        (date(2026, 9, 9), date(2026, 9, 11)),
    ]
    assert holiday_dates == [
        (date(2026, 12, 9), date(2026, 12, 11)),
        (date(2026, 12, 22), date(2026, 12, 24)),
    ]


def test_editing_biweekly_schedule_reconciles_only_pending_future_tasks(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'biweekly-edit.db'}")
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    today = date(2026, 8, 29)

    with test_session.begin() as db:
        company_id = db.execute(
            text("INSERT INTO companies (name, ein) VALUES ('AFZAL VETERINARY', '10-0000001')")
        ).lastrowid
        schedule_id = db.execute(
            text(
                """
                INSERT INTO payroll_schedules (
                    company_id, label, jurisdiction, frequency, payroll_platform,
                    next_pay_date, next_process_date, active
                ) VALUES (
                    :company_id, 'Primary Payroll', 'FL', 'biweekly', 'Gusto',
                    '2026-09-11', '2026-09-04', TRUE
                )
                """
            ),
            {"company_id": company_id},
        ).lastrowid
        other_schedule_id = db.execute(
            text(
                """
                INSERT INTO payroll_schedules (
                    company_id, label, jurisdiction, frequency, payroll_platform,
                    next_pay_date, next_process_date, active
                ) VALUES (
                    :company_id, 'Owner Payroll', 'FL', 'weekly', 'Gusto',
                    '2026-09-04', '2026-09-01', TRUE
                )
                """
            ),
            {"company_id": company_id},
        ).lastrowid
        generate_payroll_tasks(db, date(2026, 10, 15))
        db.execute(
            text(
                """
                INSERT INTO tasks (
                    company_id, payroll_schedule_id, task_type,
                    process_date, pay_date, status
                ) VALUES
                    (:company_id, :schedule_id, 'payroll', '2026-08-28', '2026-08-31', 'completed'),
                    (:company_id, :schedule_id, 'payroll', '2026-08-29', '2026-09-01', 'pending')
                """
            ),
            {"company_id": company_id, "schedule_id": schedule_id},
        )
        progressed_task_id = db.execute(
            text(
                """
                UPDATE tasks
                SET status = 'in_progress'
                WHERE payroll_schedule_id = :schedule_id
                  AND process_date = '2026-09-21'
                RETURNING id
                """
            ),
            {"schedule_id": schedule_id},
        ).scalar_one()

    with test_session.begin() as db:
        other_tasks_before = db.execute(
            text(
                """
                SELECT id, process_date, pay_date, status
                FROM tasks
                WHERE payroll_schedule_id = :schedule_id
                ORDER BY id
                """
            ),
            {"schedule_id": other_schedule_id},
        ).all()
        reconcile_payroll_schedules(
            db,
            company_id,
            [
                PayrollScheduleInput(
                    id=schedule_id,
                    label="Primary Payroll",
                    jurisdiction="FL",
                    frequency="biweekly",
                    payroll_platform="Gusto",
                    next_pay_date=date(2026, 9, 8),
                    next_process_date=date(2026, 9, 1),
                ),
                PayrollScheduleInput(
                    id=other_schedule_id,
                    label="Owner Payroll",
                    jurisdiction="FL",
                    frequency="weekly",
                    payroll_platform="Gusto",
                    next_pay_date=date(2026, 9, 4),
                    next_process_date=date(2026, 9, 1),
                ),
            ],
            today=today,
        )

    with test_session() as db:
        primary_tasks = db.execute(
            text(
                """
                SELECT id, process_date, pay_date, status
                FROM tasks
                WHERE payroll_schedule_id = :schedule_id
                ORDER BY process_date
                """
            ),
            {"schedule_id": schedule_id},
        ).all()
        other_tasks_after = db.execute(
            text(
                """
                SELECT id, process_date, pay_date, status
                FROM tasks
                WHERE payroll_schedule_id = :schedule_id
                ORDER BY id
                """
            ),
            {"schedule_id": other_schedule_id},
        ).all()
        duplicates = db.execute(
            text(
                """
                SELECT process_date, COUNT(*)
                FROM tasks
                WHERE payroll_schedule_id = :schedule_id
                GROUP BY process_date
                HAVING COUNT(*) > 1
                """
            ),
            {"schedule_id": schedule_id},
        ).all()

    by_process_date = {row.process_date: row for row in primary_tasks}
    assert by_process_date["2026-08-28"].status == "completed"
    assert by_process_date["2026-08-29"].status == "pending"
    assert by_process_date["2026-09-21"].id == progressed_task_id
    assert by_process_date["2026-09-21"].status == "in_progress"
    assert {row.process_date for row in primary_tasks if row.process_date > "2026-08-29"} == {
        "2026-09-01",
        "2026-09-16",
        "2026-09-21",
        "2026-09-30",
    }
    assert "2026-09-04" not in by_process_date
    assert "2026-10-05" not in by_process_date
    assert other_tasks_after == other_tasks_before
    assert duplicates == []
    engine.dispose()
