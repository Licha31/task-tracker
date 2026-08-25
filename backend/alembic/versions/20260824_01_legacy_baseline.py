"""Represent the schema deployed before Alembic.

Existing databases must be inspected and stamped at this revision; this upgrade
function is for creating an isolated or new database from scratch.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260824_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("ein", sa.String(length=20), nullable=False),
        sa.UniqueConstraint("ein"),
    )
    op.create_table(
        "payroll_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("sui_id", sa.String(length=50)),
        sa.Column("sit_id", sa.String(length=50)),
        sa.Column("principal_owner", sa.String(length=150)),
        sa.Column("frequency", sa.String(length=30), nullable=False),
        sa.Column("payroll_platform", sa.String(length=50), nullable=False),
        sa.Column("semi_monthly_day_1", sa.Integer()),
        sa.Column("semi_monthly_day_2", sa.Integer()),
        sa.Column("next_pay_date", sa.Date(), nullable=False),
        sa.Column("next_process_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.UniqueConstraint("company_id"),
    )
    op.create_table(
        "sales_tax_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.String(length=30), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.UniqueConstraint("company_id"),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=20), nullable=False),
        sa.Column("process_date", sa.Date()),
        sa.Column("pay_date", sa.Date()),
        sa.Column("due_date", sa.Date()),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
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


def downgrade() -> None:
    op.drop_index("uq_tasks_sales_tax_occurrence", table_name="tasks")
    op.drop_index("uq_tasks_payroll_occurrence", table_name="tasks")
    op.drop_table("tasks")
    op.drop_table("sales_tax_profiles")
    op.drop_table("payroll_profiles")
    op.drop_table("companies")
