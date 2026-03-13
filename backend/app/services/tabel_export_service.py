"""
Export a class tabel to Excel in the exact original template format.

Template structure (from real file analysis):
  Row 3: ТАБЕЛЬ
  Row 5: учета питания обучающихся
  Row 7: за период DD.MM.YYYYг.
  Row 8: Учреждение    МБУ "Школа № 71"
  Row 9: Класс N "X"
  Row 11: headers: №, ФИО, льготы, Авангард, Любава, Всего завтраков, Всего обедов, Всего ШВЕДов
  Row 12: sub-headers: завтрак, обед, ШВ.стол (x2)
  Row 13: column numbers
  Row 14+: student data
"""
import os
import logging
from datetime import date

import xlsxwriter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    Student, StudentBenefit, BenefitType, SchoolClass,
    MealUpload, StudentMealRecord,
)

logger = logging.getLogger(__name__)


def export_tabel_to_excel(db: Session, class_id: int, meal_date: date) -> str:
    sc = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not sc:
        raise ValueError("Класс не найден")

    # Get records from current upload
    upload = (
        db.query(MealUpload)
        .filter(MealUpload.class_id == class_id, MealUpload.meal_date == meal_date, MealUpload.is_current == True)
        .first()
    )

    records = []
    if upload:
        records = (
            db.query(StudentMealRecord)
            .filter(StudentMealRecord.upload_id == upload.id)
            .order_by(StudentMealRecord.row_number)
            .all()
        )

    # If no upload, get students from roster
    if not records:
        students = (
            db.query(Student)
            .filter(Student.class_id == class_id, Student.is_active == True)
            .order_by(Student.full_name)
            .all()
        )
    else:
        students = None  # use records

    class_display = f'{sc.grade} "{sc.letter.upper()}"'
    filename = f"Табель_{sc.name}_{meal_date.strftime('%d.%m.%Y')}.xlsx"
    filepath = os.path.join(settings.EXPORT_DIR, filename)
    os.makedirs(settings.EXPORT_DIR, exist_ok=True)

    wb = xlsxwriter.Workbook(filepath)
    ws = wb.add_worksheet(meal_date.strftime("%d.%m"))

    # ── Formats ──
    title_fmt = wb.add_format({"bold": True, "font_size": 14, "align": "center"})
    subtitle_fmt = wb.add_format({"font_size": 11, "align": "center"})
    info_fmt = wb.add_format({"font_size": 11})
    header_fmt = wb.add_format({
        "bold": True, "border": 1, "text_wrap": True, "valign": "vcenter",
        "align": "center", "font_size": 9, "bg_color": "#D9E1F2",
    })
    subheader_fmt = wb.add_format({
        "border": 1, "text_wrap": True, "valign": "vcenter",
        "align": "center", "font_size": 9,
    })
    num_fmt = wb.add_format({"border": 1, "align": "center", "font_size": 9, "italic": True})
    data_fmt = wb.add_format({"border": 1, "font_size": 10, "align": "center", "valign": "vcenter"})
    name_fmt = wb.add_format({"border": 1, "font_size": 10, "valign": "vcenter"})
    total_fmt = wb.add_format({
        "bold": True, "border": 1, "font_size": 10, "align": "center",
        "valign": "vcenter", "bg_color": "#E2EFDA",
    })

    # ── Column widths ──
    ws.set_column(0, 0, 4)    # №
    ws.set_column(1, 1, 2)    # spacer
    ws.set_column(2, 10, 3)   # name (merged)
    ws.set_column(11, 14, 6)  # benefit + spacer
    ws.set_column(15, 17, 8)  # Авангард
    ws.set_column(18, 20, 8)  # Любава
    ws.set_column(21, 24, 5)  # Всего завтраков
    ws.set_column(25, 28, 5)  # Всего обедов
    ws.set_column(29, 32, 5)  # Всего ШВЕДов

    # ── Header section ──
    ws.merge_range(3, 2, 3, 20, "ТАБЕЛЬ", title_fmt)
    ws.merge_range(5, 2, 5, 20, "учета питания обучающихся", subtitle_fmt)
    ws.merge_range(7, 2, 7, 20, f'за период {meal_date.strftime("%d.%m.%Y")}г.', subtitle_fmt)
    ws.write(8, 2, "Учреждение", info_fmt)
    ws.merge_range(8, 10, 8, 20, 'МБУ "Школа № 71"', info_fmt)
    ws.merge_range(9, 2, 9, 10, f"Класс {class_display}", info_fmt)

    # ── Table headers (Row 11) ──
    row = 11
    ws.write(row, 0, "№\nп/п", header_fmt)
    ws.merge_range(row, 2, row, 10, "Фамилия, имя обучающегося", header_fmt)
    ws.write(row, 11, "Отметка о наличии\nльгот по оплате\nпитания*", header_fmt)
    ws.merge_range(row, 15, row, 17, "Авангард", header_fmt)
    ws.merge_range(row, 18, row, 20, "Любава", header_fmt)
    ws.merge_range(row, 21, row, 24, "Всего\nзавтраков", header_fmt)
    ws.merge_range(row, 25, row, 28, "Всего\nобедов", header_fmt)
    ws.merge_range(row, 29, row, 32, "Всего\nШВЕДов", header_fmt)

    # ── Sub-headers (Row 12) ──
    row = 12
    ws.write(row, 15, "завтрак", subheader_fmt)
    ws.write(row, 16, "обед", subheader_fmt)
    ws.write(row, 17, "ШВ.стол", subheader_fmt)
    ws.write(row, 18, "завтрак", subheader_fmt)
    ws.write(row, 19, "обед", subheader_fmt)
    ws.write(row, 20, "ШВ.стол", subheader_fmt)

    # ── Column numbers (Row 13) ──
    row = 13
    col_nums = {0: 1, 2: 2, 11: 3, 15: 4, 17: 5, 18: 7, 20: 8, 21: 25, 25: 26}
    for c, v in col_nums.items():
        ws.write(row, c, v, num_fmt)

    # ── Data rows (Row 14+) ──
    row = 14
    sum_av_bf = sum_av_lu = sum_av_shv = 0
    sum_ly_bf = sum_ly_lu = sum_ly_shv = 0
    sum_total_bf = sum_total_lu = sum_total_shv = 0

    if records:
        for i, rec in enumerate(records):
            ws.write(row, 0, i + 1, data_fmt)
            ws.merge_range(row, 2, row, 10, rec.student_name_raw, name_fmt)
            ws.write(row, 11, rec.benefit_raw or "", data_fmt)
            ws.write(row, 15, rec.avangard_breakfast or "", data_fmt)
            ws.write(row, 16, rec.avangard_lunch or "", data_fmt)
            ws.write(row, 17, rec.avangard_shved or "", data_fmt)
            ws.write(row, 18, rec.lyubava_breakfast or "", data_fmt)
            ws.write(row, 19, rec.lyubava_lunch or "", data_fmt)
            ws.write(row, 20, rec.lyubava_shved or "", data_fmt)
            ws.write(row, 21, rec.total_breakfasts, data_fmt)
            ws.write(row, 25, rec.total_lunches, data_fmt)
            ws.write(row, 29, rec.total_shved, data_fmt)

            sum_av_bf += rec.avangard_breakfast or 0
            sum_av_lu += rec.avangard_lunch or 0
            sum_av_shv += rec.avangard_shved or 0
            sum_ly_bf += rec.lyubava_breakfast or 0
            sum_ly_lu += rec.lyubava_lunch or 0
            sum_ly_shv += rec.lyubava_shved or 0
            sum_total_bf += rec.total_breakfasts or 0
            sum_total_lu += rec.total_lunches or 0
            sum_total_shv += rec.total_shved or 0
            row += 1
    elif students:
        for i, s in enumerate(students):
            benefit_code = _get_benefit_code(db, s.id)
            ws.write(row, 0, i + 1, data_fmt)
            ws.merge_range(row, 2, row, 10, s.full_name, name_fmt)
            ws.write(row, 11, benefit_code or "", data_fmt)
            ws.write(row, 15, "", data_fmt)
            ws.write(row, 16, "", data_fmt)
            ws.write(row, 17, "", data_fmt)
            ws.write(row, 18, "", data_fmt)
            ws.write(row, 19, "", data_fmt)
            ws.write(row, 20, "", data_fmt)
            ws.write(row, 21, 0, data_fmt)
            ws.write(row, 25, 0, data_fmt)
            ws.write(row, 29, 0, data_fmt)
            row += 1

    # ── Totals row ──
    ws.merge_range(row, 2, row, 10, "ИТОГО", total_fmt)
    ws.write(row, 15, sum_av_bf or "", total_fmt)
    ws.write(row, 16, sum_av_lu or "", total_fmt)
    ws.write(row, 17, sum_av_shv or "", total_fmt)
    ws.write(row, 18, sum_ly_bf or "", total_fmt)
    ws.write(row, 19, sum_ly_lu or "", total_fmt)
    ws.write(row, 20, sum_ly_shv or "", total_fmt)
    ws.write(row, 21, sum_total_bf, total_fmt)
    ws.write(row, 25, sum_total_lu, total_fmt)
    ws.write(row, 29, sum_total_shv, total_fmt)

    # ── Signature ──
    row += 3
    ws.merge_range(row, 2, row, 20, "Классный руководитель __________________ / __________________", info_fmt)

    wb.close()
    logger.info(f"Exported tabel to {filepath}")
    return filepath


def _get_benefit_code(db: Session, student_id: int) -> str | None:
    ab = (
        db.query(StudentBenefit)
        .filter(StudentBenefit.student_id == student_id, StudentBenefit.is_active == True)
        .first()
    )
    if ab:
        bt = db.query(BenefitType).filter(BenefitType.id == ab.benefit_type_id).first()
        return bt.code if bt else None
    return None
