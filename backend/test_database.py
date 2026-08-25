from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base, resolve_database_url
from app.models import Company, PayrollSchedule, SalesTaxRegistration, Task
from app.task_generation import insert_task_if_missing


def test_database_url_defaults_to_sqlite_outside_production():
    assert resolve_database_url("development", "") == "sqlite:///./payroll_tracker.db"


def test_database_url_is_required_in_production():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        resolve_database_url("production", "")


@pytest.mark.parametrize("scheme", ["postgres://", "postgresql://"])
def test_postgresql_url_selects_psycopg_3(scheme):
    resolved = resolve_database_url("production", f"{scheme}user:pass@host/db")
    assert resolved == "postgresql+psycopg://user:pass@host/db"


def test_duplicate_task_occurrences_are_ignored(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'duplicates.db').as_posix()}")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        company = Company(name="Example", ein="12-3456789")
        db.add(company)
        db.flush()

        payroll_schedule = PayrollSchedule(
            company_id=company.id,
            label="Employees",
            jurisdiction="FL",
            frequency="weekly",
            payroll_platform="Gusto",
            next_pay_date=date(2026, 8, 26),
            next_process_date=date(2026, 8, 24),
        )
        sales_tax_registration = SalesTaxRegistration(
            company_id=company.id,
            jurisdiction="GA",
            frequency="monthly",
            next_due_date=date(2026, 8, 27),
        )
        db.add_all([payroll_schedule, sales_tax_registration])
        db.flush()

        payroll = {
            "company_id": company.id,
            "payroll_schedule_id": payroll_schedule.id,
            "task_type": "payroll",
            "process_date": date(2026, 8, 24),
            "pay_date": date(2026, 8, 26),
            "status": "pending",
        }
        sales_tax = {
            "company_id": company.id,
            "sales_tax_registration_id": sales_tax_registration.id,
            "task_type": "sales_tax",
            "due_date": date(2026, 8, 27),
            "status": "pending",
        }
        insert_task_if_missing(db, payroll)
        insert_task_if_missing(db, payroll)
        insert_task_if_missing(db, sales_tax)
        insert_task_if_missing(db, sales_tax)
        db.commit()

        assert db.query(Task).count() == 2

    engine.dispose()
