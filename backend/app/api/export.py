import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User
from app.api.deps import get_current_user, require_admin
from app.services.export_service import export_summary_for_date, export_summary_for_month
from app.services.zip_email_service import (
    create_summary_zip, create_tabels_zip, send_email_with_attachments,
)
from app.schemas.schemas import EmailSendRequest

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/summary/date")
def export_by_date(
    meal_date: date,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        path = export_summary_for_date(db, meal_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(path),
    )


@router.get("/summary/month")
def export_by_month(
    year: int, month: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        path = export_summary_for_month(db, year, month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(path),
    )


@router.get("/zip/summary")
def download_summary_zip(
    meal_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        path = create_summary_zip(db, meal_date=meal_date, year=year, month=month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return FileResponse(path, media_type="application/zip", filename=os.path.basename(path))


@router.get("/zip/tabels")
def download_tabels_zip(
    meal_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        path = create_tabels_zip(db, meal_date=meal_date, year=year, month=month)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return FileResponse(path, media_type="application/zip", filename=os.path.basename(path))


@router.post("/send-email")
def send_email(
    req: EmailSendRequest,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        dispatch = send_email_with_attachments(
            db, user.id, req.recipient_email, req.subject,
            meal_date=req.meal_date, year=req.year, month=req.month,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "id": dispatch.id,
        "status": dispatch.status,
        "summary_zip": dispatch.summary_zip_path,
        "tabels_zip": dispatch.tabels_zip_path,
        "error": dispatch.error_message,
    }
