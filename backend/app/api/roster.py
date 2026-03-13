"""
API for teacher's interactive roster and daily meal tabel.

Teachers can:
- View / add / edit / remove students in their class
- Fill in daily meal records in the browser (interactive table)
- Save drafts and submit to admin
- Export tabel as Excel in the original template format
"""
from datetime import date, datetime
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import (
    User, SchoolClass, Student, StudentBenefit, BenefitType,
    MealUpload, StudentMealRecord, SummaryRow, AuditLog,
    TeacherClassAssignment, UploadStatus,
)
from app.schemas.schemas import (
    StudentOut, StudentCreate, StudentUpdate,
    MealRecordEntry, InteractiveTabelSave, InteractiveTabelSubmit,
    StudentMealRecordOut,
)
from app.api.deps import get_current_user
from app.services.comparison_service import compare_and_create_discrepancies

router = APIRouter(prefix="/roster", tags=["roster"])


def _check_class_access(db: Session, user: User, class_id: int):
    if user.role.value == "admin":
        return
    has = (
        db.query(TeacherClassAssignment)
        .filter(TeacherClassAssignment.teacher_id == user.id,
                TeacherClassAssignment.class_id == class_id)
        .first()
    )
    if not has:
        raise HTTPException(status_code=403, detail="Нет доступа к этому классу")


def _student_to_out(db: Session, student: Student) -> StudentOut:
    benefit_code = None
    active_benefit = (
        db.query(StudentBenefit)
        .filter(StudentBenefit.student_id == student.id, StudentBenefit.is_active == True)
        .first()
    )
    if active_benefit:
        bt = db.query(BenefitType).filter(BenefitType.id == active_benefit.benefit_type_id).first()
        if bt:
            benefit_code = bt.code
    out = StudentOut.model_validate(student)
    out.benefit_code = benefit_code
    return out


# ────────────────────────────────────────────
# Student Roster
# ────────────────────────────────────────────

