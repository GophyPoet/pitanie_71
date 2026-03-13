"""
Seed script to populate initial data: admin user, classes, benefit types.
Run: python seed.py
"""
from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.models import (
    User, UserRole, SchoolClass, BenefitType, TeacherClassAssignment,
)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ──── Benefit Types ────
benefit_types = [
    ("сво", "СВО", "Дети мобилизованных (СВО)"),
    ("мн", "МН", "Многодетные семьи"),
    ("мног.", "Мног.", "Многодетные семьи (альт. обозначение)"),
    ("овз", "ОВЗ", "Ограниченные возможности здоровья"),
    ("б/к", "Б/К", "Без карты / бесплатное питание"),
    ("б/о", "Б/О", "Без оплаты / бесплатное питание"),
]
for code, name, desc in benefit_types:
    if not db.query(BenefitType).filter(BenefitType.code == code).first():
        db.add(BenefitType(code=code, name=name, description=desc))

# ──── School Classes ────
classes_data = [
    # (name, grade, letter, student_count)
    ("1-а", 1, "а", 30), ("1-б", 1, "б", 30),
    ("2-а", 2, "а", 26), ("2-б", 2, "б", 27), ("2-в", 2, "в", 25),
    ("3-а", 3, "а", 23), ("3-б", 3, "б", 27), ("3-в", 3, "в", 26), ("3-г", 3, "г", 25),
    ("4-а", 4, "а", 25), ("4-б", 4, "б", 27), ("4-в", 4, "в", 28), ("4-г", 4, "г", 28),
    ("5-а", 5, "а", 28), ("5-б", 5, "б", 27), ("5-в", 5, "в", 29), ("5-г", 5, "г", 28),
    ("6-а", 6, "а", 30), ("6-б", 6, "б", 29), ("6-в", 6, "в", 28), ("6-г", 6, "г", 30),
    ("7-а", 7, "а", 30), ("7-б", 7, "б", 30), ("7-в", 7, "в", 30), ("7-г", 7, "г", 29),
    ("8-а", 8, "а", 31), ("8-б", 8, "б", 29), ("8-в", 8, "в", 30), ("8-г", 8, "г", 26),
    ("9-а", 9, "а", 25), ("9-б", 9, "б", 28), ("9-в", 9, "в", 25), ("9-г", 9, "г", 25),
    ("10-а", 10, "а", 30),
    ("11-а", 11, "а", 26),
]
for name, grade, letter, count in classes_data:
    if not db.query(SchoolClass).filter(SchoolClass.name == name).first():
        db.add(SchoolClass(name=name, grade=grade, letter=letter, student_count=count))

db.commit()

# ──── Admin User ────
if not db.query(User).filter(User.username == "admin").first():
    admin = User(
        username="admin",
        full_name="Краснова Н.В.",
        hashed_password=hash_password("admin123"),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()

# ──── Sample Teacher ────
if not db.query(User).filter(User.username == "krasnova").first():
    teacher = User(
        username="krasnova",
        full_name="Краснова Н.В.",
        hashed_password=hash_password("teacher123"),
        role=UserRole.TEACHER,
    )
    db.add(teacher)
    db.flush()
    # Assign 10-а class
    sc = db.query(SchoolClass).filter(SchoolClass.name == "10-а").first()
    if sc:
        db.add(TeacherClassAssignment(teacher_id=teacher.id, class_id=sc.id))
    db.commit()

print("Seed completed!")
print(f"  - {len(benefit_types)} benefit types")
print(f"  - {len(classes_data)} classes")
print(f"  - Admin: admin / admin123")
print(f"  - Teacher: krasnova / teacher123 (class 10-а)")
db.close()
