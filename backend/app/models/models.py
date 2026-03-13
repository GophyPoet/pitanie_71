import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text,
    ForeignKey, Enum as SAEnum, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"


class UploadStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"


class DiscrepancyStatus(str, enum.Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"


# ──────────────────────────────────────────────
# Users & Roles
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.TEACHER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    teacher_classes = relationship("TeacherClassAssignment", back_populates="teacher")
    uploads = relationship("MealUpload", back_populates="teacher")
    audit_logs = relationship("AuditLog", back_populates="user")


# ──────────────────────────────────────────────
# Classes
# ──────────────────────────────────────────────

class SchoolClass(Base):
    __tablename__ = "school_classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), unique=True, nullable=False)  # "10-а", "1-б"
    grade = Column(Integer, nullable=False)  # 10, 1
    letter = Column(String(5), nullable=False)  # "а", "б"
    student_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    teacher_assignments = relationship("TeacherClassAssignment", back_populates="school_class")
    students = relationship("Student", back_populates="school_class")
    uploads = relationship("MealUpload", back_populates="school_class")
    summary_rows = relationship("SummaryRow", back_populates="school_class")


class TeacherClassAssignment(Base):
    __tablename__ = "teacher_class_assignments"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    is_primary = Column(Boolean, default=True)

    teacher = relationship("User", back_populates="teacher_classes")
    school_class = relationship("SchoolClass", back_populates="teacher_assignments")

    __table_args__ = (
        UniqueConstraint("teacher_id", "class_id", name="uq_teacher_class"),
    )


# ──────────────────────────────────────────────
# Students & Benefits
# ──────────────────────────────────────────────

class BenefitType(Base):
    __tablename__ = "benefit_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)  # СВО, МН, ОВЗ, б/к, Б/О, Мног.
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")

    student_benefits = relationship("StudentBenefit", back_populates="benefit_type")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, default="")  # e.g. "НЕТ КАРТЫ"

    school_class = relationship("SchoolClass", back_populates="students")
    benefits = relationship("StudentBenefit", back_populates="student")
    meal_records = relationship("StudentMealRecord", back_populates="student")


class StudentBenefit(Base):
    __tablename__ = "student_benefits"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    benefit_type_id = Column(Integer, ForeignKey("benefit_types.id"), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)

    student = relationship("Student", back_populates="benefits")
    benefit_type = relationship("BenefitType", back_populates="student_benefits")


# ──────────────────────────────────────────────
# Meal Uploads & Versions
# ──────────────────────────────────────────────

