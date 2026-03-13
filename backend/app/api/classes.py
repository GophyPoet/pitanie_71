from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import SchoolClass, BenefitType
from app.schemas.schemas import SchoolClassCreate, SchoolClassOut, BenefitTypeCreate, BenefitTypeOut
from app.api.deps import require_admin, get_current_user

router = APIRouter(prefix="/classes", tags=["classes"])


@router.get("/", response_model=list[SchoolClassOut])
def list_classes(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(SchoolClass).filter(SchoolClass.is_active == True).order_by(
        SchoolClass.grade, SchoolClass.letter
    ).all()


@router.post("/", response_model=SchoolClassOut)
def create_class(req: SchoolClassCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(SchoolClass).filter(SchoolClass.name == req.name).first():
        raise HTTPException(status_code=400, detail="Класс уже существует")
    sc = SchoolClass(**req.model_dump())
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return sc


@router.get("/benefits", response_model=list[BenefitTypeOut])
def list_benefits(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(BenefitType).order_by(BenefitType.code).all()


@router.post("/benefits", response_model=BenefitTypeOut)
def create_benefit(req: BenefitTypeCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    bt = BenefitType(**req.model_dump())
    db.add(bt)
    db.commit()
    db.refresh(bt)
    return bt
