import calendar
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import MonthlyPlan, MonthlyPlanDay
from app.schemas.schemas import MonthlyPlanCreate, MonthlyPlanOut
from app.api.deps import require_admin, get_current_user

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/", response_model=MonthlyPlanOut)
def create_plan(
    req: MonthlyPlanCreate,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(MonthlyPlan)
        .filter(MonthlyPlan.year == req.year, MonthlyPlan.month == req.month)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="План на этот месяц уже существует")

    plan = MonthlyPlan(year=req.year, month=req.month)
    db.add(plan)
    db.flush()

    # Generate school days (Mon-Fri, excluding weekends)
    _, days_in_month = calendar.monthrange(req.year, req.month)
    for day in range(1, days_in_month + 1):
        d = date(req.year, req.month, day)
        is_school = d.weekday() < 5  # Mon=0, Fri=4
        db.add(MonthlyPlanDay(plan_id=plan.id, date=d, is_school_day=is_school))

    db.commit()
    db.refresh(plan)
    return plan


@router.get("/", response_model=list[MonthlyPlanOut])
def list_plans(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(MonthlyPlan).order_by(MonthlyPlan.year.desc(), MonthlyPlan.month.desc()).all()


@router.get("/{plan_id}", response_model=MonthlyPlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    plan = db.query(MonthlyPlan).filter(MonthlyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="План не найден")
    return plan


@router.delete("/{plan_id}/days/{day_id}")
def remove_day(plan_id: int, day_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    day = db.query(MonthlyPlanDay).filter(
        MonthlyPlanDay.id == day_id, MonthlyPlanDay.plan_id == plan_id
    ).first()
    if not day:
        raise HTTPException(status_code=404, detail="День не найден")
    db.delete(day)
    db.commit()
    return {"message": "День удалён"}


@router.post("/{plan_id}/days")
def add_day(
    plan_id: int, day_date: date,
    db: Session = Depends(get_db), _=Depends(require_admin),
):
    plan = db.query(MonthlyPlan).filter(MonthlyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="План не найден")
    existing = db.query(MonthlyPlanDay).filter(
        MonthlyPlanDay.plan_id == plan_id, MonthlyPlanDay.date == day_date
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Дата уже есть в плане")
    day = MonthlyPlanDay(plan_id=plan_id, date=day_date, is_school_day=True)
    db.add(day)
    db.commit()
    return {"id": day.id, "date": str(day_date)}


@router.put("/{plan_id}/days/{day_id}/toggle")
def toggle_school_day(
    plan_id: int, day_id: int,
    db: Session = Depends(get_db), _=Depends(require_admin),
):
    day = db.query(MonthlyPlanDay).filter(
        MonthlyPlanDay.id == day_id, MonthlyPlanDay.plan_id == plan_id
    ).first()
    if not day:
        raise HTTPException(status_code=404, detail="День не найден")
    day.is_school_day = not day.is_school_day
    db.commit()
    return {"is_school_day": day.is_school_day}
