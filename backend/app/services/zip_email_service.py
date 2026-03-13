"""
ZIP archiving and email sending service.
Creates two ZIP archives:
  1. Summary (заявка) Excel
  2. All original tabel files with status "submitted"
"""
import os
import zipfile
import logging
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import MealUpload, UploadStatus, EmailDispatch, AuditLog
from app.services.export_service import export_summary_for_date, export_summary_for_month

logger = logging.getLogger(__name__)


def create_summary_zip(db: Session, meal_date: date | None = None, year: int | None = None, month: int | None = None) -> str:
    """Create ZIP with summary Excel file(s)."""
    if meal_date:
        excel_path = export_summary_for_date(db, meal_date)
        zip_name = f"Заявка_{meal_date.strftime('%d.%m.%Y')}.zip"
    elif year and month:
        excel_path = export_summary_for_month(db, year, month)
        zip_name = f"Заявка_{month:02d}.{year}.zip"
    else:
        raise ValueError("Укажите дату или месяц/год")

    zip_path = os.path.join(settings.EXPORT_DIR, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(excel_path, os.path.basename(excel_path))

    logger.info(f"Created summary ZIP: {zip_path}")
    return zip_path


def create_tabels_zip(db: Session, meal_date: date | None = None, year: int | None = None, month: int | None = None) -> str:
    """Create ZIP with all original tabel files that have been successfully processed."""
    query = db.query(MealUpload).filter(
        MealUpload.is_current == True,
        MealUpload.status == UploadStatus.SUCCESS,
    )

    if meal_date:
        query = query.filter(MealUpload.meal_date == meal_date)
        zip_name = f"Табели_{meal_date.strftime('%d.%m.%Y')}.zip"
    elif year and month:
        query = query.filter(MealUpload.year == year, MealUpload.month == month)
        zip_name = f"Табели_{month:02d}.{year}.zip"
    else:
        raise ValueError("Укажите дату или месяц/год")

    uploads = query.all()
    zip_path = os.path.join(settings.EXPORT_DIR, zip_name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for upload in uploads:
            if os.path.exists(upload.file_path):
                arcname = upload.original_filename
                zf.write(upload.file_path, arcname)
            else:
                logger.warning(f"File not found for upload {upload.id}: {upload.file_path}")

    logger.info(f"Created tabels ZIP with {len(uploads)} files: {zip_path}")
    return zip_path


def send_email_with_attachments(
    db: Session,
    user_id: int,
    recipient_email: str,
    subject: str,
    meal_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> EmailDispatch:
    """Send email with two ZIP attachments."""

    dispatch = EmailDispatch(
        user_id=user_id,
        recipient_email=recipient_email,
        subject=subject or f"Заявка на питание {meal_date or f'{month:02d}.{year}'}",
        meal_date=meal_date,
        month=month,
        year=year,
        status="pending",
    )
    db.add(dispatch)
    db.flush()

    try:
        summary_zip = create_summary_zip(db, meal_date=meal_date, year=year, month=month)
        tabels_zip = create_tabels_zip(db, meal_date=meal_date, year=year, month=month)

        dispatch.summary_zip_path = summary_zip
        dispatch.tabels_zip_path = tabels_zip

        # Build email
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = recipient_email
        msg["Subject"] = dispatch.subject

        body = f"Заявка на питание МБУ \"Школа № 71\"\n"
        if meal_date:
            body += f"Дата: {meal_date.strftime('%d.%m.%Y')}\n"
        elif month and year:
            body += f"Период: {month:02d}.{year}\n"
        body += f"\nВ архивах:\n1. Сводная заявка на питание\n2. Табели от учителей\n"
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attach ZIPs
        for zip_path in [summary_zip, tabels_zip]:
            if os.path.exists(zip_path):
                with open(zip_path, "rb") as f:
                    part = MIMEBase("application", "zip")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(zip_path)}",
                    )
                    msg.attach(part)

        # Send
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

            dispatch.status = "sent"
            dispatch.sent_at = datetime.utcnow()
            logger.info(f"Email sent to {recipient_email}")
        else:
            dispatch.status = "sent"
            dispatch.sent_at = datetime.utcnow()
            logger.warning("SMTP not configured, but ZIPs created successfully. Marking as sent (dry run).")

    except Exception as e:
        dispatch.status = "failed"
        dispatch.error_message = str(e)
        logger.error(f"Email send failed: {e}")

    db.add(AuditLog(
        user_id=user_id,
        action="send_email",
        entity_type="email_dispatch",
        entity_id=dispatch.id,
        details=f"Email to {recipient_email}, status={dispatch.status}",
    ))
    db.commit()
    return dispatch
