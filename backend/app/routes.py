from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from app.auth import password_is_valid, require_admin
from app.database import get_db
from app.models import Company
from app.schemas import CompanyInput, CompanyRead
from app.task_generation import ensure_tasks_until

router = APIRouter(prefix="/api")


class TaskStatusUpdate(BaseModel):
    status: str


class AdminLogin(BaseModel):
    password: str


@router.post("/auth/login")
def login(payload: AdminLogin, request: Request, response: Response):
    if not password_is_valid(payload.password):
        raise HTTPException(status_code=401, detail="Incorrect password")

    request.session.clear()
    request.session["access"] = "admin"
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": True}


@router.get("/auth/session")
def get_auth_session(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": request.session.get("access") == "admin"}


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request):
    request.session.clear()
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"Cache-Control": "no-store"},
    )


def build_company(db: Session, company) -> dict:
    payroll_schedules = (
        db.execute(
            text(
                """
            SELECT
                id, label, jurisdiction, sui_id, sit_id, principal_owner,
                frequency, payroll_platform, next_pay_date, next_process_date,
                semi_monthly_day_1, semi_monthly_day_2
            FROM payroll_schedules
            WHERE company_id = :company_id AND active = TRUE
            ORDER BY id
            """
            ),
            {"company_id": company["id"]},
        )
        .mappings()
        .all()
    )
    sales_tax_registrations = (
        db.execute(
            text(
                """
            SELECT id, jurisdiction, frequency, next_due_date
            FROM sales_tax_registrations
            WHERE company_id = :company_id AND active = TRUE
            ORDER BY id
            """
            ),
            {"company_id": company["id"]},
        )
        .mappings()
        .all()
    )

    return {
        "id": company["id"],
        "name": company["name"],
        "ein": company["ein"],
        "payroll_schedules": [dict(schedule) for schedule in payroll_schedules],
        "sales_tax_registrations": [dict(registration) for registration in sales_tax_registrations],
    }


def get_company_or_404(db: Session, company_id: int) -> dict:
    company = (
        db.execute(
            text("SELECT id, name, ein FROM companies WHERE id = :company_id"),
            {"company_id": company_id},
        )
        .mappings()
        .first()
    )
    if company is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return build_company(db, company)


def ensure_unique_ein(db: Session, ein: str, company_id: int | None = None) -> None:
    sql = "SELECT id FROM companies WHERE ein = :ein"
    params: dict[str, object] = {"ein": ein.strip()}
    if company_id is not None:
        sql += " AND id != :company_id"
        params["company_id"] = company_id
    if db.execute(text(sql), params).first() is not None:
        raise HTTPException(status_code=409, detail="A client with this EIN already exists")


def normalized_text(value: str) -> str:
    return value.strip()


