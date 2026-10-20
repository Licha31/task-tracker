from datetime import date

import pytest
from sqlalchemy import create_engine, text

from alembic import command
from test_migrations import alembic_config
from tools.migrate_postgres_to_sqlite import migrate


def source_fixture(tmp_path, monkeypatch):
    path = tmp_path / "source.db"
    url = f"sqlite:///{path.as_posix()}"
    command.upgrade(alembic_config(url, monkeypatch), "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO companies VALUES (7, 'Client', '77')"))
        connection.execute(text("""
            INSERT INTO payroll_schedules
            (id, company_id, label, jurisdiction, frequency, payroll_platform,
             next_pay_date, next_process_date, active)
            VALUES (11, 7, 'Main', 'FL', 'weekly', 'Gusto', '2026-10-23', '2026-10-21', 0)
        """))
        connection.execute(text("""
            INSERT INTO sales_tax_registrations
            (id, company_id, jurisdiction, frequency, next_due_date, active)
            VALUES (13, 7, 'GA', 'monthly', '2026-10-28', 1)
        """))
        connection.execute(text("""
            INSERT INTO payroll_profiles
            (id, company_id, frequency, payroll_platform, next_pay_date, next_process_date)
            VALUES (11, 7, 'weekly', 'Gusto', '2026-10-23', '2026-10-21')
        """))
        connection.execute(text("""
            INSERT INTO sales_tax_profiles (id, company_id, frequency, next_due_date)
            VALUES (13, 7, 'monthly', '2026-10-28')
        """))
        connection.execute(text("""
            INSERT INTO tasks
            (id, company_id, payroll_schedule_id, task_type, process_date, pay_date, status)
            VALUES (101, 7, 11, 'payroll', '2026-10-21', '2026-10-23', 'completed')
        """))
        connection.execute(text("""
            INSERT INTO tasks
            (id, company_id, sales_tax_registration_id, task_type, due_date, status)
            VALUES (102, 7, 13, 'sales_tax', '2026-10-28', 'in_progress')
        """))
    engine.dispose()
    return url, path


def test_import_preserves_all_data_and_source(tmp_path, monkeypatch):
    source_url, source_path = source_fixture(tmp_path, monkeypatch)
    before = source_path.read_bytes()
    target = tmp_path / "target.db"
    counts = migrate(source_url, target)
    assert counts == {
        "companies": 1,
        "payroll_schedules": 1,
        "sales_tax_registrations": 1,
        "payroll_profiles": 1,
        "sales_tax_profiles": 1,
        "tasks": 2,
    }
    assert source_path.read_bytes() == before
    engine = create_engine(f"sqlite:///{target.as_posix()}")
    with engine.connect() as connection:
        tasks = connection.execute(text("SELECT * FROM tasks ORDER BY id")).mappings().all()
        assert [(row["id"], row["status"]) for row in tasks] == [(101, "completed"), (102, "in_progress")]
        assert tasks[0]["payroll_schedule_id"] == 11
        assert tasks[0]["process_date"] == date(2026, 10, 21).isoformat()
        assert tasks[1]["sales_tax_registration_id"] == 13
        assert tasks[1]["due_date"] == date(2026, 10, 28).isoformat()
        assert connection.execute(text("SELECT active FROM payroll_schedules WHERE id=11")).scalar_one() == 0
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    engine.dispose()


def test_existing_target_requires_overwrite_and_creates_backup(tmp_path, monkeypatch):
    source_url, _ = source_fixture(tmp_path, monkeypatch)
    target = tmp_path / "target.db"
    target.write_bytes(b"existing SQLite data")
    with pytest.raises(FileExistsError):
        migrate(source_url, target)
    assert target.read_bytes() == b"existing SQLite data"
    migrate(source_url, target, overwrite=True)
    backups = list(tmp_path.glob("target-*.db"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"existing SQLite data"


def test_import_rejects_orphan_without_touching_target(tmp_path, monkeypatch):
    source_url, _ = source_fixture(tmp_path, monkeypatch)
    source = create_engine(source_url)
    with source.begin() as connection:
        connection.execute(text("UPDATE tasks SET company_id=999 WHERE id=101"))
    source.dispose()
    target = tmp_path / "target.db"
    with pytest.raises(ValueError, match="no company"):
        migrate(source_url, target)
    assert not target.exists()
