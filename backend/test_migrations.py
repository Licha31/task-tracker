from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command

BACKEND_ROOT = Path(__file__).parent
BASELINE_REVISION = "20260824_01"


def alembic_config(database_url: str, monkeypatch) -> Config:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    return Config(BACKEND_ROOT / "alembic.ini")


def test_old_schema_data_is_preserved_and_backfilled(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    config = alembic_config(database_url, monkeypatch)
    command.upgrade(config, BASELINE_REVISION)
    engine = create_engine(database_url)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO companies (id, name, ein) VALUES
                    (10, 'Company A', '10-0000001'),
                    (20, 'Company Without Services', '20-0000002')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO payroll_profiles (
                    id, company_id, sui_id, sit_id, principal_owner, frequency,
                    payroll_platform, semi_monthly_day_1, semi_monthly_day_2,
                    next_pay_date, next_process_date
                ) VALUES (
                    31, 10, 'SUI-1', 'SIT-1', 'Alex', 'weekly',
                    'Gusto', NULL, NULL, '2026-08-28', '2026-08-24'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO sales_tax_profiles (id, company_id, frequency, next_due_date)
                VALUES (41, 10, 'monthly', '2026-08-25')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO tasks (
                    id, company_id, task_type, process_date, pay_date, due_date, status
                ) VALUES
                    (101, 10, 'payroll', '2026-08-24', '2026-08-28', NULL, 'completed'),
                    (102, 10, 'sales_tax', NULL, NULL, '2026-08-25', 'in_progress')
                """
            )
        )

    command.upgrade(config, "head")

    with engine.connect() as connection:
        company = connection.execute(
            text("SELECT id, name, ein FROM companies WHERE id = 10")
        ).one()
        schedule = (
            connection.execute(text("SELECT * FROM payroll_schedules WHERE id = 31"))
            .mappings()
            .one()
        )
        registration = (
            connection.execute(text("SELECT * FROM sales_tax_registrations WHERE id = 41"))
            .mappings()
            .one()
        )
        tasks = connection.execute(text("SELECT * FROM tasks ORDER BY id")).mappings().all()

        assert company == (10, "Company A", "10-0000001")
        assert schedule["company_id"] == 10
        assert schedule["label"] == "Primary Payroll"
        assert schedule["jurisdiction"] == "UNSET"
        assert schedule["sui_id"] == "SUI-1"
        assert schedule["sit_id"] == "SIT-1"
        assert schedule["principal_owner"] == "Alex"
        assert schedule["frequency"] == "weekly"
        assert schedule["payroll_platform"] == "Gusto"
        assert schedule["next_pay_date"] == "2026-08-28"
        assert schedule["next_process_date"] == "2026-08-24"
        assert schedule["active"] == 1
        assert registration["jurisdiction"] == "UNSET"
        assert registration["frequency"] == "monthly"
        assert registration["next_due_date"] == "2026-08-25"
        assert [(task["id"], task["status"]) for task in tasks] == [
            (101, "completed"),
            (102, "in_progress"),
        ]
        assert tasks[0]["payroll_schedule_id"] == 31
        assert tasks[1]["sales_tax_registration_id"] == 41
        assert connection.execute(text("SELECT COUNT(*) FROM payroll_profiles")).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM sales_tax_profiles")).scalar_one() == 1
        assert (
            connection.execute(text("SELECT COUNT(*) FROM companies WHERE id = 20")).scalar_one()
            == 1
        )

    with engine.begin() as connection:
        second_schedule_id = connection.execute(
            text(
                """
                INSERT INTO payroll_schedules (
                    company_id, label, jurisdiction, frequency, payroll_platform,
                    next_pay_date, next_process_date, active
                ) VALUES (10, 'Owners', 'GA', 'weekly', 'Gusto',
                          '2026-08-28', '2026-08-24', TRUE)
                """
            )
        ).lastrowid
        connection.execute(
            text(
                """
                INSERT INTO tasks (
                    company_id, payroll_schedule_id, task_type, process_date, pay_date, status
                ) VALUES (10, :schedule_id, 'payroll', '2026-08-24', '2026-08-28', 'pending')
                """
            ),
            {"schedule_id": second_schedule_id},
        )

    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                """
                    INSERT INTO tasks (
                        company_id, payroll_schedule_id, task_type,
                        process_date, pay_date, status
                    ) VALUES (10, 31, 'payroll', '2026-08-24', '2026-08-28', 'pending')
                    """
            )
        )

    engine.dispose()


def test_migration_aborts_when_a_task_has_no_legacy_profile(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'orphan.db').as_posix()}"
    config = alembic_config(database_url, monkeypatch)
    command.upgrade(config, BASELINE_REVISION)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO companies (id, name, ein) VALUES (1, 'Orphan', '11-1111111')")
        )
        connection.execute(
            text(
                """
                INSERT INTO tasks (
                    id, company_id, task_type, process_date, pay_date, status
                ) VALUES (1, 1, 'payroll', '2026-08-24', '2026-08-28', 'pending')
                """
            )
        )

    with pytest.raises(RuntimeError, match="deterministic legacy profile"):
        command.upgrade(config, "head")

    assert "payroll_schedules" not in inspect(engine).get_table_names()
    engine.dispose()


def test_migration_aborts_for_an_unsupported_legacy_task_type(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'unsupported-task-type.db').as_posix()}"
    config = alembic_config(database_url, monkeypatch)
    command.upgrade(config, BASELINE_REVISION)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO companies (id, name, ein) VALUES (1, 'Invalid', '11-1111111')")
        )
        connection.execute(
            text(
                """
                INSERT INTO tasks (id, company_id, task_type, due_date, status)
                VALUES (1, 1, 'other', '2026-08-24', 'pending')
                """
            )
        )

    with pytest.raises(RuntimeError, match="unsupported task types"):
        command.upgrade(config, "head")

    assert "payroll_schedules" not in inspect(engine).get_table_names()
    engine.dispose()


@pytest.mark.parametrize(
    ("task_type", "task_columns", "task_values", "profile_sql", "message"),
    [
        (
            "payroll",
            "process_date, pay_date",
            "NULL, '2026-08-28'",
            """
            INSERT INTO payroll_profiles (
                id, company_id, frequency, payroll_platform, next_pay_date, next_process_date
            ) VALUES (1, 1, 'weekly', 'Gusto', '2026-08-28', '2026-08-24')
            """,
            "payroll tasks missing process_date: 1",
        ),
        (
            "sales_tax",
            "due_date",
            "NULL",
            """
            INSERT INTO sales_tax_profiles (id, company_id, frequency, next_due_date)
            VALUES (1, 1, 'monthly', '2026-08-25')
            """,
            "sales-tax tasks missing due_date: 1",
        ),
    ],
    ids=["payroll-without-process-date", "sales-tax-without-due-date"],
)
def test_migration_aborts_for_missing_legacy_operational_date(
    tmp_path,
    monkeypatch,
    task_type,
    task_columns,
    task_values,
    profile_sql,
    message,
):
    database_url = f"sqlite:///{(tmp_path / f'{task_type}-missing-date.db').as_posix()}"
    config = alembic_config(database_url, monkeypatch)
    command.upgrade(config, BASELINE_REVISION)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO companies (id, name, ein) VALUES (1, 'Invalid', '11-1111111')")
        )
        connection.execute(text(profile_sql))
        connection.execute(
            text(
                f"""
                INSERT INTO tasks (
                    id, company_id, task_type, {task_columns}, status
                ) VALUES (1, 1, :task_type, {task_values}, 'pending')
                """
            ),
            {"task_type": task_type},
        )

    with pytest.raises(RuntimeError, match=message):
        command.upgrade(config, "head")

    assert "payroll_schedules" not in inspect(engine).get_table_names()
    engine.dispose()


def test_additive_revision_can_downgrade_before_new_writes(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'downgrade.db').as_posix()}"
    config = alembic_config(database_url, monkeypatch)
    command.upgrade(config, BASELINE_REVISION)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO companies (id, name, ein) VALUES (1, 'A', '11-1111111')")
        )
        connection.execute(
            text(
                """
                INSERT INTO payroll_profiles (
                    id, company_id, frequency, payroll_platform, next_pay_date, next_process_date
                ) VALUES (1, 1, 'weekly', 'Gusto', '2026-08-28', '2026-08-24')
                """
            )
        )
    command.upgrade(config, "head")
    command.downgrade(config, BASELINE_REVISION)

    tables = inspect(engine).get_table_names()
    assert "payroll_profiles" in tables
    assert "payroll_schedules" not in tables
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM payroll_profiles")).scalar_one() == 1
    engine.dispose()


def test_downgrade_refuses_multi_configuration_writes(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'guarded-downgrade.db').as_posix()}"
    config = alembic_config(database_url, monkeypatch)
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO companies (id, name, ein) VALUES (1, 'A', '11-1111111')")
        )
        connection.execute(
            text(
                """
                INSERT INTO payroll_schedules (
                    company_id, label, jurisdiction, frequency, payroll_platform,
                    next_pay_date, next_process_date, active
                ) VALUES (1, 'New Payroll', 'FL', 'weekly', 'Gusto',
                          '2026-08-28', '2026-08-24', TRUE)
                """
            )
        )

    with pytest.raises(RuntimeError, match="cannot be represented"):
        command.downgrade(config, BASELINE_REVISION)

    assert "payroll_schedules" in inspect(engine).get_table_names()
    engine.dispose()
