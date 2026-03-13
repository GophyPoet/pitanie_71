from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.models.models import User, UserRole, TeacherClassAssignment, SchoolClass
from app.schemas.schemas import UserCreate, UserOut, UserWithClasses, SchoolClassOut
from app.api.deps import require_admin

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(User).order_by(User.full_name).all()


@router.post("/", response_model=UserOut)
def create_user(req: UserCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Логин уже занят")
    user = User(
        username=req.username,
        full_name=req.full_name,
        hashed_password=hash_password(req.password),
        role=req.role,
    )
    db.add(user)
    db.flush()
    for cid in req.class_ids:
        db.add(TeacherClassAssignment(teacher_id=user.id, class_id=cid))
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserWithClasses)
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    assignments = db.query(TeacherClassAssignment).filter(
        TeacherClassAssignment.teacher_id == user_id
    ).all()
    classes = []
    for a in assignments:
        sc = db.query(SchoolClass).filter(SchoolClass.id == a.class_id).first()
        if sc:
            classes.append(SchoolClassOut.model_validate(sc))
    result = UserWithClasses.model_validate(user)
    result.assigned_classes = classes
    return result


@router.put("/{user_id}/toggle-active")
def toggle_active(user_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_active = not user.is_active
    db.commit()
    return {"is_active": user.is_active}


@router.put("/{user_id}/reset-password")
def reset_password(user_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.hashed_password = hash_password("123456")
    db.commit()
    return {"message": "Пароль сброшен на 123456"}


@router.put("/{user_id}/classes")
def update_classes(
    user_id: int, class_ids: list[int], db: Session = Depends(get_db), _=Depends(require_admin)
):
    db.query(TeacherClassAssignment).filter(
        TeacherClassAssignment.teacher_id == user_id
    ).delete()
    for cid in class_ids:
        db.add(TeacherClassAssignment(teacher_id=user_id, class_id=cid))
    db.commit()
    return {"message": "Классы обновлены"}
