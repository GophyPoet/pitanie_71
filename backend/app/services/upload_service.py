"""
Service that orchestrates the full upload pipeline:
1. Save file
2. Parse Excel
3. Create/update students
4. Save meal records
5. Update summary row
6. Run comparison
"""
import os
import logging
import shutil
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    User, SchoolClass, MealUpload, UploadStatus,
    Student, StudentBenefit, BenefitType,
    StudentMealRecord, SummaryRow,
    AuditLog, TeacherClassAssignment,
)
from app.services.excel_parser import parse_tabel_file, ParsedTabel
from app.services.comparison_service import compare_and_create_discrepancies

logger = logging.getLogger(__name__)


class UploadError(Exception):
    pass


def _find_or_create_class(db: Session, class_name: str, grade: int, letter: str) -> SchoolClass:
    sc = db.query(SchoolClass).filter(SchoolClass.name == class_name).first()
    if not sc:
        sc = SchoolClass(name=class_name, grade=grade, letter=letter)
        db.add(sc)
        db.flush()
    return sc


def _find_or_create_student(db: Session, name: str, class_id: int, benefit_raw: str | None, notes: str) -> Student:
    name_clean = name.strip()
    student = (
        db.query(Student)
        .filter(Student.full_name == name_clean, Student.class_id == class_id)
        .first()
    )
    if not student:
        student = Student(full_name=name_clean, class_id=class_id, notes=notes)
        db.add(student)
        db.flush()

    # Update benefit if present
    if benefit_raw:
        benefit_code = benefit_raw.strip().lower()
        bt = db.query(BenefitType).filter(
            func.lower(BenefitType.code) == benefit_code
        ).first()
        if bt:
            existing = (
                db.query(StudentBenefit)
                .filter(
                    StudentBenefit.student_id == student.id,
                    StudentBenefit.benefit_type_id == bt.id,
                    StudentBenefit.is_active == True,
                )
                .first()
            )
            if not existing:
                db.add(StudentBenefit(student_id=student.id, benefit_type_id=bt.id))

    return student


def _compute_summary_from_records(
    parsed: ParsedTabel, class_id: int, meal_date: date, upload_id: int, teacher_name: str, student_count: int,
) -> dict:
    """Compute summary row values from parsed student records."""
    eating = 0
    parent_bf = 0
    parent_lunch = 0
    parent_lunch_shved = 0
    free_bf = 0
    free_lunch = 0
    multichild = 0
    mobilized = 0
    mobilized_cnt = 0
    ovz = 0
    ovz_cnt = 0

    for s in parsed.students:
        has_meal = (
            s.total_breakfasts + s.total_lunches + s.total_shved +
            s.avangard_breakfast + s.avangard_lunch + s.avangard_shved +
            s.lyubava_breakfast + s.lyubava_lunch + s.lyubava_shved
        ) > 0
        if has_meal:
            eating += 1

        benefit = (s.benefit_raw or "").strip().lower()

        if benefit in ("сво",):
            mobilized_cnt += 1
            mobilized += s.total_breakfasts + s.total_lunches
        elif benefit in ("овз",):
            ovz_cnt += 1
            ovz += s.total_breakfasts + s.total_lunches
        elif benefit in ("мн", "мног.", "мног"):
            multichild += s.total_breakfasts
        elif benefit in ("б/к", "б/о"):
            # Бесплатно
            free_bf += s.total_breakfasts
            free_lunch += s.total_lunches
        else:
            # Parent-pay or no benefit
            if s.avangard_shved or s.lyubava_shved or s.total_shved:
                parent_lunch_shved += s.avangard_shved + s.lyubava_shved + s.total_shved
            parent_bf += s.avangard_breakfast + s.lyubava_breakfast
            parent_lunch += s.avangard_lunch + s.lyubava_lunch

    total_bf = sum(
        s.total_breakfasts if s.total_breakfasts else (s.avangard_breakfast + s.lyubava_breakfast)
        for s in parsed.students
    )
    total_lunch = sum(
        s.total_lunches if s.total_lunches else (s.avangard_lunch + s.lyubava_lunch)
        for s in parsed.students
    )

    return {
        "class_id": class_id,
        "meal_date": meal_date,
        "upload_id": upload_id,
        "teacher_name": teacher_name,
        "student_count": student_count,
        "eating_count": eating,
        "parent_breakfast": parent_bf,
        "parent_lunch": parent_lunch,
        "parent_lunch_shved": parent_lunch_shved,
        "free_breakfast": free_bf,
        "free_lunch": free_lunch,
        "multichild_breakfast": multichild,
        "mobilized_breakfast_lunch": mobilized,
        "mobilized_count": mobilized_cnt,
        "ovz_breakfast_lunch": ovz,
        "ovz_count": ovz_cnt,
        "total_breakfasts": total_bf,
        "total_lunches": total_lunch,
        "is_submitted": True,
        "submitted_at": datetime.utcnow(),
        "source": "import",
    }


