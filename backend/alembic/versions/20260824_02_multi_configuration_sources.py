"""Add multiple source configurations and backfill existing tasks."""

import sqlalchemy as sa

from alembic import op

revision = "20260824_02"
down_revision = "20260824_01"
branch_labels = None
depends_on = None


def scalar(connection, sql: str) -> int:
    return connection.execute(sa.text(sql)).scalar_one()


def assert_legacy_task_shapes_are_valid(connection) -> None:
    unsupported_task_types = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE task_type NOT IN ('payroll', 'sales_tax')
        """,
    )
    if unsupported_task_types:
        raise RuntimeError(
            "Migration aborted: tasks contain unsupported task types "
            f"(invalid tasks: {unsupported_task_types})."
        )

    payroll_without_process_date = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE task_type = 'payroll' AND process_date IS NULL
        """,
    )
    sales_tax_without_due_date = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE task_type = 'sales_tax' AND due_date IS NULL
        """,
    )
    if payroll_without_process_date or sales_tax_without_due_date:
        raise RuntimeError(
            "Migration aborted: tasks are missing required operational dates "
            "(payroll tasks missing process_date: "
            f"{payroll_without_process_date}; sales-tax tasks missing due_date: "
            f"{sales_tax_without_due_date})."
        )


def assert_legacy_tasks_are_assignable(connection) -> None:
    missing_payroll = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM tasks AS t
        LEFT JOIN payroll_profiles AS p ON p.company_id = t.company_id
        WHERE t.task_type = 'payroll' AND p.id IS NULL
        """,
    )
    missing_sales_tax = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM tasks AS t
        LEFT JOIN sales_tax_profiles AS s ON s.company_id = t.company_id
        WHERE t.task_type = 'sales_tax' AND s.id IS NULL
        """,
    )
    if missing_payroll or missing_sales_tax:
        raise RuntimeError(
            "Migration aborted: every existing Payroll and Sales Tax task must have a "
            "deterministic legacy profile (missing payroll tasks: "
            f"{missing_payroll}; missing sales-tax tasks: {missing_sales_tax})."
        )


def assert_copy_is_exact(connection) -> None:
    payroll_profiles = (
        connection.execute(sa.text("SELECT * FROM payroll_profiles ORDER BY id")).mappings().all()
    )
    payroll_schedules = (
        connection.execute(sa.text("SELECT * FROM payroll_schedules ORDER BY id")).mappings().all()
    )
    if len(payroll_profiles) != len(payroll_schedules):
        raise RuntimeError("Migration aborted: Payroll Schedule copy count does not match.")

    payroll_fields = (
        "id",
        "company_id",
        "sui_id",
        "sit_id",
        "principal_owner",
        "frequency",
        "payroll_platform",
        "semi_monthly_day_1",
        "semi_monthly_day_2",
        "next_pay_date",
        "next_process_date",
    )
    for profile, schedule in zip(payroll_profiles, payroll_schedules, strict=True):
        if any(profile[field] != schedule[field] for field in payroll_fields):
            raise RuntimeError("Migration aborted: a Payroll Schedule value was not preserved.")
        if schedule["label"] != "Primary Payroll" or schedule["jurisdiction"] != "UNSET":
            raise RuntimeError("Migration aborted: Payroll migration defaults are invalid.")

    sales_profiles = (
        connection.execute(sa.text("SELECT * FROM sales_tax_profiles ORDER BY id")).mappings().all()
    )
    registrations = (
        connection.execute(sa.text("SELECT * FROM sales_tax_registrations ORDER BY id"))
        .mappings()
        .all()
    )
    if len(sales_profiles) != len(registrations):
        raise RuntimeError("Migration aborted: Sales Tax Registration copy count does not match.")

    sales_fields = ("id", "company_id", "frequency", "next_due_date")
    for profile, registration in zip(sales_profiles, registrations, strict=True):
        if any(profile[field] != registration[field] for field in sales_fields):
            raise RuntimeError("Migration aborted: a Sales Tax value was not preserved.")
        if registration["jurisdiction"] != "UNSET":
            raise RuntimeError("Migration aborted: Sales Tax migration jurisdiction is invalid.")


def assert_task_backfill_is_complete(connection) -> None:
    invalid = scalar(
        connection,
        """
        SELECT COUNT(*)
        FROM tasks AS t
        LEFT JOIN payroll_schedules AS p ON p.id = t.payroll_schedule_id
        LEFT JOIN sales_tax_registrations AS s ON s.id = t.sales_tax_registration_id
        WHERE
            (t.task_type = 'payroll' AND (
                t.payroll_schedule_id IS NULL
                OR t.sales_tax_registration_id IS NOT NULL
                OR p.company_id != t.company_id
            ))
            OR
            (t.task_type = 'sales_tax' AND (
                t.sales_tax_registration_id IS NULL
                OR t.payroll_schedule_id IS NOT NULL
                OR s.company_id != t.company_id
            ))
        """,
    )
    if invalid:
        raise RuntimeError(f"Migration aborted: {invalid} tasks have invalid source associations.")


def reset_postgresql_sequence(connection, table_name: str) -> None:
    maximum_id = connection.execute(sa.text(f"SELECT MAX(id) FROM {table_name}")).scalar_one()
    connection.execute(
        sa.text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), :value, :is_called)"),
        {"value": maximum_id or 1, "is_called": maximum_id is not None},
    )


def upgrade() -> None:
    connection = op.get_bind()
    assert_legacy_task_shapes_are_valid(connection)
    assert_legacy_tasks_are_assignable(connection)

    op.create_table(
        "payroll_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("jurisdiction", sa.String(length=20), nullable=False),
        sa.Column("sui_id", sa.String(length=50)),
        sa.Column("sit_id", sa.String(length=50)),
        sa.Column("principal_owner", sa.String(length=150)),
        sa.Column("frequency", sa.String(length=30), nullable=False),
        sa.Column("payroll_platform", sa.String(length=50), nullable=False),
        sa.Column("semi_monthly_day_1", sa.Integer()),
        sa.Column("semi_monthly_day_2", sa.Integer()),
        sa.Column("next_pay_date", sa.Date(), nullable=False),
        sa.Column("next_process_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index(
        "ix_payroll_schedules_company_id",
        "payroll_schedules",
        ["company_id"],
    )
    op.create_table(
        "sales_tax_registrations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=20), nullable=False),
        sa.Column("frequency", sa.String(length=30), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index(
        "ix_sales_tax_registrations_company_id",
        "sales_tax_registrations",
        ["company_id"],
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO payroll_schedules (
                id, company_id, label, jurisdiction, sui_id, sit_id, principal_owner,
                frequency, payroll_platform, semi_monthly_day_1, semi_monthly_day_2,
                next_pay_date, next_process_date, active
            )
            SELECT
                id, company_id, 'Primary Payroll', 'UNSET', sui_id, sit_id, principal_owner,
                frequency, payroll_platform, semi_monthly_day_1, semi_monthly_day_2,
                next_pay_date, next_process_date, TRUE
            FROM payroll_profiles
            """
        )
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO sales_tax_registrations (
                id, company_id, jurisdiction, frequency, next_due_date, active
            )
            SELECT id, company_id, 'UNSET', frequency, next_due_date, TRUE
            FROM sales_tax_profiles
            """
        )
    )
    assert_copy_is_exact(connection)

    if connection.dialect.name == "sqlite":
        op.execute(
            "ALTER TABLE tasks ADD COLUMN payroll_schedule_id INTEGER "
            "REFERENCES payroll_schedules(id)"
        )
        op.execute(
            "ALTER TABLE tasks ADD COLUMN sales_tax_registration_id INTEGER "
            "REFERENCES sales_tax_registrations(id)"
        )
    else:
        op.add_column(
            "tasks",
            sa.Column(
                "payroll_schedule_id",
                sa.Integer(),
                sa.ForeignKey("payroll_schedules.id"),
            ),
        )
        op.add_column(
            "tasks",
            sa.Column(
                "sales_tax_registration_id",
                sa.Integer(),
                sa.ForeignKey("sales_tax_registrations.id"),
            ),
        )

    connection.execute(
        sa.text(
            """
            UPDATE tasks
            SET payroll_schedule_id = (
                SELECT id FROM payroll_schedules
                WHERE payroll_schedules.company_id = tasks.company_id
            )
            WHERE task_type = 'payroll'
            """
        )
    )
    connection.execute(
        sa.text(
            """
            UPDATE tasks
            SET sales_tax_registration_id = (
                SELECT id FROM sales_tax_registrations
                WHERE sales_tax_registrations.company_id = tasks.company_id
            )
            WHERE task_type = 'sales_tax'
            """
        )
    )
    assert_task_backfill_is_complete(connection)

    payroll_filter = sa.text("task_type = 'payroll'")
    sales_tax_filter = sa.text("task_type = 'sales_tax'")
    op.create_index(
        "uq_tasks_payroll_schedule_occurrence",
        "tasks",
        ["payroll_schedule_id", "process_date"],
        unique=True,
        sqlite_where=payroll_filter,
        postgresql_where=payroll_filter,
    )
    op.create_index(
        "uq_tasks_sales_tax_registration_occurrence",
        "tasks",
        ["sales_tax_registration_id", "due_date"],
        unique=True,
        sqlite_where=sales_tax_filter,
        postgresql_where=sales_tax_filter,
    )
    op.drop_index("uq_tasks_payroll_occurrence", table_name="tasks")
    op.drop_index("uq_tasks_sales_tax_occurrence", table_name="tasks")

    if connection.dialect.name == "postgresql":
        reset_postgresql_sequence(connection, "payroll_schedules")
        reset_postgresql_sequence(connection, "sales_tax_registrations")


def assert_downgrade_is_lossless(connection) -> None:
    payroll_profiles = (
        connection.execute(sa.text("SELECT * FROM payroll_profiles ORDER BY id")).mappings().all()
    )
    payroll_schedules = (
        connection.execute(sa.text("SELECT * FROM payroll_schedules ORDER BY id")).mappings().all()
    )
    payroll_fields = (
        "id",
        "company_id",
        "sui_id",
        "sit_id",
        "principal_owner",
        "frequency",
        "payroll_platform",
        "semi_monthly_day_1",
        "semi_monthly_day_2",
        "next_pay_date",
        "next_process_date",
    )
    payroll_changed = len(payroll_profiles) != len(payroll_schedules) or any(
        any(profile[field] != schedule[field] for field in payroll_fields)
        or schedule["label"] != "Primary Payroll"
        or schedule["jurisdiction"] != "UNSET"
        or not schedule["active"]
        for profile, schedule in zip(payroll_profiles, payroll_schedules, strict=False)
    )

    sales_profiles = (
        connection.execute(sa.text("SELECT * FROM sales_tax_profiles ORDER BY id")).mappings().all()
    )
    registrations = (
        connection.execute(sa.text("SELECT * FROM sales_tax_registrations ORDER BY id"))
        .mappings()
        .all()
    )
    sales_fields = ("id", "company_id", "frequency", "next_due_date")
    sales_changed = len(sales_profiles) != len(registrations) or any(
        any(profile[field] != registration[field] for field in sales_fields)
        or registration["jurisdiction"] != "UNSET"
        or not registration["active"]
        for profile, registration in zip(sales_profiles, registrations, strict=False)
    )
    payroll_duplicates = scalar(
        connection,
        """
        SELECT COUNT(*) FROM (
            SELECT company_id, process_date
            FROM tasks WHERE task_type = 'payroll'
            GROUP BY company_id, process_date HAVING COUNT(*) > 1
        ) AS duplicates
        """,
    )
    sales_duplicates = scalar(
        connection,
        """
        SELECT COUNT(*) FROM (
            SELECT company_id, due_date
            FROM tasks WHERE task_type = 'sales_tax'
            GROUP BY company_id, due_date HAVING COUNT(*) > 1
        ) AS duplicates
        """,
    )
    if payroll_changed or sales_changed or payroll_duplicates or sales_duplicates:
        raise RuntimeError(
            "Downgrade aborted: multi-configuration writes or configuration edits cannot be "
            "represented by the legacy schema without data loss."
        )


def downgrade() -> None:
    connection = op.get_bind()
    assert_downgrade_is_lossless(connection)

    payroll_filter = sa.text("task_type = 'payroll'")
    sales_tax_filter = sa.text("task_type = 'sales_tax'")
    op.create_index(
        "uq_tasks_payroll_occurrence",
        "tasks",
        ["company_id", "task_type", "process_date"],
        unique=True,
        sqlite_where=payroll_filter,
        postgresql_where=payroll_filter,
    )
    op.create_index(
        "uq_tasks_sales_tax_occurrence",
        "tasks",
        ["company_id", "task_type", "due_date"],
        unique=True,
        sqlite_where=sales_tax_filter,
        postgresql_where=sales_tax_filter,
    )
    op.drop_index("uq_tasks_payroll_schedule_occurrence", table_name="tasks")
    op.drop_index("uq_tasks_sales_tax_registration_occurrence", table_name="tasks")

    if connection.dialect.name == "sqlite":
        op.execute("ALTER TABLE tasks DROP COLUMN sales_tax_registration_id")
        op.execute("ALTER TABLE tasks DROP COLUMN payroll_schedule_id")
    else:
        op.drop_column("tasks", "sales_tax_registration_id")
        op.drop_column("tasks", "payroll_schedule_id")

    op.drop_index("ix_sales_tax_registrations_company_id", table_name="sales_tax_registrations")
    op.drop_table("sales_tax_registrations")
    op.drop_index("ix_payroll_schedules_company_id", table_name="payroll_schedules")
    op.drop_table("payroll_schedules")
