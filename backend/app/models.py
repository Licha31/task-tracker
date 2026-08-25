from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    ein: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    payroll_profile: Mapped[PayrollProfile | None] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    sales_tax_profile: Mapped[SalesTaxProfile | None] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    payroll_schedules: Mapped[list[PayrollSchedule]] = relationship(back_populates="company")
    sales_tax_registrations: Mapped[list[SalesTaxRegistration]] = relationship(
        back_populates="company"
    )


class PayrollProfile(Base):
    __tablename__ = "payroll_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        unique=True,
        nullable=False,
    )
    sui_id: Mapped[str | None] = mapped_column(String(50))
    sit_id: Mapped[str | None] = mapped_column(String(50))
    principal_owner: Mapped[str | None] = mapped_column(String(150))
    frequency: Mapped[str] = mapped_column(String(30), nullable=False)
    payroll_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    semi_monthly_day_1: Mapped[int | None] = mapped_column(Integer)
    semi_monthly_day_2: Mapped[int | None] = mapped_column(Integer)
    next_pay_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_process_date: Mapped[date] = mapped_column(Date, nullable=False)

    company: Mapped[Company] = relationship(back_populates="payroll_profile")


class SalesTaxProfile(Base):
    __tablename__ = "sales_tax_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        unique=True,
        nullable=False,
    )
    frequency: Mapped[str] = mapped_column(String(30), nullable=False)
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False)

    company: Mapped[Company] = relationship(back_populates="sales_tax_profile")


class PayrollSchedule(Base):
    __tablename__ = "payroll_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(20), nullable=False)
    sui_id: Mapped[str | None] = mapped_column(String(50))
    sit_id: Mapped[str | None] = mapped_column(String(50))
    principal_owner: Mapped[str | None] = mapped_column(String(150))
    frequency: Mapped[str] = mapped_column(String(30), nullable=False)
    payroll_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    semi_monthly_day_1: Mapped[int | None] = mapped_column(Integer)
    semi_monthly_day_2: Mapped[int | None] = mapped_column(Integer)
    next_pay_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_process_date: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    company: Mapped[Company] = relationship(back_populates="payroll_schedules")


class SalesTaxRegistration(Base):
    __tablename__ = "sales_tax_registrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    jurisdiction: Mapped[str] = mapped_column(String(20), nullable=False)
    frequency: Mapped[str] = mapped_column(String(30), nullable=False)
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    company: Mapped[Company] = relationship(back_populates="sales_tax_registrations")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
    )
    payroll_schedule_id: Mapped[int | None] = mapped_column(ForeignKey("payroll_schedules.id"))
    sales_tax_registration_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales_tax_registrations.id")
    )

    task_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    process_date: Mapped[date | None] = mapped_column(Date)
    pay_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    __table_args__ = (
        Index(
            "uq_tasks_payroll_schedule_occurrence",
            "payroll_schedule_id",
            "process_date",
            unique=True,
            sqlite_where=text("task_type = 'payroll'"),
            postgresql_where=text("task_type = 'payroll'"),
        ),
        Index(
            "uq_tasks_sales_tax_registration_occurrence",
            "sales_tax_registration_id",
            "due_date",
            unique=True,
            sqlite_where=text("task_type = 'sales_tax'"),
            postgresql_where=text("task_type = 'sales_tax'"),
        ),
    )