def process_upload(
    db: Session,
    teacher: User,
    class_id: int,
    meal_date: date,
    file_path: str,
    original_filename: str,
) -> MealUpload:
    """Full upload processing pipeline."""

    # 1. Validate teacher has access to this class
    has_access = (
        teacher.role.value == "admin"
        or db.query(TeacherClassAssignment)
        .filter(
            TeacherClassAssignment.teacher_id == teacher.id,
            TeacherClassAssignment.class_id == class_id,
        )
        .first()
        is not None
    )
    if not has_access:
        raise UploadError("У вас нет доступа к этому классу")

    # 2. Mark previous uploads as non-current
    prev_uploads = (
        db.query(MealUpload)
        .filter(
            MealUpload.class_id == class_id,
            MealUpload.meal_date == meal_date,
            MealUpload.is_current == True,
        )
        .all()
    )
    max_version = 0
    for pu in prev_uploads:
        pu.is_current = False
        max_version = max(max_version, pu.version)

    # 3. Create upload record
    stored_name = f"{class_id}_{meal_date}_{max_version + 1}_{original_filename}"
    final_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    shutil.copy2(file_path, final_path)

    upload = MealUpload(
        teacher_id=teacher.id,
        class_id=class_id,
        meal_date=meal_date,
        month=meal_date.month,
        year=meal_date.year,
        original_filename=original_filename,
        stored_filename=stored_name,
        file_path=final_path,
        status=UploadStatus.PROCESSING,
        version=max_version + 1,
        is_current=True,
    )
    db.add(upload)
    db.flush()

    # 4. Parse
    try:
        parsed = parse_tabel_file(final_path)
    except Exception as e:
        upload.status = UploadStatus.ERROR
        upload.error_message = f"Ошибка парсинга: {str(e)}"
        db.flush()
        raise UploadError(f"Ошибка парсинга файла: {str(e)}")

    upload.sheet_name = parsed.sheet_name
    upload.parsed_class_name = parsed.class_name
    upload.parsed_date = parsed.period_text

    # 5. Validate parsed class matches expected
    if parsed.class_name:
        sc = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        if sc and parsed.class_name != sc.name:
            upload.error_message = (
                f"Внимание: класс в файле ({parsed.class_name}) "
                f"не совпадает с выбранным ({sc.name})"
            )

    if parsed.errors:
        upload.status = UploadStatus.ERROR
        upload.error_message = "; ".join(parsed.errors)
        db.flush()
        raise UploadError(upload.error_message)

    # 6. Save student records
    for ps in parsed.students:
        student = _find_or_create_student(db, ps.full_name, class_id, ps.benefit_raw, ps.notes)
        record = StudentMealRecord(
            upload_id=upload.id,
            student_id=student.id,
            student_name_raw=ps.full_name,
            row_number=ps.row_number,
            benefit_raw=ps.benefit_raw,
            avangard_breakfast=ps.avangard_breakfast,
            avangard_lunch=ps.avangard_lunch,
            avangard_shved=ps.avangard_shved,
            lyubava_breakfast=ps.lyubava_breakfast,
            lyubava_lunch=ps.lyubava_lunch,
            lyubava_shved=ps.lyubava_shved,
            total_breakfasts=ps.total_breakfasts,
            total_lunches=ps.total_lunches,
            total_shved=ps.total_shved,
        )
        db.add(record)

    # 7. Update/create summary row
    sc = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    teacher_name = teacher.full_name
    student_count = sc.student_count if sc else len(parsed.students)

    summary_data = _compute_summary_from_records(
        parsed, class_id, meal_date, upload.id, teacher_name, student_count,
    )

    existing_summary = (
        db.query(SummaryRow)
        .filter(SummaryRow.class_id == class_id, SummaryRow.meal_date == meal_date)
        .first()
    )
    if existing_summary:
        for k, v in summary_data.items():
            setattr(existing_summary, k, v)
    else:
        db.add(SummaryRow(**summary_data))

    db.flush()

    # 8. Run comparison
    try:
        compare_and_create_discrepancies(db, class_id, meal_date, upload.id)
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        # Non-fatal

    upload.status = UploadStatus.SUCCESS
    db.flush()

    # 9. Audit
    db.add(AuditLog(
        user_id=teacher.id,
        action="upload_tabel",
        entity_type="meal_upload",
        entity_id=upload.id,
        details=f"Uploaded tabel for class_id={class_id}, date={meal_date}, version={upload.version}",
    ))
    db.commit()

    return upload
