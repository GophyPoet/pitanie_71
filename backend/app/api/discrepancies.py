from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Discrepancy, DiscrepancyStatus, SchoolClass, User
from app.schemas.schemas import DiscrepancyOut
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/discrepancies", tags=["discrepancies"])


@router.get("/", response_model=list[DiscrepancyOut])
def list_discrepancies(
    meal_date: date | None = None,
    class_id: int | None = None,
    status: DiscrepancyStatus | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Discrepancy)
    if meal_date:
        query = query.filter(Discrepancy.meal_date == meal_date)
    if class_id:
        query = query.filter(Discrepancy.class_id == class_id)
    if status:
        query = query.filter(Discrepancy.status == status)

    discs = query.order_by(Discrepancy.created_at.desc()).limit(100).all()
    results = []
    for d in discs:
        sc = db.query(SchoolClass).filter(SchoolClass.id == d.class_id).first()
        out = DiscrepancyOut.model_validate(d)
        out.class_name = sc.name if sc else ""
        results.append(out)
    return results


@router.put("/{disc_id}/review")
def review_discrepancy(
    disc_id: int,
    action: str = "reviewed",  # reviewed | dismissed
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    disc = db.query(Discrepancy).filter(Discrepancy.id == disc_id).first()
    if not disc:
        raise HTTPException(status_code=404, detail="Расхождение не найдено")
    if action == "dismissed":
        disc.status = DiscrepancyStatus.DISMISSED
    else:
        disc.status = DiscrepancyStatus.REVIEWED
    disc.reviewed_by = user.id
    disc.reviewed_at = datetime.utcnow()
    db.commit()
    return {"status": disc.status.value}
