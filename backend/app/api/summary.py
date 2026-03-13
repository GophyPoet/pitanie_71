from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import (
    User, SummaryRow, SchoolClass, MealUpload, Discrepancy, ManualEdit, AuditLog,
    UploadStatus, DiscrepancyStatus,
)
from app.schemas.schemas import (
    SummaryRowOut, SummaryRowUpdate, ClassSubmissionStatus, DashboardStats,
)
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("/by-date", response_model=list[SummaryRowOut])
def get_summary_by_date(
    meal_date: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(SummaryRow)
        .join(SchoolClass, SummaryRow.class_id == SchoolClass.id)
        .filter(SummaryRow.meal_date == meal_date)
        .order_by(SchoolClass.grade, SchoolClass.letter)
        .all()
    )
    results = []
    for r in rows:
        sc = db.query(SchoolClass).filter(SchoolClass.id == r.class_id).first()
        out = SummaryRowOut.model_validate(r)
        out.class_name = sc.name if sc else ""
        results.append(out)
    return results


@router.put("/{summary_id}", response_model=SummaryRowOut)
def update_summary_row(
    summary_id: int,
    req: SummaryRowUpdate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.query(SummaryRow).filter(SummaryRow.id == summary_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    updates = req.model_dump(exclude_unset=True, exclude={"comment"})
    for field, new_val in updates.items():
        if new_val is not None:
            old_val = getattr(row, field)
            if old_val != new_val:
                db.add(ManualEdit(
                    user_id=user.id,
                    table_name="summary_rows",
                    record_id=summary_id,
                    field_name=field,
                    old_value=str(old_val),
                    new_value=str(new_val),
                    comment=req.comment,
                ))
                setattr(row, field, new_val)

    row.source = "manual"
    db.add(AuditLog(
        user_id=user.id,
        action="manual_edit_summary",
        entity_type="summary_row",
        entity_id=summary_id,
        details=f"Manual edit: {req.comment}",
    ))
    db.commit()
    sc = db.query(SchoolClass).filter(SchoolClass.id == row.class_id).first()
    out = SummaryRowOut.model_validate(row)
    out.class_name = sc.name if sc else ""
    return out


@router.get("/submission-status", response_model=list[ClassSubmissionStatus])
def get_submission_status(
    meal_date: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    classes = db.query(SchoolClass).filter(SchoolClass.is_active == True).order_by(
        SchoolClass.grade, SchoolClass.letter
    ).all()
    result = []
    for sc in classes:
        summary = (
            db.query(SummaryRow)
            .filter(SummaryRow.class_id == sc.id, SummaryRow.meal_date == meal_date)
            .first()
        )
        disc = (
            db.query(Discrepancy)
            .filter(
                Discrepancy.class_id == sc.id,
                Discrepancy.meal_date == meal_date,
                Discrepancy.status == DiscrepancyStatus.NEW,
            )
            .first()
        )
        upload = None
        if summary and summary.upload_id:
            upload = db.query(MealUpload).filter(MealUpload.id == summary.upload_id).first()

        result.append(ClassSubmissionStatus(
            class_id=sc.id,
            class_name=sc.name,
            meal_date=meal_date,
            is_submitted=summary is not None and summary.is_submitted,
            teacher_name=summary.teacher_name if summary else "",
            submitted_at=summary.submitted_at if summary else None,
            upload_id=upload.id if upload else None,
            version=upload.version if upload else 0,
            has_discrepancies=disc is not None,
        ))
    return result


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    meal_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not meal_date:
        meal_date = date.today()

    total_classes = db.query(SchoolClass).filter(SchoolClass.is_active == True).count()
    submitted = (
        db.query(SummaryRow)
        .filter(SummaryRow.meal_date == meal_date, SummaryRow.is_submitted == True)
        .count()
    )
    summaries = (
        db.query(SummaryRow)
        .filter(SummaryRow.meal_date == meal_date)
        .all()
    )
    total_eating = sum(s.eating_count or 0 for s in summaries)
    total_bf = sum(s.total_breakfasts or 0 for s in summaries)
    total_lunch = sum(s.total_lunches or 0 for s in summaries)
    disc_new = (
        db.query(Discrepancy)
        .filter(Discrepancy.meal_date == meal_date, Discrepancy.status == DiscrepancyStatus.NEW)
        .count()
    )

    return DashboardStats(
        total_classes=total_classes,
        submitted_today=submitted,
        not_submitted_today=total_classes - submitted,
        total_eating_today=total_eating,
        total_breakfasts_today=total_bf,
        total_lunches_today=total_lunch,
        discrepancies_new=disc_new,
    )
