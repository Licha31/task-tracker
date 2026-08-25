from sqlalchemy import text

from app.database import engine

with engine.connect() as connection:
    payroll_profiles = connection.execute(
        text(
            """
            SELECT
                company_id,
                frequency,
                next_pay_date,
                next_process_date,
                semi_monthly_day_1,
                semi_monthly_day_2
            FROM payroll_profiles
            """
        )
    ).mappings().all()

    sales_tax_profiles = connection.execute(
        text(
            """
            SELECT
                company_id,
                frequency,
                next_due_date
            FROM sales_tax_profiles
            """
        )
    ).mappings().all()


print("PAYROLL")
for profile in payroll_profiles:
    print(dict(profile))

print()

print("SALES TAX")
for profile in sales_tax_profiles:
    print(dict(profile))