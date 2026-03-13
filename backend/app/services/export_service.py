"""
Excel export service - generates summary request (Заявка на питание) in Excel format,
matching the real template structure.
"""
import os
import logging
from datetime import date, datetime
from pathlib import Path

import xlsxwriter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import SummaryRow, SchoolClass

logger = logging.getLogger(__name__)

# Price constants from real file (Row 4)
PRICES = {
    "parent_breakfast": 70.10,
    "parent_lunch": 87.10,
    "parent_lunch_shved": 137.00,
    "benefit_breakfast": 70.10,
    "benefit_lunch": 87.10,
    "free_breakfast_1_4": "78,68 / 70,10",
    "free_lunch": 87.10,
    "multichild": 91.52,
    "sozvezdie": 70.10,
    "mobilized": "110,17 / 219,66",
    "ovz": "188,85 / 157,20",
    "sozvezdie_ovz": "188,85 / 157,20",
}


def export_summary_for_date(db: Session, meal_date: date) -> str:
    """Export summary request for a specific date as .xlsx file."""
    rows = (
        db.query(SummaryRow, SchoolClass)
        .join(SchoolClass, SummaryRow.class_id == SchoolClass.id)
        .filter(SummaryRow.meal_date == meal_date)
        .order_by(SchoolClass.grade, SchoolClass.letter)
        .all()
    )

    filename = f"Заявка_на_питание_{meal_date.strftime('%d.%m.%Y')}.xlsx"
    filepath = os.path.join(settings.EXPORT_DIR, filename)

    wb = xlsxwriter.Workbook(filepath)
    ws = wb.add_worksheet(meal_date.strftime("%d.%m"))

    # Formats
    header_fmt = wb.add_format({
        "bold": True, "border": 1, "text_wrap": True, "valign": "vcenter", "align": "center",
        "font_size": 9,
    })
    data_fmt = wb.add_format({"border": 1, "font_size": 9, "align": "center", "valign": "vcenter"})
    text_fmt = wb.add_format({"border": 1, "font_size": 9, "valign": "vcenter"})
    total_fmt = wb.add_format({
        "bold": True, "border": 1, "font_size": 9, "align": "center", "valign": "vcenter",
        "bg_color": "#D9E1F2",
    })
    title_fmt = wb.add_format({"bold": True, "font_size": 11})
    price_fmt = wb.add_format({"border": 1, "font_size": 8, "align": "center", "valign": "vcenter", "italic": True})

    # Column widths
    col_widths = [5, 6, 22, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 15]
    for i, w in enumerate(col_widths):
        ws.set_column(i, i, w)

    # Title
    ws.merge_range(0, 0, 0, 21, "Заявка на выдачу питания обучающимся (по классам)", title_fmt)
    ws.write(1, 0, meal_date.strftime("%d.%m.%Y"))

    # Headers Row 2
    headers_r2 = [
        (0, "№ п/п"), (1, "Класс"), (2, "ФИО кл.руководителя"),
        (3, "Кол-во детей\nв классе"), (4, "Кол-во\nпитающихся"),
        (5, "Родительская плата"), (8, "Льготное питание"),
        (10, "Бесплатно питание"), (12, "Многод\nсемьи"),
        (13, "Созвез-\nдие"), (14, "Мобилизован."),
        (16, "ОВЗ"), (18, "Созвездие\nОВЗ"),
        (20, "ИТОГО\nзавтраков"), (21, "ИТОГО\nобедов"), (22, "ПРИМЕЧАНИЕ"),
    ]
    for c, text in headers_r2:
        ws.write(2, c, text, header_fmt)
    ws.merge_range(2, 5, 2, 7, "Родительская плата", header_fmt)
    ws.merge_range(2, 8, 2, 9, "Льготное питание", header_fmt)
    ws.merge_range(2, 10, 2, 11, "Бесплатно питание", header_fmt)
    ws.merge_range(2, 14, 2, 15, "Мобилизован.", header_fmt)
    ws.merge_range(2, 16, 2, 17, "ОВЗ", header_fmt)
    ws.merge_range(2, 18, 2, 19, "Созвездие ОВЗ", header_fmt)

    # Sub-headers Row 3
    sub_headers = {
        5: "завтрак", 6: "обед", 7: "обед/шв",
        8: "завтрак", 9: "обед",
        10: "завтрак", 11: "обед",
        12: "завтрак", 13: "завтрак",
        14: "завтрак/обед", 15: "",
        16: "завтрак/обед", 17: "",
        18: "завтрак/обед", 19: "",
    }
    for c, text in sub_headers.items():
        ws.write(3, c, text, header_fmt)

    # Prices Row 4
    prices = {
        5: 70.10, 6: 87.10, 7: 137.00,
        8: 70.10, 9: 87.10,
        10: "78,68 / 70,10", 11: 87.10,
        12: 91.52, 13: 70.10,
        14: "110,17 / 219,66",
        16: "188,85 / 157,20",
        18: "188,85 / 157,20",
    }
    for c, val in prices.items():
        ws.write(4, c, val, price_fmt)

    # Data rows
    r = 5
    num = 1
    elementary_start = r
    elementary_rows = []
    middle_rows = []

    for summary, sc in rows:
        if sc.grade <= 4:
            elementary_rows.append((summary, sc))
        else:
            middle_rows.append((summary, sc))

    def write_row(ws, r, num, summary, sc):
        ws.write(r, 0, num, data_fmt)
        ws.write(r, 1, sc.name, text_fmt)
        ws.write(r, 2, summary.teacher_name, text_fmt)
        ws.write(r, 3, summary.student_count, data_fmt)
        ws.write(r, 4, summary.eating_count, data_fmt)
        ws.write(r, 5, summary.parent_breakfast or "", data_fmt)
        ws.write(r, 6, summary.parent_lunch or "", data_fmt)
        ws.write(r, 7, summary.parent_lunch_shved or "", data_fmt)
        ws.write(r, 8, summary.benefit_breakfast or "", data_fmt)
        ws.write(r, 9, summary.benefit_lunch or "", data_fmt)
        ws.write(r, 10, summary.free_breakfast or "", data_fmt)
        ws.write(r, 11, summary.free_lunch or "", data_fmt)
        ws.write(r, 12, summary.multichild_breakfast or "", data_fmt)
        ws.write(r, 13, summary.sozvezdie_breakfast or "", data_fmt)
        ws.write(r, 14, summary.mobilized_breakfast_lunch or "", data_fmt)
        ws.write(r, 15, summary.mobilized_count or "", data_fmt)
        ws.write(r, 16, summary.ovz_breakfast_lunch or "", data_fmt)
        ws.write(r, 17, summary.ovz_count or "", data_fmt)
        ws.write(r, 18, summary.sozvezdie_ovz_breakfast_lunch or "", data_fmt)
        ws.write(r, 19, summary.sozvezdie_ovz_count or "", data_fmt)
        ws.write(r, 20, summary.total_breakfasts, data_fmt)
        ws.write(r, 21, summary.total_lunches, data_fmt)
        ws.write(r, 22, summary.notes or "", text_fmt)

    # Elementary
    for summary, sc in elementary_rows:
        write_row(ws, r, num, summary, sc)
        r += 1
        num += 1

    # Elementary subtotal
    if elementary_rows:
        _write_subtotal(ws, r, elementary_rows, total_fmt)
        r += 1

    # Middle/senior
    for summary, sc in middle_rows:
        write_row(ws, r, num, summary, sc)
        r += 1
        num += 1

    # Middle subtotal
    if middle_rows:
        _write_subtotal(ws, r, middle_rows, total_fmt)
        r += 1

    # Grand total student count
    all_rows = elementary_rows + middle_rows
    grand_total = sum(s.student_count for s, _ in all_rows)
    ws.write(r + 1, 3, grand_total, total_fmt)

    # Signature
    ws.write(r + 3, 2, 'Ответственный за питание МБУ "Школа № 71" ____________________Н.В.Краснова')

    wb.close()
    logger.info(f"Exported summary to {filepath}")
    return filepath