class MealUpload(Base):
    __tablename__ = "meal_uploads"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    meal_date = Column(Date, nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    status = Column(SAEnum(UploadStatus), default=UploadStatus.PENDING)
    error_message = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    is_current = Column(Boolean, default=True)
    sheet_name = Column(String(100), nullable=True)
    parsed_class_name = Column(String(50), nullable=True)
    parsed_date = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    teacher = relationship("User", back_populates="uploads")
    school_class = relationship("SchoolClass", back_populates="uploads")
    student_records = relationship("StudentMealRecord", back_populates="upload", cascade="all, delete-orphan")
    class_totals = relationship("ClassMealTotal", back_populates="upload", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_upload_class_date", "class_id", "meal_date"),
    )


# ──────────────────────────────────────────────
# Parsed meal data per student per upload
# ──────────────────────────────────────────────

class StudentMealRecord(Base):
    __tablename__ = "student_meal_records"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("meal_uploads.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    student_name_raw = Column(String(255), nullable=False)
    row_number = Column(Integer, nullable=False)
    benefit_raw = Column(String(50), nullable=True)

    # Авангард
    avangard_breakfast = Column(Integer, default=0)
    avangard_lunch = Column(Integer, default=0)
    avangard_shved = Column(Integer, default=0)

    # Любава
    lyubava_breakfast = Column(Integer, default=0)
    lyubava_lunch = Column(Integer, default=0)
    lyubava_shved = Column(Integer, default=0)

    # Totals from file
    total_breakfasts = Column(Integer, default=0)
    total_lunches = Column(Integer, default=0)
    total_shved = Column(Integer, default=0)

    student = relationship("Student", back_populates="meal_records")
    upload = relationship("MealUpload", back_populates="student_records")


# ──────────────────────────────────────────────
# Class-level totals from parsed tabel
# ──────────────────────────────────────────────

class ClassMealTotal(Base):
    __tablename__ = "class_meal_totals"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("meal_uploads.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    meal_date = Column(Date, nullable=False)

    total_students = Column(Integer, default=0)
    total_eating = Column(Integer, default=0)

    # Parent pay
    parent_breakfast = Column(Integer, default=0)
    parent_lunch = Column(Integer, default=0)
    parent_lunch_shved = Column(Integer, default=0)

    # Льготное питание
    benefit_breakfast = Column(Integer, default=0)
    benefit_lunch = Column(Integer, default=0)

    # Бесплатно
    free_breakfast = Column(Integer, default=0)
    free_lunch = Column(Integer, default=0)

    # Многодетные
    multichild_breakfast = Column(Integer, default=0)

    # Созвездие
    sozvezdie_breakfast = Column(Integer, default=0)

    # Мобилизованные (СВО)
    mobilized_breakfast_lunch = Column(Integer, default=0)
    mobilized_count = Column(Integer, default=0)

    # ОВЗ
    ovz_breakfast_lunch = Column(Integer, default=0)
    ovz_count = Column(Integer, default=0)

    # Созвездие ОВЗ
    sozvezdie_ovz_breakfast_lunch = Column(Integer, default=0)
    sozvezdie_ovz_count = Column(Integer, default=0)

    # Grand totals
    grand_total_breakfasts = Column(Integer, default=0)
    grand_total_lunches = Column(Integer, default=0)

    notes = Column(Text, default="")

    upload = relationship("MealUpload", back_populates="class_totals")

    __table_args__ = (
        Index("ix_class_total_date", "class_id", "meal_date"),
    )


# ──────────────────────────────────────────────
# Monthly Plan
# ──────────────────────────────────────────────

class MonthlyPlan(Base):
    __tablename__ = "monthly_plans"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    days = relationship("MonthlyPlanDay", back_populates="plan", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_plan_year_month"),
    )


class MonthlyPlanDay(Base):
    __tablename__ = "monthly_plan_days"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("monthly_plans.id"), nullable=False)
    date = Column(Date, nullable=False)
    is_school_day = Column(Boolean, default=True)

    plan = relationship("MonthlyPlan", back_populates="days")

    __table_args__ = (
        UniqueConstraint("plan_id", "date", name="uq_plan_day"),
    )


# ──────────────────────────────────────────────
# Summary Request (Заявка на питание) row
# ──────────────────────────────────────────────

class SummaryRow(Base):
    __tablename__ = "summary_rows"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    meal_date = Column(Date, nullable=False)
    upload_id = Column(Integer, ForeignKey("meal_uploads.id"), nullable=True)

    teacher_name = Column(String(255), default="")
    student_count = Column(Integer, default=0)
    eating_count = Column(Integer, default=0)

    parent_breakfast = Column(Integer, default=0)
    parent_lunch = Column(Integer, default=0)
    parent_lunch_shved = Column(Integer, default=0)

    benefit_breakfast = Column(Integer, default=0)
    benefit_lunch = Column(Integer, default=0)

    free_breakfast = Column(Integer, default=0)
    free_lunch = Column(Integer, default=0)

    multichild_breakfast = Column(Integer, default=0)

    sozvezdie_breakfast = Column(Integer, default=0)

    mobilized_breakfast_lunch = Column(Integer, default=0)
    mobilized_count = Column(Integer, default=0)

    ovz_breakfast_lunch = Column(Integer, default=0)
    ovz_count = Column(Integer, default=0)

    sozvezdie_ovz_breakfast_lunch = Column(Integer, default=0)
    sozvezdie_ovz_count = Column(Integer, default=0)

    total_breakfasts = Column(Integer, default=0)
    total_lunches = Column(Integer, default=0)

    notes = Column(Text, default="")
    is_submitted = Column(Boolean, default=False)
    submitted_at = Column(DateTime, nullable=True)
    source = Column(String(20), default="import")  # import | manual

    school_class = relationship("SchoolClass", back_populates="summary_rows")

    __table_args__ = (
        UniqueConstraint("class_id", "meal_date", name="uq_summary_class_date"),
        Index("ix_summary_date", "meal_date"),
    )


# ──────────────────────────────────────────────
# Discrepancies
# ──────────────────────────────────────────────

class Discrepancy(Base):
    __tablename__ = "discrepancies"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("school_classes.id"), nullable=False)
    meal_date = Column(Date, nullable=False)
    previous_date = Column(Date, nullable=False)
    upload_id = Column(Integer, ForeignKey("meal_uploads.id"), nullable=True)
    status = Column(SAEnum(DiscrepancyStatus), default=DiscrepancyStatus.NEW)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    items = relationship("DiscrepancyItem", back_populates="discrepancy", cascade="all, delete-orphan")


class DiscrepancyItem(Base):
    __tablename__ = "discrepancy_items"

    id = Column(Integer, primary_key=True, index=True)
    discrepancy_id = Column(Integer, ForeignKey("discrepancies.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    old_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    severity = Column(String(20), default="warning")  # info, warning, error
    student_name = Column(String(255), nullable=True)

    discrepancy = relationship("Discrepancy", back_populates="items")


# ──────────────────────────────────────────────
# Manual Edits
# ──────────────────────────────────────────────

class ManualEdit(Base):
    __tablename__ = "manual_edits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    table_name = Column(String(100), nullable=False)
    record_id = Column(Integer, nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ──────────────────────────────────────────────
# Email Dispatches
# ──────────────────────────────────────────────

class EmailDispatch(Base):
    __tablename__ = "email_dispatches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    meal_date = Column(Date, nullable=True)
    month = Column(Integer, nullable=True)
    year = Column(Integer, nullable=True)
    status = Column(String(20), default="pending")  # pending, sent, failed
    error_message = Column(Text, nullable=True)
    summary_zip_path = Column(String(1000), nullable=True)
    tabels_zip_path = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)


# ──────────────────────────────────────────────
# Audit Log
# ──────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, default="")
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")
