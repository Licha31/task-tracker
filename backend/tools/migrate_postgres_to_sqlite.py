"""One-time, read-only source import into an Alembic-built SQLite database."""

import argparse
import os
import shutil
import tempfile
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, select, text

from alembic import command
from app.database import DEFAULT_DATABASE_PATH
from app.models import (
    Company,
    PayrollProfile,
    PayrollSchedule,
    SalesTaxProfile,
    SalesTaxRegistration,
    Task,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
TABLES = [
    Company.__table__,
    PayrollSchedule.__table__,
    SalesTaxRegistration.__table__,
    PayrollProfile.__table__,
    SalesTaxProfile.__table__,
    Task.__table__,
]


def normalized(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def rows(connection, table):
    return [dict(row) for row in connection.execute(select(table).order_by(table.c.id)).mappings()]


def comparable(data):
    return [{key: normalized(value) for key, value in row.items()} for row in data]


def validate_relationships(data):
    companies = {row["id"] for row in data["companies"]}
    schedules = {row["id"]: row for row in data["payroll_schedules"]}
    registrations = {row["id"]: row for row in data["sales_tax_registrations"]}
    task_ids = [row["id"] for row in data["tasks"]]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("Duplicate task IDs")
    for task in data["tasks"]:
        company_id = task["company_id"]
        if company_id not in companies:
            raise ValueError(f"Task {task['id']} has no company")
        if task["task_type"] == "payroll":
            source = schedules.get(task["payroll_schedule_id"])
            if source is None or task["sales_tax_registration_id"] is not None:
                raise ValueError(f"Payroll task {task['id']} has no valid source")
        elif task["task_type"] == "sales_tax":
            source = registrations.get(task["sales_tax_registration_id"])
            if source is None or task["payroll_schedule_id"] is not None:
                raise ValueError(f"Sales Tax task {task['id']} has no valid source")
        else:
            raise ValueError(f"Task {task['id']} has unsupported type")
        if source["company_id"] != company_id:
            raise ValueError(f"Task {task['id']} source belongs to another company")
    for table_name in ("payroll_schedules", "sales_tax_registrations", "payroll_profiles", "sales_tax_profiles"):
        for row in data[table_name]:
            if row["company_id"] not in companies:
                raise ValueError(f"{table_name} row {row['id']} has no company")


@contextmanager
def source_connection(source_url):
    engine = create_engine(source_url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                if connection.dialect.name == "postgresql":
                    connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
                elif connection.dialect.name == "sqlite":
                    connection.execute(text("PRAGMA query_only=ON"))
                else:
                    raise ValueError("Source must be PostgreSQL (or SQLite for an isolated test)")
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def migrate(source_url: str, target: Path = DEFAULT_DATABASE_PATH, overwrite: bool = False) -> dict[str, int]:
    if not source_url:
        raise ValueError("SOURCE_DATABASE_URL is required")
    target = target.resolve()
    if target.exists() and not overwrite:
        raise FileExistsError(f"Target exists: {target}. Use --overwrite to back it up and replace it.")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, staging_name = tempfile.mkstemp(prefix=".task-tracker-import-", suffix=".db", dir=target.parent)
    os.close(descriptor)
    staging = Path(staging_name)
    staging.unlink()
    sqlite_url = f"sqlite:///{staging.as_posix()}"
    try:
        with source_connection(source_url) as source:
            source_data = {table.name: rows(source, table) for table in TABLES}
            validate_relationships(source_data)

            config = Config(str(BACKEND_ROOT / "alembic.ini"))
            config.cmd_opts = argparse.Namespace(x=[f"database_url={sqlite_url}"])
            command.upgrade(config, "head")
            expected_head = ScriptDirectory.from_config(config).get_current_head()

            engine = create_engine(sqlite_url)

            @event.listens_for(engine, "connect")
            def enable_foreign_keys(dbapi_connection, _record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            try:
                with engine.begin() as destination:
                    for table in TABLES:
                        if source_data[table.name]:
                            destination.execute(table.insert(), source_data[table.name])
                with engine.connect() as destination:
                    actual_head = destination.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    if actual_head != expected_head:
                        raise ValueError(f"Alembic revision mismatch: {actual_head} != {expected_head}")
                    target_data = {table.name: rows(destination, table) for table in TABLES}
                    validate_relationships(target_data)
                    for table in TABLES:
                        if comparable(source_data[table.name]) != comparable(target_data[table.name]):
                            raise ValueError(f"Imported data differs in {table.name}")
                    foreign_key_errors = destination.execute(text("PRAGMA foreign_key_check")).all()
                    if foreign_key_errors:
                        raise ValueError(f"SQLite foreign key check failed: {foreign_key_errors}")
            finally:
                engine.dispose()

        if target.exists():
            if not overwrite:
                raise FileExistsError(f"Target appeared during import: {target}")
            stamp = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S-%f")
            backup = target.with_name(f"{target.stem}-{stamp}.db")
            with target.open("rb") as source_file, backup.open("xb") as backup_file:
                shutil.copyfileobj(source_file, backup_file)
            if not backup.is_file() or backup.stat().st_size != target.stat().st_size:
                raise OSError("Existing database backup failed; target was not replaced")
            print(f"Existing SQLite backup: {backup}")
        os.replace(staging, target)
        for table in TABLES:
            count = len(source_data[table.name])
            print(f"{table.name}: {count} / {count}")
        print("Foreign key check: PASS")
        print("Migration: SUCCESS")
        return {table.name: len(source_data[table.name]) for table in TABLES}
    finally:
        staging.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    source_url = os.getenv("SOURCE_DATABASE_URL", "")
    if not source_url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
        parser.error("Set SOURCE_DATABASE_URL to an explicit PostgreSQL URL")
    if source_url.startswith("postgres://"):
        source_url = source_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif source_url.startswith("postgresql://"):
        source_url = source_url.replace("postgresql://", "postgresql+psycopg://", 1)
    migrate(source_url, args.target, args.overwrite)


if __name__ == "__main__":
    main()