def _write_subtotal(ws, r, rows_data, fmt):
    totals = {}
    fields = [
        "student_count", "eating_count", "parent_breakfast", "parent_lunch",
        "parent_lunch_shved", "benefit_breakfast", "benefit_lunch",
        "free_breakfast", "free_lunch", "multichild_breakfast",
        "sozvezdie_breakfast", "mobilized_breakfast_lunch", "mobilized_count",
        "ovz_breakfast_lunch", "ovz_count", "sozvezdie_ovz_breakfast_lunch",
        "sozvezdie_ovz_count", "total_breakfasts", "total_lunches",
    ]
    col_map = {
        "student_count": 3, "eating_count": 4, "parent_breakfast": 5,
        "parent_lunch": 6, "parent_lunch_shved": 7,
        "benefit_breakfast": 8, "benefit_lunch": 9,
        "free_breakfast": 10, "free_lunch": 11,
        "multichild_breakfast": 12, "sozvezdie_breakfast": 13,
        "mobilized_breakfast_lunch": 14, "mobilized_count": 15,
        "ovz_breakfast_lunch": 16, "ovz_count": 17,
        "sozvezdie_ovz_breakfast_lunch": 18, "sozvezdie_ovz_count": 19,
        "total_breakfasts": 20, "total_lunches": 21,
    }
    for f in fields:
        totals[f] = sum(getattr(s, f, 0) or 0 for s, _ in rows_data)
    for f, col in col_map.items():
        ws.write(r, col, totals[f], fmt)


