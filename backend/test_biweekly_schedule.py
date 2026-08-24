from datetime import date

from app.payroll_schedule import generate_biweekly_payroll_dates

dates = generate_biweekly_payroll_dates(
    anchor_pay_date=date(2026, 8, 28),
    anchor_process_date=date(2026, 8, 26),
    occurrences=5,
)

for process_date, pay_date in dates:
    print(
        f"Process: {process_date} | Pay: {pay_date}"
    )