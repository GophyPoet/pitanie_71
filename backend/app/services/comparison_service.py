"""
Service for comparing meal data between consecutive days.
Detects discrepancies in student counts, benefits, totals, etc.
"""
import logging
from datetime import date
from sqlalchemy.orm import Session

from app.models.models import (
    SummaryRow, StudentMealRecord, MealUpload, SchoolClass,
    Discrepancy, DiscrepancyItem, DiscrepancyStatus,
)

logger = logging.getLogger(__name__)


def find_previous_summary(db: Session, class_id: int, current_date: date) -> SummaryRow | None:
    """Find the most recent summary row before current_date for the same class."""
    return (
        db.query(SummaryRow)
        .filter(
            SummaryRow.class_id == class_id,
            SummaryRow.meal_date < current_date,
        )
        .order_by(SummaryRow.meal_date.desc())
        .first()
    )


def compare_and_create_discrepancies(
    db: Session,
    class_id: int,
    current_date: date,
    upload_id: int,
) -> Discrepancy | None:
    """
    Compare current day data with previous day for the same class.
    Creates Discrepancy + DiscrepancyItem records.
    """
    current = (
        db.query(SummaryRow)
        .filter(SummaryRow.class_id == class_id, SummaryRow.meal_date == current_date)
        .first()
    )
    if not current:
        return None

    previous = find_previous_summary(db, class_id, current_date)
    if not previous:
        logger.info(f"No previous data for class_id={class_id}, skipping comparison")
        return None

    # Delete old discrepancy for same class+date if exists
    db.query(Discrepancy).filter(
        Discrepancy.class_id == class_id,
        Discrepancy.meal_date == current_date,
    ).delete()
    db.flush()

    disc = Discrepancy(
        class_id=class_id,
        meal_date=current_date,
        previous_date=previous.meal_date,
        upload_id=upload_id,
        status=DiscrepancyStatus.NEW,
    )
    db.add(disc)
    db.flush()

    items = []

    # Compare numeric fields
    field_labels = {
        "eating_count": "Кол-во питающихся",
        "student_count": "Кол-во детей в классе",
        "parent_breakfast": "Родит. плата завтрак",
        "parent_lunch": "Родит. плата обед",
        "parent_lunch_shved": "Родит. плата обед/шв",
        "free_breakfast": "Бесплатно завтрак",
        "free_lunch": "Бесплатно обед",
        "multichild_breakfast": "Многодетные завтрак",
        "mobilized_breakfast_lunch": "Мобилизованные завтрак/обед",
        "mobilized_count": "Мобилизованные кол-во",
        "ovz_breakfast_lunch": "ОВЗ завтрак/обед",
        "ovz_count": "ОВЗ кол-во",
        "total_breakfasts": "ИТОГО завтраков",
        "total_lunches": "ИТОГО обедов",
    }

    for field_name, label in field_labels.items():
        old_val = getattr(previous, field_name, 0) or 0
        new_val = getattr(current, field_name, 0) or 0
        diff = new_val - old_val
        if diff != 0:
            severity = "info"
            if abs(diff) >= 3:
                severity = "warning"
            if abs(diff) >= 5:
                severity = "error"
            items.append(DiscrepancyItem(
                discrepancy_id=disc.id,
                field_name=field_name,
                description=f"{label}: было {old_val}, стало {new_val} (разница: {diff:+d})",
                old_value=str(old_val),
                new_value=str(new_val),
                severity=severity,
            ))

    # Compare student-level records
    _compare_students(db, disc, upload_id, class_id, current_date, previous.meal_date, items)

    if items:
        db.add_all(items)
        logger.info(f"Created {len(items)} discrepancy items for class_id={class_id}, date={current_date}")
    else:
        # No discrepancies found, remove the empty record
        db.delete(disc)
        db.flush()
        return None

    db.flush()
    return disc


def _compare_students(
    db: Session,
    disc: Discrepancy,
    current_upload_id: int,
    class_id: int,
    current_date: date,
    previous_date: date,
    items: list,
):
    """Compare student-level records between two uploads."""
    # Get current upload records
    current_records = (
        db.query(StudentMealRecord)
        .filter(StudentMealRecord.upload_id == current_upload_id)
        .all()
    )
    # Get previous upload
    prev_upload = (
        db.query(MealUpload)
        .filter(
            MealUpload.class_id == class_id,
            MealUpload.meal_date == previous_date,
            MealUpload.is_current == True,
        )
        .first()
    )
    if not prev_upload:
        return

    prev_records = (
        db.query(StudentMealRecord)
        .filter(StudentMealRecord.upload_id == prev_upload.id)
        .all()
    )

    current_names = {r.student_name_raw.lower().strip(): r for r in current_records}
    prev_names = {r.student_name_raw.lower().strip(): r for r in prev_records}

    # New students
    for name in current_names:
        if name not in prev_names:
            items.append(DiscrepancyItem(
                discrepancy_id=disc.id,
                field_name="student_added",
                description=f"Новый ученик: {current_names[name].student_name_raw}",
                old_value=None,
                new_value=current_names[name].student_name_raw,
                severity="warning",
                student_name=current_names[name].student_name_raw,
            ))

    # Missing students
    for name in prev_names:
        if name not in current_names:
            items.append(DiscrepancyItem(
                discrepancy_id=disc.id,
                field_name="student_removed",
                description=f"Ученик отсутствует: {prev_names[name].student_name_raw}",
                old_value=prev_names[name].student_name_raw,
                new_value=None,
                severity="warning",
                student_name=prev_names[name].student_name_raw,
            ))

    # Changed benefit status
    for name in current_names:
        if name in prev_names:
            cur = current_names[name]
            prev = prev_names[name]
            if (cur.benefit_raw or "") != (prev.benefit_raw or ""):
                items.append(DiscrepancyItem(
                    discrepancy_id=disc.id,
                    field_name="benefit_changed",
                    description=(
                        f"Изменилась льгота у {cur.student_name_raw}: "
                        f"было '{prev.benefit_raw or '-'}', стало '{cur.benefit_raw or '-'}'"
                    ),
                    old_value=prev.benefit_raw,
                    new_value=cur.benefit_raw,
                    severity="warning",
                    student_name=cur.student_name_raw,
                ))
