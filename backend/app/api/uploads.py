import os
import tempfile
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import (
    User, MealUpload, StudentMealRecord, SchoolClass, TeacherClassAssignment,
)
from app.schemas.schemas import UploadOut, StudentMealRecordOut
from app.api.deps import get_current_user
from app.services.upload_service import process_upload, UploadError

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/", response_model=UploadOut)
async def upload_tabel(
    file: UploadFile = File(...),
    class_id: int = Form(...),
    meal_date: date = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Файл не выбран")

    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in (".xls", ".xlsx"):
        raise HTTPException(status_code=400, detail="Поддерживаются только .xls и .xlsx файлы")

    # Save to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 10 МБ)")
        tmp.write(content)
        tmp_path = tmp.name

    try:
        upload = process_upload(db, user, class_id, meal_date, tmp_path, file.filename)
    except UploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    sc = db.query(SchoolClass).filter(SchoolClass.id == upload.class_id).first()
    result = UploadOut.model_validate(upload)
    result.class_name = sc.name if sc else ""
    result.teacher_name = user.full_name
    return result


@router.get("/", response_model=list[UploadOut])
def list_uploads(
    class_id: int | None = None,
    meal_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(MealUpload)

    if user.role.value == "teacher":
        query = query.filter(MealUpload.teacher_id == user.id)
    if class_id:
        query = query.filter(MealUpload.class_id == class_id)
    if meal_date:
        query = query.filter(MealUpload.meal_date == meal_date)

    uploads = query.order_by(MealUpload.created_at.desc()).limit(100).all()
    results = []
    for u in uploads:
        sc = db.query(SchoolClass).filter(SchoolClass.id == u.class_id).first()
        teacher = db.query(User).filter(User.id == u.teacher_id).first()
        out = UploadOut.model_validate(u)
        out.class_name = sc.name if sc else ""
        out.teacher_name = teacher.full_name if teacher else ""
        results.append(out)
    return results


@router.get("/{upload_id}/records", response_model=list[StudentMealRecordOut])
def get_upload_records(
    upload_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    upload = db.query(MealUpload).filter(MealUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Загрузка не найдена")
    records = (
        db.query(StudentMealRecord)
        .filter(StudentMealRecord.upload_id == upload_id)
        .order_by(StudentMealRecord.row_number)
        .all()
    )
    return records


@router.get("/my-classes")
def my_classes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get classes assigned to current teacher."""
    if user.role.value == "admin":
        classes = db.query(SchoolClass).filter(SchoolClass.is_active == True).order_by(
            SchoolClass.grade, SchoolClass.letter
        ).all()
    else:
        assignments = db.query(TeacherClassAssignment).filter(
            TeacherClassAssignment.teacher_id == user.id
        ).all()
        class_ids = [a.class_id for a in assignments]
        classes = db.query(SchoolClass).filter(SchoolClass.id.in_(class_ids)).order_by(
            SchoolClass.grade, SchoolClass.letter
        ).all()
    return [{"id": c.id, "name": c.name} for c in classes]
