from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

PayrollFrequency = Literal["weekly", "biweekly", "semi_monthly", "monthly"]
SalesTaxFrequency = Literal["monthly", "quarterly"]


class PayrollScheduleInput(BaseModel):
    id: int | None = None
    label: str = Field(min_length=1, max_length=100)
    jurisdiction: str = Field(min_length=1, max_length=20)
    sui_id: str | None = None
    sit_id: str | None = None
    principal_owner: str | None = None
    frequency: PayrollFrequency
    payroll_platform: str = Field(min_length=1, max_length=50)
    next_pay_date: date
    next_process_date: date
    semi_monthly_day_1: int | None = Field(default=None, ge=1, le=31)
    semi_monthly_day_2: int | None = Field(default=None, ge=1, le=31)

    @model_validator(mode="after")
    def validate_semi_monthly_days(self):
        if self.frequency == "semi_monthly":
            if self.semi_monthly_day_1 is None or self.semi_monthly_day_2 is None:
                raise ValueError("Both semi-monthly pay days are required")
            if self.semi_monthly_day_1 == self.semi_monthly_day_2:
                raise ValueError("Semi-monthly pay days must be different")
        return self


class SalesTaxRegistrationInput(BaseModel):
    id: int | None = None
    jurisdiction: str = Field(min_length=1, max_length=20)
    frequency: SalesTaxFrequency
    next_due_date: date


class CompanyInput(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    ein: str = Field(min_length=1, max_length=20)
    payroll_schedules: list[PayrollScheduleInput] = Field(default_factory=list)
    sales_tax_registrations: list[SalesTaxRegistrationInput] = Field(default_factory=list)


class PayrollScheduleRead(PayrollScheduleInput):
    id: int


class SalesTaxRegistrationRead(SalesTaxRegistrationInput):
    id: int


class CompanyRead(BaseModel):
    id: int
    name: str
    ein: str
    payroll_schedules: list[PayrollScheduleRead]
    sales_tax_registrations: list[SalesTaxRegistrationRead]