def reconcile_payroll_schedules(db: Session, company_id: int, schedules) -> None:
    active_ids = set(
        db.execute(
            text(
                "SELECT id FROM payroll_schedules WHERE company_id = :company_id AND active = TRUE"
            ),
            {"company_id": company_id},
        ).scalars()
    )
    supplied_ids = [schedule.id for schedule in schedules if schedule.id is not None]
    if len(supplied_ids) != len(set(supplied_ids)):
        raise HTTPException(status_code=422, detail="Duplicate Payroll Schedule ID")
    if not set(supplied_ids).issubset(active_ids):
        raise HTTPException(status_code=422, detail="Invalid Payroll Schedule ID")

    for schedule in schedules:
        values = {
            "company_id": company_id,
            "label": normalized_text(schedule.label),
            "jurisdiction": normalized_text(schedule.jurisdiction),
            "sui_id": normalized_text(schedule.sui_id) if schedule.sui_id else None,
            "sit_id": normalized_text(schedule.sit_id) if schedule.sit_id else None,
            "principal_owner": (
                normalized_text(schedule.principal_owner) if schedule.principal_owner else None
            ),
            "frequency": schedule.frequency,
            "payroll_platform": normalized_text(schedule.payroll_platform),
            "next_pay_date": schedule.next_pay_date,
            "next_process_date": schedule.next_process_date,
            "semi_monthly_day_1": schedule.semi_monthly_day_1,
            "semi_monthly_day_2": schedule.semi_monthly_day_2,
        }
        if schedule.id is None:
            db.execute(
                text(
                    """
                    INSERT INTO payroll_schedules (
                        company_id, label, jurisdiction, sui_id, sit_id, principal_owner,
                        frequency, payroll_platform, next_pay_date, next_process_date,
                        semi_monthly_day_1, semi_monthly_day_2, active
                    ) VALUES (
                        :company_id, :label, :jurisdiction, :sui_id, :sit_id, :principal_owner,
                        :frequency, :payroll_platform, :next_pay_date, :next_process_date,
                        :semi_monthly_day_1, :semi_monthly_day_2, TRUE
                    )
                    """
                ),
                values,
            )
        else:
            db.execute(
                text(
                    """
                    UPDATE payroll_schedules
                    SET label = :label,
                        jurisdiction = :jurisdiction,
                        sui_id = :sui_id,
                        sit_id = :sit_id,
                        principal_owner = :principal_owner,
                        frequency = :frequency,
                        payroll_platform = :payroll_platform,
                        next_pay_date = :next_pay_date,
                        next_process_date = :next_process_date,
                        semi_monthly_day_1 = :semi_monthly_day_1,
                        semi_monthly_day_2 = :semi_monthly_day_2
                    WHERE id = :schedule_id AND company_id = :company_id AND active = TRUE
                    """
                ),
                {**values, "schedule_id": schedule.id},
            )

    for schedule_id in active_ids - set(supplied_ids):
        db.execute(
            text("UPDATE payroll_schedules SET active = FALSE WHERE id = :schedule_id"),
            {"schedule_id": schedule_id},
        )


def reconcile_sales_tax_registrations(db: Session, company_id: int, registrations) -> None:
    active_ids = set(
        db.execute(
            text(
                "SELECT id FROM sales_tax_registrations "
                "WHERE company_id = :company_id AND active = TRUE"
            ),
            {"company_id": company_id},
        ).scalars()
    )
    supplied_ids = [
        registration.id for registration in registrations if registration.id is not None
    ]
    if len(supplied_ids) != len(set(supplied_ids)):
        raise HTTPException(status_code=422, detail="Duplicate Sales Tax Registration ID")
    if not set(supplied_ids).issubset(active_ids):
        raise HTTPException(status_code=422, detail="Invalid Sales Tax Registration ID")

    for registration in registrations:
        values = {
            "company_id": company_id,
            "jurisdiction": normalized_text(registration.jurisdiction),
            "frequency": registration.frequency,
            "next_due_date": registration.next_due_date,
        }
        if registration.id is None:
            db.execute(
                text(
                    """
                    INSERT INTO sales_tax_registrations (
                        company_id, jurisdiction, frequency, next_due_date, active
                    ) VALUES (
                        :company_id, :jurisdiction, :frequency, :next_due_date, TRUE
                    )
                    """
                ),
                values,
            )
        else:
            db.execute(
                text(
                    """
                    UPDATE sales_tax_registrations
                    SET jurisdiction = :jurisdiction,
                        frequency = :frequency,
                        next_due_date = :next_due_date
                    WHERE id = :registration_id AND company_id = :company_id AND active = TRUE
                    """
                ),
                {**values, "registration_id": registration.id},
            )

    for registration_id in active_ids - set(supplied_ids):
        db.execute(
            text("UPDATE sales_tax_registrations SET active = FALSE WHERE id = :registration_id"),
            {"registration_id": registration_id},
        )


