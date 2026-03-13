"""
Excel parser for school meal tabel files (.xls / .xlsx).

Supports two tabel formats found in real files:
1. OLD FORMAT (elementary, 1-4 grades): weekly tabel with dates as columns,
   завтрак/обед/полдник per date.
2. NEW FORMAT (5-11 grades): daily tabel with Авангард and Любава columns,
   plus totals for breakfasts, lunches, and ШВЕД.

The parser auto-detects format by looking for "Авангард" or "Любава" headers.
"""
import re
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import xlrd

logger = logging.getLogger(__name__)


@dataclass
class ParsedStudent:
    row_number: int
    full_name: str
    benefit_raw: str | None = None
    notes: str = ""
    avangard_breakfast: int = 0
    avangard_lunch: int = 0
    avangard_shved: int = 0
    lyubava_breakfast: int = 0
    lyubava_lunch: int = 0
    lyubava_shved: int = 0
    total_breakfasts: int = 0
    total_lunches: int = 0
    total_shved: int = 0


@dataclass
class ParsedTabel:
    class_name: str = ""
    class_grade: int = 0
    class_letter: str = ""
    period_text: str = ""
    meal_date: date | None = None
    school_name: str = ""
    sheet_name: str = ""
    students: list[ParsedStudent] = field(default_factory=list)
    total_students: int = 0
    format_type: str = "new"  # "new" (Авангард/Любава) or "old" (weekly)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _safe_int(val) -> int:
    if val is None or val == "":
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _clean_name(name: str) -> str:
    """Remove extra whitespace, trailing notes like '- НЕТ КАРТЫ'."""
    name = str(name).strip()
    name = re.sub(r"\s+", " ", name)
    return name


def _extract_notes(name: str) -> tuple[str, str]:
    """Split 'Жуков Михаил - НЕТ КАРТЫ' -> ('Жуков Михаил', 'НЕТ КАРТЫ')."""
    parts = name.split("-", 1)
    if len(parts) == 2 and len(parts[1].strip()) > 2:
        return parts[0].strip(), parts[1].strip()
    return name, ""


def _parse_class_name(raw: str) -> tuple[str, int, str]:
    """Parse 'Класс 10 \"А\"' -> ('10-а', 10, 'а')."""
    raw = str(raw).strip()
    raw = raw.replace("Класс", "").strip()
    raw = raw.replace('"', "").replace("«", "").replace("»", "")
    m = re.match(r"(\d+)\s*[\"'\s]*([А-Яа-яA-Za-z])", raw)
    if m:
        grade = int(m.group(1))
        letter = m.group(2).lower()
        return f"{grade}-{letter}", grade, letter
    return raw.lower().replace(" ", "-"), 0, ""


def _parse_date_from_period(text: str) -> date | None:
    """Extract date from period text like 'за период 13.03.2026г.'"""
    text = str(text)
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None


def select_best_sheet(workbook: xlrd.Book) -> tuple[str, str]:
    """
    Select the best sheet to parse from the workbook.
    Returns (sheet_name, reason).

    Strategy:
    1. Look for sheets with recent dates in the period row.
    2. Prefer sheets with Авангард/Любава format (newer template).
    3. Skip sheets that are clearly auxiliary (Лист2, etc.).
    """
    candidates = []
    skip_names = {"лист2"}

    for sname in workbook.sheet_names():
        if sname.strip().lower() in skip_names:
            continue
        sh = workbook.sheet_by_name(sname)
        if sh.nrows < 10:
            continue

        score = 0
        parsed_date = None
        has_avangard = False

        for r in range(min(15, sh.nrows)):
            for c in range(min(30, sh.ncols)):
                val = str(sh.cell_value(r, c)).strip()
                if not val:
                    continue
                val_lower = val.lower()
                if "авангард" in val_lower:
                    has_avangard = True
                    score += 10
                if "любава" in val_lower:
                    score += 10
                if "за период" in val_lower or re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", val):
                    d = _parse_date_from_period(val)
                    if d:
                        parsed_date = d
                        # More recent dates get higher scores
                        score += 5 + (d.year - 2020)

        candidates.append((sname, score, parsed_date, has_avangard))

    if not candidates:
        return workbook.sheet_names()[0], "fallback to first sheet"

    candidates.sort(key=lambda x: x[1], reverse=True)
    best = candidates[0]
    return best[0], f"score={best[1]}, date={best[2]}, avangard={best[3]}"