@router.get("/{class_id}/students", response_model=list[StudentOut])
def list_students(class_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_class_access(db, user, class_id)
    students = (
        db.query(Student)
        .filter(Student.class_id == class_id, Student.is_active == True)
        .order_by(Student.full_name)
        .all()
    )
    return [_student_to_out(db, s) for s in students]


@router.post("/{class_id}/students", response_model=StudentOut)
def add_student(
    class_id: int, req: StudentCreate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    _check_class_access(db, user, class_id)
    # Check duplicate
    existing = (
        db.query(Student)
        .filter(Student.class_id == class_id, Student.full_name == req.full_name.strip(), Student.is_active == True)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Ученик с таким именем уже есть в классе")

    student = Student(full_name=req.full_name.strip(), class_id=class_id, notes=req.notes)
    db.add(student)
    db.flush()

    if req.benefit_code:
        bt = db.query(BenefitType).filter(BenefitType.code == req.benefit_code.lower()).first()
        if bt:
            db.add(StudentBenefit(student_id=student.id, benefit_type_id=bt.id, is_active=True))

    # Update class student count
    sc = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if sc:
        sc.student_count = db.query(Student).filter(Student.class_id == class_id, Student.is_active == True).count()

    db.add(AuditLog(user_id=user.id, action="add_student", entity_type="student", entity_id=student.id,
                     details=f"Added {req.full_name} to class {class_id}"))
    db.commit()
    return _student_to_out(db, student)


@router.put("/{class_id}/students/{student_id}", response_model=StudentOut)
def update_student(
    class_id: int, student_id: int, req: StudentUpdate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    _check_class_access(db, user, class_id)
    student = db.query(Student).filter(Student.id == student_id, Student.class_id == class_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")

    if req.full_name is not None:
        student.full_name = req.full_name.strip()
    if req.notes is not None:
        student.notes = req.notes
    if req.is_active is not None:
        student.is_active = req.is_active
        sc = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
        if sc:
            sc.student_count = db.query(Student).filter(Student.class_id == class_id, Student.is_active == True).count()

    if req.benefit_code is not None:
        # Remove old active benefits
        db.query(StudentBenefit).filter(
            StudentBenefit.student_id == student_id, StudentBenefit.is_active == True
        ).update({"is_active": False})
        if req.benefit_code:
            bt = db.query(BenefitType).filter(BenefitType.code == req.benefit_code.lower()).first()
            if bt:
                db.add(StudentBenefit(student_id=student_id, benefit_type_id=bt.id, is_active=True))

    db.commit()
    return _student_to_out(db, student)


@router.delete("/{class_id}/students/{student_id}")
def remove_student(
    class_id: int, student_id: int,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    _check_class_access(db, user, class_id)
    student = db.query(Student).filter(Student.id == student_id, Student.class_id == class_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")
    student.is_active = False
    sc = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if sc:
        sc.student_count = db.query(Student).filter(Student.class_id == class_id, Student.is_active == True).count()
    db.commit()
    return {"ok": True}


# ────────────────────────────────────────────
# Interactive Daily Tabel
# ────────────────────────────────────────────

@router.get("/{class_id}/tabel/{meal_date}", response_model=list[StudentMealRecordOut])
def get_tabel(
    class_id: int, meal_date: date,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Get saved meal records for a class+date (for pre-filling the interactive table)."""
    _check_class_access(db, user, class_id)
    upload = (
        db.query(MealUpload)
        .filter(MealUpload.class_id == class_id, MealUpload.meal_date == meal_date, MealUpload.is_current == True)
        .first()
    )
    if not upload:
        return []
    records = (
        db.query(StudentMealRecord)
        .filter(StudentMealRecord.upload_id == upload.id)
        .order_by(StudentMealRecord.row_number)
        .all()
    )
    return records


@router.post("/tabel/save")
def save_tabel(
    req: InteractiveTabelSave,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Save interactive tabel as draft (without submitting to admin)."""
    _check_class_access(db, user, req.class_id)
    upload = _save_records(db, user, req.class_id, req.meal_date, req.records, submit=False)
    return {"upload_id": upload.id, "status": upload.status.value, "message": "Черновик сохранён"}


@router.post("/tabel/submit")
def submit_tabel(
    req: InteractiveTabelSubmit,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Submit interactive tabel — saves records AND pushes to summary for admin."""
    _check_class_access(db, user, req.class_id)
    upload = _save_records(db, user, req.class_id, req.meal_date, req.records, submit=True)
    return {
        "upload_id": upload.id,
        "status": upload.status.value,
        "message": "Табель отправлен администратору",
    }


def _save_records(
    db: Session, user: User, class_id: int, meal_date: date,
    records: list[MealRecordEntry], submit: bool,
) -> MealUpload:
    """Create/update MealUpload + StudentMealRecords from interactive input."""

    # Mark previous uploads as non-current
    prev_uploads = (
        db.query(MealUpload)
        .filter(MealUpload.class_id == class_id, MealUpload.meal_date == meal_date, MealUpload.is_current == True)
        .all()
    )
    max_version = 0
    for pu in prev_uploads:
        pu.is_current = False
        max_version = max(max_version, pu.version)

    upload = MealUpload(
        teacher_id=user.id,
        class_id=class_id,
        meal_date=meal_date,
        month=meal_date.month,
        year=meal_date.year,
        original_filename="interactive",
        stored_filename="interactive",
        file_path="",
        status=UploadStatus.SUCCESS,
        version=max_version + 1,
        is_current=True,
        sheet_name="interactive",
        parsed_class_name=None,
        parsed_date=str(meal_date),
    )
    db.add(upload)
    db.flush()

    sc = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if upload.parsed_class_name is None and sc:
        upload.parsed_class_name = sc.name

    # Save student records
    for i, entry in enumerate(records):
        student = db.query(Student).filter(Student.id == entry.student_id).first()
        if not student:
            continue

        # Get benefit
        active_benefit = (
            db.query(StudentBenefit)
            .filter(StudentBenefit.student_id == student.id, StudentBenefit.is_active == True)
            .first()
        )
        benefit_raw = None
        if active_benefit:
            bt = db.query(BenefitType).filter(BenefitType.id == active_benefit.benefit_type_id).first()
            if bt:
                benefit_raw = bt.code

        total_bf = entry.avangard_breakfast + entry.lyubava_breakfast
        total_lu = entry.avangard_lunch + entry.lyubava_lunch
        total_shv = entry.avangard_shved + entry.lyubava_shved

        rec = StudentMealRecord(
            upload_id=upload.id,
            student_id=student.id,
            student_name_raw=student.full_name,
            row_number=i + 1,
            benefit_raw=benefit_raw,
            avangard_breakfast=entry.avangard_breakfast,
            avangard_lunch=entry.avangard_lunch,
            avangard_shved=entry.avangard_shved,
            lyubava_breakfast=entry.lyubava_breakfast,
            lyubava_lunch=entry.lyubava_lunch,
            lyubava_shved=entry.lyubava_shved,
            total_breakfasts=total_bf,
            total_lunches=total_lu,
            total_shved=total_shv,
        )
        db.add(rec)

    db.flush()

    # If submitting → update summary row for admin
    if submit:
        _update_summary_from_upload(db, upload, user)
        # Comparison
        try:
            compare_and_create_discrepancies(db, class_id, meal_date, upload.id)
        except Exception:
            pass

    db.add(AuditLog(
        user_id=user.id,
        action="interactive_save" if not submit else "interactive_submit",
        entity_type="meal_upload",
        entity_id=upload.id,
        details=f"class_id={class_id}, date={meal_date}, records={len(records)}, submit={submit}",
    ))
    db.commit()
    return upload


def _update_summary_from_upload(db: Session, upload: MealUpload, user: User):
    """Recompute summary row from the upload's student records."""
    records = db.query(StudentMealRecord).filter(StudentMealRecord.upload_id == upload.id).all()
    sc = db.query(SchoolClass).filter(SchoolClass.id == upload.class_id).first()

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
    total_bf = 0
    total_lu = 0

    for r in records:
        has_meal = (r.total_breakfasts + r.total_lunches + r.total_shved) > 0
        if has_meal:
            eating += 1
        total_bf += r.total_breakfasts
        total_lu += r.total_lunches

        benefit = (r.benefit_raw or "").strip().lower()
        if benefit in ("сво",):
            mobilized_cnt += 1
            mobilized += r.total_breakfasts + r.total_lunches
        elif benefit in ("овз",):
            ovz_cnt += 1
            ovz += r.total_breakfasts + r.total_lunches
        elif benefit in ("мн", "мног.", "мног"):
            multichild += r.total_breakfasts
        elif benefit in ("б/к", "б/о"):
            free_bf += r.total_breakfasts
            free_lunch += r.total_lunches
        else:
            parent_bf += r.avangard_breakfast + r.lyubava_breakfast
            parent_lunch += r.avangard_lunch + r.lyubava_lunch
            parent_lunch_shved += r.avangard_shved + r.lyubava_shved

    summary_data = dict(
        class_id=upload.class_id,
        meal_date=upload.meal_date,
        upload_id=upload.id,
        teacher_name=user.full_name,
        student_count=sc.student_count if sc else len(records),
        eating_count=eating,
        parent_breakfast=parent_bf,
        parent_lunch=parent_lunch,
        parent_lunch_shved=parent_lunch_shved,
        free_breakfast=free_bf,
        free_lunch=free_lunch,
        multichild_breakfast=multichild,
        mobilized_breakfast_lunch=mobilized,
        mobilized_count=mobilized_cnt,
        ovz_breakfast_lunch=ovz,
        ovz_count=ovz_cnt,
        total_breakfasts=total_bf,
        total_lunches=total_lu,
        is_submitted=True,
        submitted_at=datetime.utcnow(),
        source="interactive",
    )

    existing = (
        db.query(SummaryRow)
        .filter(SummaryRow.class_id == upload.class_id, SummaryRow.meal_date == upload.meal_date)
        .first()
    )
    if existing:
        for k, v in summary_data.items():
            setattr(existing, k, v)
    else:
        db.add(SummaryRow(**summary_data))
    db.flush()


# ────────────────────────────────────────────
# Export tabel as Excel (original template)
# ────────────────────────────────────────────

@router.get("/{class_id}/export-tabel/{meal_date}")
def export_tabel_excel(
    class_id: int, meal_date: date,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Export tabel as .xlsx in the exact original template format."""
    _check_class_access(db, user, class_id)
    from app.services.tabel_export_service import export_tabel_to_excel
    try:
        path = export_tabel_to_excel(db, class_id, meal_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(path),
    )