@router.patch("/tasks/{task_id}")
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.status not in {"pending", "in_progress", "completed"}:
        raise HTTPException(status_code=422, detail="Invalid status")
    result = db.execute(
        text("UPDATE tasks SET status = :status WHERE id = :task_id"),
        {"status": payload.status, "task_id": task_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    db.commit()
    return {"id": task_id, "status": payload.status}


@router.get("/tasks")
def list_tasks(week_start: date, week_end: date, db: Session = Depends(get_db)):
    ensure_tasks_until(db, week_end)
    statement = text(
        """
        SELECT
            tasks.id,
            companies.name AS company_name,
            tasks.task_type,
            payroll_schedules.label AS source_label,
            COALESCE(
                payroll_schedules.jurisdiction,
                sales_tax_registrations.jurisdiction
            ) AS source_jurisdiction,
            tasks.process_date,
            tasks.pay_date,
            tasks.due_date,
            tasks.status
        FROM tasks
        JOIN companies ON tasks.company_id = companies.id
        LEFT JOIN payroll_schedules ON tasks.payroll_schedule_id = payroll_schedules.id
        LEFT JOIN sales_tax_registrations
            ON tasks.sales_tax_registration_id = sales_tax_registrations.id
        WHERE
            (tasks.task_type = 'payroll' AND tasks.process_date BETWEEN :week_start AND :week_end)
            OR
            (tasks.task_type = 'sales_tax' AND tasks.due_date BETWEEN :week_start AND :week_end)
        ORDER BY COALESCE(tasks.process_date, tasks.due_date), tasks.id
        """
    )
    return (
        db.execute(
            statement,
            {"week_start": week_start, "week_end": week_end},
        )
        .mappings()
        .all()
    )


@router.get("/clients", response_model=list[CompanyRead])
def list_clients(_admin: None = Depends(require_admin), db: Session = Depends(get_db)):
    companies = db.execute(text("SELECT id, name, ein FROM companies ORDER BY name")).mappings()
    return [build_company(db, company) for company in companies]


@router.get("/clients/{company_id}", response_model=CompanyRead)
def get_client(
    company_id: int,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return get_company_or_404(db, company_id)


@router.post("/clients", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: CompanyInput,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_unique_ein(db, payload.ein)
    if any(schedule.id is not None for schedule in payload.payroll_schedules) or any(
        registration.id is not None for registration in payload.sales_tax_registrations
    ):
        raise HTTPException(status_code=422, detail="New configurations cannot include IDs")

    company_id = db.execute(
        insert(Company)
        .values(name=payload.name.strip(), ein=payload.ein.strip())
        .returning(Company.id)
    ).scalar_one()
    reconcile_payroll_schedules(db, company_id, payload.payroll_schedules)
    reconcile_sales_tax_registrations(db, company_id, payload.sales_tax_registrations)
    db.commit()
    return get_company_or_404(db, company_id)


@router.put("/clients/{company_id}", response_model=CompanyRead)
def update_client(
    company_id: int,
    payload: CompanyInput,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    get_company_or_404(db, company_id)
    ensure_unique_ein(db, payload.ein, company_id)
    db.execute(
        text("UPDATE companies SET name = :name, ein = :ein WHERE id = :company_id"),
        {"name": payload.name.strip(), "ein": payload.ein.strip(), "company_id": company_id},
    )
    reconcile_payroll_schedules(db, company_id, payload.payroll_schedules)
    reconcile_sales_tax_registrations(db, company_id, payload.sales_tax_registrations)
    db.commit()
    return get_company_or_404(db, company_id)


@router.delete("/clients/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    company_id: int,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    get_company_or_404(db, company_id)
    params = {"company_id": company_id}
    db.execute(text("DELETE FROM tasks WHERE company_id = :company_id"), params)
    db.execute(text("DELETE FROM payroll_schedules WHERE company_id = :company_id"), params)
    db.execute(text("DELETE FROM sales_tax_registrations WHERE company_id = :company_id"), params)
    db.execute(text("DELETE FROM payroll_profiles WHERE company_id = :company_id"), params)
    db.execute(text("DELETE FROM sales_tax_profiles WHERE company_id = :company_id"), params)
    db.execute(text("DELETE FROM companies WHERE id = :company_id"), params)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
