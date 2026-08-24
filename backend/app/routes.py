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

COMPANY_SELECT = """
SELECT
    c.id,
    c.name,
    c.ein,
    p.id AS payroll_id,
    p.sui_id,
    p.sit_id,
    p.principal_owner,
    p.frequency AS payroll_frequency,
    p.payroll_platform,
    p.next_pay_date,
    p.next_process_date,
    p.semi_monthly_day_1,
    p.semi_monthly_day_2,
    s.id AS sales_tax_id,
    s.frequency AS sales_tax_frequency,
    s.next_due_date AS sales_tax_next_due_date
FROM companies AS c
LEFT JOIN payroll_profiles AS p ON p.company_id = c.id
LEFT JOIN sales_tax_profiles AS s ON s.company_id = c.id
"""


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


def row_to_company(row) -> dict:
    payroll = None
    if row.payroll_id is not None:
        payroll = {
            "id": row.payroll_id,
            "sui_id": row.sui_id,
            "sit_id": row.sit_id,
            "principal_owner": row.principal_owner,
            "frequency": row.payroll_frequency,
            "payroll_platform": row.payroll_platform,
            "next_pay_date": row.next_pay_date,
            "next_process_date": row.next_process_date,
            "semi_monthly_day_1": row.semi_monthly_day_1,
            "semi_monthly_day_2": row.semi_monthly_day_2,
        }

    sales_tax = None
    if row.sales_tax_id is not None:
        sales_tax = {
            "id": row.sales_tax_id,
            "frequency": row.sales_tax_frequency,
            "next_due_date": row.sales_tax_next_due_date,
        }

    return {
        "id": row.id,
        "name": row.name,
        "ein": row.ein,
        "payroll": payroll,
        "sales_tax": sales_tax,
    }


def get_company_or_404(db: Session, company_id: int) -> dict:
    sql = text(COMPANY_SELECT + " WHERE c.id = :company_id")
    row = db.execute(sql, {"company_id": company_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return row_to_company(row)


def ensure_unique_ein(db: Session, ein: str, company_id: int | None = None) -> None:
    sql = "SELECT id FROM companies WHERE ein = :ein"
    params: dict[str, object] = {"ein": ein.strip()}

    if company_id is not None:
        sql += " AND id != :company_id"
        params["company_id"] = company_id

    existing = db.execute(text(sql), params).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A client with this EIN already exists")


def insert_payroll_profile(db: Session, company_id: int, payroll) -> None:
    db.execute(
        text(
            """
            INSERT INTO payroll_profiles (
                company_id,
                sui_id,
                sit_id,
                principal_owner,
                frequency,
                payroll_platform,
                next_pay_date,
                next_process_date,
                semi_monthly_day_1,
                semi_monthly_day_2
            ) VALUES (
                :company_id,
                :sui_id,
                :sit_id,
                :principal_owner,
                :frequency,
                :payroll_platform,
                :next_pay_date,
                :next_process_date,
                :semi_monthly_day_1,
                :semi_monthly_day_2
            )
            """
        ),
        {
            "company_id": company_id,
            "sui_id": payroll.sui_id or None,
            "sit_id": payroll.sit_id or None,
            "principal_owner": payroll.principal_owner or None,
            "frequency": payroll.frequency,
            "payroll_platform": payroll.payroll_platform.strip(),
            "next_pay_date": payroll.next_pay_date,
            "next_process_date": payroll.next_process_date,
            "semi_monthly_day_1": payroll.semi_monthly_day_1,
            "semi_monthly_day_2": payroll.semi_monthly_day_2,
        },
    )


@router.patch("/tasks/{task_id}")
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    allowed_statuses = {"pending", "in_progress", "completed"}

    if payload.status not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Invalid status")

    result = db.execute(
        text(
            """
            UPDATE tasks
            SET status = :status
            WHERE id = :task_id
            """
        ),
        {"status": payload.status, "task_id": task_id},
    )

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")

    db.commit()
    return {"id": task_id, "status": payload.status}


@router.get("/tasks")
def list_tasks(
    week_start: date,
    week_end: date,
    db: Session = Depends(get_db),
):
    ensure_tasks_until(db, week_end)

    statement = text(
        """
        SELECT
            tasks.id,
            companies.name AS company_name,
            tasks.task_type,
            tasks.process_date,
            tasks.pay_date,
            tasks.due_date,
            tasks.status
        FROM tasks
        JOIN companies
            ON tasks.company_id = companies.id
        WHERE
            (
                tasks.task_type = 'payroll'
                AND tasks.process_date BETWEEN :week_start AND :week_end
            )
            OR
            (
                tasks.task_type = 'sales_tax'
                AND tasks.due_date BETWEEN :week_start AND :week_end
            )
        ORDER BY COALESCE(tasks.process_date, tasks.due_date)
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
def list_clients(
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sql = text(COMPANY_SELECT + " ORDER BY c.name")
    rows = db.execute(sql).mappings().all()
    return [row_to_company(row) for row in rows]


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

    company_id = db.execute(
        insert(Company)
        .values(name=payload.name.strip(), ein=payload.ein.strip())
        .returning(Company.id)
    ).scalar_one()

    if payload.payroll is not None:
        insert_payroll_profile(db, company_id, payload.payroll)

    if payload.sales_tax is not None:
        db.execute(
            text(
                """
                INSERT INTO sales_tax_profiles (company_id, frequency, next_due_date)
                VALUES (:company_id, :frequency, :next_due_date)
                """
            ),
            {
                "company_id": company_id,
                "frequency": payload.sales_tax.frequency,
                "next_due_date": payload.sales_tax.next_due_date,
            },
        )

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
        {
            "name": payload.name.strip(),
            "ein": payload.ein.strip(),
            "company_id": company_id,
        },
    )

    db.execute(
        text("DELETE FROM payroll_profiles WHERE company_id = :company_id"),
        {"company_id": company_id},
    )
    if payload.payroll is not None:
        insert_payroll_profile(db, company_id, payload.payroll)

    db.execute(
        text("DELETE FROM sales_tax_profiles WHERE company_id = :company_id"),
        {"company_id": company_id},
    )
    if payload.sales_tax is not None:
        db.execute(
            text(
                """
                INSERT INTO sales_tax_profiles (company_id, frequency, next_due_date)
                VALUES (:company_id, :frequency, :next_due_date)
                """
            ),
            {
                "company_id": company_id,
                "frequency": payload.sales_tax.frequency,
                "next_due_date": payload.sales_tax.next_due_date,
            },
        )

    db.commit()
    return get_company_or_404(db, company_id)


@router.delete("/clients/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    company_id: int,
    _admin: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    get_company_or_404(db, company_id)

    db.execute(text("DELETE FROM tasks WHERE company_id = :company_id"), {"company_id": company_id})
    db.execute(
        text("DELETE FROM payroll_profiles WHERE company_id = :company_id"),
        {"company_id": company_id},
    )
    db.execute(
        text("DELETE FROM sales_tax_profiles WHERE company_id = :company_id"),
        {"company_id": company_id},
    )
    db.execute(text("DELETE FROM companies WHERE id = :company_id"), {"company_id": company_id})
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