def export_summary_for_month(db: Session, year: int, month: int) -> str:
    """Export all summary dates for a given month into a multi-sheet workbook."""
    from sqlalchemy import extract

    dates = (
        db.query(SummaryRow.meal_date)
        .filter(
            extract("year", SummaryRow.meal_date) == year,
            extract("month", SummaryRow.meal_date) == month,
        )
        .distinct()
        .order_by(SummaryRow.meal_date)
        .all()
    )

    filename = f"Заявка_на_питание_{month:02d}.{year}.xlsx"
    filepath = os.path.join(settings.EXPORT_DIR, filename)

    wb = xlsxwriter.Workbook(filepath)

    for (d,) in dates:
        rows = (
            db.query(SummaryRow, SchoolClass)
            .join(SchoolClass, SummaryRow.class_id == SchoolClass.id)
            .filter(SummaryRow.meal_date == d)
            .order_by(SchoolClass.grade, SchoolClass.letter)
            .all()
        )
        if not rows:
            continue

        ws = wb.add_worksheet(d.strftime("%d.%m"))

        header_fmt = wb.add_format({
            "bold": True, "border": 1, "text_wrap": True, "valign": "vcenter",
            "align": "center", "font_size": 9,
        })
        data_fmt = wb.add_format({"border": 1, "font_size": 9, "align": "center", "valign": "vcenter"})
        text_fmt = wb.add_format({"border": 1, "font_size": 9, "valign": "vcenter"})
        total_fmt = wb.add_format({
            "bold": True, "border": 1, "font_size": 9, "align": "center",
            "valign": "vcenter", "bg_color": "#D9E1F2",
        })
        title_fmt = wb.add_format({"bold": True, "font_size": 11})

        col_widths = [5, 6, 22, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 15]
        for i, w in enumerate(col_widths):
            ws.set_column(i, i, w)

        ws.merge_range(0, 0, 0, 21, "Заявка на выдачу питания обучающимся (по классам)", title_fmt)
        ws.write(1, 0, d.strftime("%d.%m.%Y"))

        headers = [
            "№ п/п", "Класс", "ФИО кл.руководителя", "Кол-во детей\nв классе",
            "Кол-во\nпитающихся", "завтрак", "обед", "обед/шв",
            "завтрак", "обед", "завтрак", "обед", "завтрак",
            "завтрак", "завтрак/обед", "", "завтрак/обед", "",
            "завтрак/обед", "", "ИТОГО\nзавтраков", "ИТОГО\nобедов", "ПРИМЕЧАНИЕ",
        ]
        for c, h in enumerate(headers):
            ws.write(2, c, h, header_fmt)

        r = 3
        num = 1
        for summary, sc in rows:
            ws.write(r, 0, num, data_fmt)
            ws.write(r, 1, sc.name, text_fmt)
            ws.write(r, 2, summary.teacher_name, text_fmt)
            ws.write(r, 3, summary.student_count, data_fmt)
            ws.write(r, 4, summary.eating_count, data_fmt)
            ws.write(r, 5, summary.parent_breakfast or "", data_fmt)
            ws.write(r, 6, summary.parent_lunch or "", data_fmt)
            ws.write(r, 7, summary.parent_lunch_shved or "", data_fmt)
            ws.write(r, 8, summary.benefit_breakfast or "", data_fmt)
            ws.write(r, 9, summary.benefit_lunch or "", data_fmt)
            ws.write(r, 10, summary.free_breakfast or "", data_fmt)
            ws.write(r, 11, summary.free_lunch or "", data_fmt)
            ws.write(r, 12, summary.multichild_breakfast or "", data_fmt)
            ws.write(r, 13, summary.sozvezdie_breakfast or "", data_fmt)
            ws.write(r, 14, summary.mobilized_breakfast_lunch or "", data_fmt)
            ws.write(r, 15, summary.mobilized_count or "", data_fmt)
            ws.write(r, 16, summary.ovz_breakfast_lunch or "", data_fmt)
            ws.write(r, 17, summary.ovz_count or "", data_fmt)
            ws.write(r, 18, summary.sozvezdie_ovz_breakfast_lunch or "", data_fmt)
            ws.write(r, 19, summary.sozvezdie_ovz_count or "", data_fmt)
            ws.write(r, 20, summary.total_breakfasts, data_fmt)
            ws.write(r, 21, summary.total_lunches, data_fmt)
            ws.write(r, 22, summary.notes or "", text_fmt)
            r += 1
            num += 1

    wb.close()
    logger.info(f"Exported monthly summary to {filepath}")
    return filepath