def parse_tabel_sheet(sheet: xlrd.sheet.Sheet, sheet_name: str) -> ParsedTabel:
    """Parse a single sheet from a tabel workbook."""
    result = ParsedTabel(sheet_name=sheet_name)

    # Find key rows by scanning first 20 rows
    class_row = -1
    period_row = -1
    header_row = -1
    has_avangard = False

    for r in range(min(20, sheet.nrows)):
        for c in range(min(35, sheet.ncols)):
            val = str(sheet.cell_value(r, c)).strip()
            if not val:
                continue
            val_lower = val.lower()
            if val_lower.startswith("класс"):
                class_row = r
                raw = val
                result.class_name, result.class_grade, result.class_letter = _parse_class_name(raw)
            if "за период" in val_lower or (re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", val) and "период" not in val_lower and r < 10):
                period_row = r
                result.period_text = val
                result.meal_date = _parse_date_from_period(val)
            if "авангард" in val_lower:
                has_avangard = True
                header_row = r
            if "учреждение" in val_lower:
                for cc in range(c + 1, min(c + 15, sheet.ncols)):
                    sv = str(sheet.cell_value(r, cc)).strip()
                    if sv:
                        result.school_name = sv
                        break

    if has_avangard:
        result.format_type = "new"
        result = _parse_new_format(sheet, result, header_row)
    else:
        result.format_type = "old"
        result = _parse_old_format(sheet, result)

    result.total_students = len(result.students)
    return result


def _parse_new_format(sheet: xlrd.sheet.Sheet, result: ParsedTabel, header_row: int) -> ParsedTabel:
    """
    Parse new format (5-11 grades) with Авангард and Любава columns.

    Layout (from real file analysis):
      Row header_row: col 15=Авангард, col 18=Любава, col 21=Всего завтраков, col 25=Всего обедов, col 29=Всего ШВЕДов
      Row header_row+1: col 15=завтрак, col 16=обед, col 17=ШВ.стол, col 18=завтрак, col 19=обед, col 20=ШВ.стол
      Data starts at header_row+3 (after column number row)
    """
    # Detect column positions from header
    col_av_breakfast = 15
    col_av_lunch = 16
    col_av_shved = 17
    col_ly_breakfast = 18
    col_ly_lunch = 19
    col_ly_shved = 20
    col_total_bf = 21
    col_total_lunch = 25
    col_total_shved = 29

    # Try to auto-detect from actual headers
    if header_row >= 0:
        for c in range(sheet.ncols):
            val = str(sheet.cell_value(header_row, c)).strip().lower()
            if "авангард" in val:
                col_av_breakfast = c
                col_av_lunch = c + 1
                col_av_shved = c + 2
            elif "любава" in val:
                col_ly_breakfast = c
                col_ly_lunch = c + 1
                col_ly_shved = c + 2
            elif "всего завтраков" in val:
                col_total_bf = c
            elif "всего обедов" in val:
                col_total_lunch = c
            elif "всего швед" in val:
                col_total_shved = c

    # Data rows start after header + subheader + column numbers
    data_start = header_row + 3

    for r in range(data_start, sheet.nrows):
        # Column 0 = row number, Column 2 = student name
        num_val = sheet.cell_value(r, 0)
        name_val = str(sheet.cell_value(r, 2)).strip()

        if not name_val:
            continue
        # Stop at summary rows
        name_lower = name_val.lower()
        if any(kw in name_lower for kw in ["итого", "всего", "подпись", "учитель", "ответственный"]):
            break
        # Check if this is a student row (has a row number)
        if not _safe_int(num_val):
            continue

        clean_name, notes = _extract_notes(name_val)
        benefit_raw = str(sheet.cell_value(r, 11)).strip() if sheet.ncols > 11 else ""
        if benefit_raw in ("", "0", "0.0"):
            benefit_raw = None

        student = ParsedStudent(
            row_number=_safe_int(num_val),
            full_name=_clean_name(clean_name),
            benefit_raw=benefit_raw,
            notes=notes,
            avangard_breakfast=_safe_int(sheet.cell_value(r, col_av_breakfast)),
            avangard_lunch=_safe_int(sheet.cell_value(r, col_av_lunch)),
            avangard_shved=_safe_int(sheet.cell_value(r, col_av_shved)),
            lyubava_breakfast=_safe_int(sheet.cell_value(r, col_ly_breakfast)),
            lyubava_lunch=_safe_int(sheet.cell_value(r, col_ly_lunch)),
            lyubava_shved=_safe_int(sheet.cell_value(r, col_ly_shved)),
            total_breakfasts=_safe_int(sheet.cell_value(r, col_total_bf)),
            total_lunches=_safe_int(sheet.cell_value(r, col_total_lunch)),
            total_shved=_safe_int(sheet.cell_value(r, col_total_shved)),
        )

        # Recompute totals if file has formula-based values that didn't resolve
        computed_bf = student.avangard_breakfast + student.lyubava_breakfast
        computed_lunch = student.avangard_lunch + student.lyubava_lunch
        computed_shved = student.avangard_shved + student.lyubava_shved

        if student.total_breakfasts == 0 and computed_bf > 0:
            student.total_breakfasts = computed_bf
        if student.total_lunches == 0 and computed_lunch > 0:
            student.total_lunches = computed_lunch
        if student.total_shved == 0 and computed_shved > 0:
            student.total_shved = computed_shved

        result.students.append(student)

    if not result.students:
        result.errors.append("Не удалось найти данные учеников на листе")

    return result


def _parse_old_format(sheet: xlrd.sheet.Sheet, result: ParsedTabel) -> ParsedTabel:
    """
    Parse old format (elementary 1-4 grades) with weekly dates.

    Layout:
      Row 12: headers (№, ФИО, льготы, ДАТА)
      Row 14: actual dates (19.10., 20.10., ...)
      Row 15: day of week
      Row 16: завтрак/обед/полдник for each day
      Row 18+: student data
    """
    # Find the date header row and student data
    date_cols = []
    header_row = -1
    benefit_col = 11  # default

    for r in range(min(20, sheet.nrows)):
        val = str(sheet.cell_value(r, 2)).strip().lower()
        if "фамилия" in val:
            header_row = r
        # Look for date patterns in columns 15+
        for c in range(15, min(40, sheet.ncols)):
            cell_val = str(sheet.cell_value(r, c)).strip()
            if re.match(r"\d{1,2}\.\d{1,2}\.", cell_val):
                date_cols.append((c, cell_val))

    # For old format, sum all breakfast (col offset 0) and lunch (col offset 1)
    # per date block. Each date has 3 columns: завтрак, обед, полдник
    data_start = header_row + 6 if header_row >= 0 else 18

    for r in range(data_start, sheet.nrows):
        num_val = sheet.cell_value(r, 0)
        name_val = str(sheet.cell_value(r, 2)).strip()

        if not name_val or not _safe_int(num_val):
            continue
        name_lower = name_val.lower()
        if any(kw in name_lower for kw in ["итого", "всего"]):
            break

        clean_name, notes = _extract_notes(name_val)
        benefit_raw = str(sheet.cell_value(r, benefit_col)).strip()
        if benefit_raw in ("", "0", "0.0"):
            benefit_raw = None

        total_bf = 0
        total_lunch = 0
        # Sum across all date columns (each date = 3 cols: breakfast, lunch, poldnik)
        for dc, _ in date_cols:
            total_bf += _safe_int(sheet.cell_value(r, dc))      # завтрак
            total_lunch += _safe_int(sheet.cell_value(r, dc + 1))  # обед

        student = ParsedStudent(
            row_number=_safe_int(num_val),
            full_name=_clean_name(clean_name),
            benefit_raw=benefit_raw,
            notes=notes,
            total_breakfasts=total_bf,
            total_lunches=total_lunch,
        )
        result.students.append(student)

    if not result.students:
        result.errors.append("Не удалось найти данные учеников (старый формат)")

    return result


def parse_tabel_file(file_path: str | Path) -> ParsedTabel:
    """Main entry point: parse a tabel .xls file and return structured data."""
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in (".xls", ".xlsx"):
        raise ValueError(f"Неподдерживаемый формат файла: {suffix}")

    wb = xlrd.open_workbook(str(file_path))
    sheet_name, reason = select_best_sheet(wb)
    logger.info(f"Selected sheet '{sheet_name}': {reason}")

    sheet = wb.sheet_by_name(sheet_name)
    result = parse_tabel_sheet(sheet, sheet_name)

    if not result.class_name:
        result.warnings.append("Не удалось определить класс из файла")
    if not result.meal_date:
        result.warnings.append("Не удалось определить дату из файла")

    logger.info(
        f"Parsed: class={result.class_name}, date={result.meal_date}, "
        f"students={len(result.students)}, format={result.format_type}"
    )
    return result
