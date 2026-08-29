import calendar
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.task_generation import parse_date
from app.task_queries import get_tasks_for_range

NAVY = colors.HexColor("#0E1E35")
GOLD = colors.HexColor("#E9C34A")
WARM_WHITE = colors.HexColor("#F4F4F1")
ROW_RULE = colors.HexColor("#D6D9DD")
BODY_TEXT = colors.HexColor("#1C2735")


@dataclass(frozen=True)
class PrintableTask:
    operational_date: date
    client: str
    task: str
    jurisdiction: str
    schedule: str
    pay_date: date | None


def month_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def prepare_monthly_tasks(db: Session, year: int, month: int) -> list[PrintableTask]:
    month_start, month_end = month_bounds(year, month)
    rows = get_tasks_for_range(db, month_start, month_end)
    tasks = [
        PrintableTask(
            operational_date=parse_date(
                row["process_date"] if row["task_type"] == "payroll" else row["due_date"]
            ),
            client=row["company_name"],
            task="Payroll" if row["task_type"] == "payroll" else "Sales Tax",
            jurisdiction=row["source_jurisdiction"],
            schedule=row["source_label"] if row["task_type"] == "payroll" else "—",
            pay_date=parse_date(row["pay_date"])
            if row["task_type"] == "payroll" and row["pay_date"]
            else None,
        )
        for row in rows
    ]
    return sorted(
        tasks,
        key=lambda task: (
            task.operational_date,
            task.client.casefold(),
            task.task,
            task.schedule.casefold(),
            task.jurisdiction.casefold(),
        ),
    )


def _draw_page_number(canvas, document) -> None:
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#5F6874"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(landscape(letter)[0] - 0.45 * inch, 0.28 * inch, f"Page {document.page}")
    canvas.restoreState()


def _cell(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value)), style)


def render_monthly_pdf(tasks: list[PrintableTask], year: int, month: int) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(letter),
        rightMargin=0.45 * inch,
        leftMargin=0.45 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.42 * inch,
        title=f"Monthly Task Schedule - {year:04d}-{month:02d}",
        author="Task Tracker",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ScheduleTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=NAVY,
        alignment=0,
        spaceAfter=2,
    )
    month_style = ParagraphStyle(
        "ScheduleMonth",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=BODY_TEXT,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        textColor=BODY_TEXT,
    )
    date_style = ParagraphStyle("DateCell", parent=cell_style, fontName="Helvetica-Bold")
    right_style = ParagraphStyle("RightCell", parent=cell_style, alignment=TA_RIGHT)
    month_label = date(year, month, 1).strftime("%B %Y")
    story = [
        Paragraph("Monthly Task Schedule", title_style),
        Paragraph(month_label, month_style),
        Spacer(1, 7),
        Table(
            [[""]],
            colWidths=[10.1 * inch],
            rowHeights=[2],
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), GOLD)]),
        ),
        Spacer(1, 9),
    ]

    headers = ["Operational Date", "Client", "Task", "Jurisdiction", "Schedule", "Pay Date"]
    data: list[list[object]] = [headers]
    for task in tasks:
        data.append(
            [
                _cell(task.operational_date.strftime("%b %d, %Y"), date_style),
                _cell(task.client, cell_style),
                _cell(task.task, cell_style),
                _cell(task.jurisdiction, cell_style),
                _cell(task.schedule, cell_style),
                _cell(task.pay_date.strftime("%b %d, %Y") if task.pay_date else "—", right_style),
            ]
        )

    if not tasks:
        data.append(
            [Paragraph("No tasks scheduled for this month.", cell_style), "", "", "", "", ""]
        )

    table = Table(
        data,
        repeatRows=1,
        colWidths=[1.25 * inch, 2.35 * inch, 1.0 * inch, 1.05 * inch, 2.7 * inch, 1.25 * inch],
        hAlign="LEFT",
    )
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WARM_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LINEBELOW", (0, 1), (-1, -1), 0.45, ROW_RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if not tasks:
        table_style.append(("SPAN", (0, 1), (-1, 1)))
    table.setStyle(TableStyle(table_style))
    story.append(table)
    document.build(story, onFirstPage=_draw_page_number, onLaterPages=_draw_page_number)
    return output.getvalue()
