from datetime import date

from app.payroll_schedule import (
    generate_semi_monthly_payroll_dates,
)

dates = generate_semi_monthly_payroll_dates(
    start_date=date(2026, 8, 25),
    anchor_process_date=date(2026, 8, 21),
    day_1=10,
    day_2=25,
    occurrences=6,
)

for process_date, pay_date in dates:
    print(
        f"Process: {process_date} | Pay: {pay_date}"
    )