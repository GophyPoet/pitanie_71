from datetime import date, datetime
from pydantic import BaseModel, EmailStr
from app.models.models import UserRole, UploadStatus, DiscrepancyStatus


# ──── Auth ────
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    full_name: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ──── User ────
class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str
    role: UserRole = UserRole.TEACHER
    class_ids: list[int] = []

class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class UserWithClasses(UserOut):
    assigned_classes: list["SchoolClassOut"] = []


# ──── School Class ────
class SchoolClassCreate(BaseModel):
    name: str
    grade: int
    letter: str
    student_count: int = 0

class SchoolClassOut(BaseModel):
    id: int
    name: str
    grade: int
    letter: str
    student_count: int
    is_active: bool
    class Config:
        from_attributes = True


# ──── Benefit Type ────
class BenefitTypeOut(BaseModel):
    id: int
    code: str
    name: str
    description: str
    class Config:
        from_attributes = True

class BenefitTypeCreate(BaseModel):
    code: str
    name: str
    description: str = ""


# ──── Upload ────
class UploadOut(BaseModel):
    id: int
    teacher_id: int
    class_id: int
    class_name: str = ""
    teacher_name: str = ""
    meal_date: date
    month: int
    year: int
    original_filename: str
    status: UploadStatus
    error_message: str | None
    version: int
    is_current: bool
    sheet_name: str | None
    parsed_class_name: str | None
    parsed_date: str | None
    created_at: datetime
    class Config:
        from_attributes = True


# ──── Student Meal Record ────
class StudentMealRecordOut(BaseModel):
    id: int
    student_name_raw: str
    benefit_raw: str | None
    avangard_breakfast: int
    avangard_lunch: int
    avangard_shved: int
    lyubava_breakfast: int
    lyubava_lunch: int
    lyubava_shved: int
    total_breakfasts: int
    total_lunches: int
    total_shved: int
    class Config:
        from_attributes = True


# ──── Summary Row ────
class SummaryRowOut(BaseModel):
    id: int
    class_id: int
    class_name: str = ""
    meal_date: date
    teacher_name: str
    student_count: int
    eating_count: int
    parent_breakfast: int
    parent_lunch: int
    parent_lunch_shved: int
    benefit_breakfast: int
    benefit_lunch: int
    free_breakfast: int
    free_lunch: int
    multichild_breakfast: int
    sozvezdie_breakfast: int
    mobilized_breakfast_lunch: int
    mobilized_count: int
    ovz_breakfast_lunch: int
    ovz_count: int
    sozvezdie_ovz_breakfast_lunch: int
    sozvezdie_ovz_count: int
    total_breakfasts: int
    total_lunches: int
    notes: str
    is_submitted: bool
    submitted_at: datetime | None
    source: str
    class Config:
        from_attributes = True

class SummaryRowUpdate(BaseModel):
    student_count: int | None = None
    eating_count: int | None = None
    parent_breakfast: int | None = None
    parent_lunch: int | None = None
    parent_lunch_shved: int | None = None
    benefit_breakfast: int | None = None
    benefit_lunch: int | None = None
    free_breakfast: int | None = None
    free_lunch: int | None = None
    multichild_breakfast: int | None = None
    sozvezdie_breakfast: int | None = None
    mobilized_breakfast_lunch: int | None = None
    mobilized_count: int | None = None
    ovz_breakfast_lunch: int | None = None
    ovz_count: int | None = None
    sozvezdie_ovz_breakfast_lunch: int | None = None
    sozvezdie_ovz_count: int | None = None
    total_breakfasts: int | None = None
    total_lunches: int | None = None
    notes: str | None = None
    comment: str = ""


# ──── Monthly Plan ────
class MonthlyPlanCreate(BaseModel):
    year: int
    month: int

class MonthlyPlanDayOut(BaseModel):
    id: int
    date: date
    is_school_day: bool
    class Config:
        from_attributes = True

class MonthlyPlanOut(BaseModel):
    id: int
    year: int
    month: int
    created_at: datetime
    days: list[MonthlyPlanDayOut] = []
    class Config:
        from_attributes = True


# ──── Discrepancy ────
class DiscrepancyItemOut(BaseModel):
    id: int
    field_name: str
    description: str
    old_value: str | None
    new_value: str | None
    severity: str
    student_name: str | None
    class Config:
        from_attributes = True

class DiscrepancyOut(BaseModel):
    id: int
    class_id: int
    class_name: str = ""
    meal_date: date
    previous_date: date
    status: DiscrepancyStatus
    items: list[DiscrepancyItemOut] = []
    created_at: datetime
    class Config:
        from_attributes = True


# ──── Submission Status ────
class ClassSubmissionStatus(BaseModel):
    class_id: int
    class_name: str
    meal_date: date
    is_submitted: bool
    teacher_name: str = ""
    submitted_at: datetime | None = None
    upload_id: int | None = None
    version: int = 0
    has_discrepancies: bool = False


# ──── Email ────
class EmailSendRequest(BaseModel):
    recipient_email: EmailStr
    meal_date: date | None = None
    month: int | None = None
    year: int | None = None
    subject: str = ""


# ──── Dashboard Stats ────
class DashboardStats(BaseModel):
    total_classes: int
    submitted_today: int
    not_submitted_today: int
    total_eating_today: int
    total_breakfasts_today: int
    total_lunches_today: int
    discrepancies_new: int
