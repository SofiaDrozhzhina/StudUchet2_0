import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import date, datetime
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "storage" / "documents"
TEMPLATES = ROOT / "storage" / "templates"
ARCHIVE = ROOT / "storage" / "archive"
for folder in (DOCS, TEMPLATES, ARCHIVE):
    folder.mkdir(parents=True, exist_ok=True)

# Готовые популярные причины для заявления на матпомощь
AID_REASONS = [
    "проживаю в неполной семье",
    "из многодетной семьи",
    "в связи с потерей кормильца",
    "являюсь сиротой (оставшимся без попечения родителей)",
    "являюсь ребенком-инвалидом (инвалидом I, II группы)",
    "в связи с тяжелым материальным положением в семье",
    "в связи с необходимостью дорогостоящего лечения / покупки медикаментов",
    "в связи с чрезвычайными обстоятельствами (пожар, утрата имущества)"
]

def safe_name(name):
    bad = '<>:"/\\|?*'
    for char in bad:
        name = name.replace(char, "_")
    return name.strip() or "document"

def copy_into(source, folder, prefix=""):
    source = Path(source)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (prefix + safe_name(source.name))
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return str(target.resolve())

def open_file(path):
    path = str(Path(path).resolve())
    if not os.path.exists(path):
        raise FileNotFoundError("Файл не найден: " + path)
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])

def print_file(path):
    path = str(Path(path).resolve())
    if not os.path.exists(path):
        raise FileNotFoundError("Файл не найден: " + path)
    if not sys.platform.startswith("win"):
        open_file(path)
        return
    os.startfile(path, "print")

# ================= СКЛОНЕНИЕ ФИО В РОДИТЕЛЬНЫЙ ПАДЕЖ =================
def inflect_fio_genitive(last_name, first_name, middle_name):
    ln = (last_name or "").strip()
    fn = (first_name or "").strip()
    mn = (middle_name or "").strip()

    is_female = mn.endswith("на") or mn.endswith("кызы") or ln.endswith(("ова", "ева", "ина", "ына", "ая"))

    ln_gen = ln
    if is_female:
        if ln.endswith(("ова", "ева", "ина", "ына")):
            ln_gen = ln[:-1] + "ой"
        elif ln.endswith("ая"):
            ln_gen = ln[:-2] + "ой"
    else:
        if ln.endswith(("ов", "ев", "ин", "ын")):
            ln_gen = ln + "а"
        elif ln.endswith(("ский", "цкий")):
            ln_gen = ln[:-2] + "ого"
        elif ln.endswith(("ий", "ый")):
            ln_gen = ln[:-2] + "ого"
        elif ln and ln[-1] not in "аеёиоуыэюяьъ":
            ln_gen = ln + "а"
        elif ln.endswith("ь"):
            ln_gen = ln[:-1] + "я"

    fn_gen = fn
    if is_female:
        if fn.endswith("ия"):
            fn_gen = fn[:-1] + "и"
        elif fn.endswith("я"):
            fn_gen = fn[:-1] + "и"
        elif fn.endswith("а"):
            if fn[-2:] in ("га", "ка", "ха", "жа", "ча", "ша", "ща"):
                fn_gen = fn[:-1] + "и"
            else:
                fn_gen = fn[:-1] + "ы"
        elif fn.endswith("ь"):
            fn_gen = fn[:-1] + "и"
    else:
        if fn.endswith("й"):
            fn_gen = fn[:-1] + "я"
        elif fn.endswith("ь"):
            fn_gen = fn[:-1] + "я"
        elif fn and fn[-1] not in "аеёиоуыэюяьъ":
            fn_gen = fn + "а"
        elif fn.endswith("а"):
            fn_gen = fn[:-1] + "ы"
        elif fn.endswith("я"):
            fn_gen = fn[:-1] + "и"

    mn_gen = mn
    if is_female:
        if mn.endswith("на"):
            mn_gen = mn[:-1] + "ы"
    else:
        if mn.endswith(("ич", "лы")):
            mn_gen = mn + "а"

    full_fio_gen = " ".join(filter(None, [ln_gen, fn_gen, mn_gen]))
    student_word = "студентки" if is_female else "студента"
    return full_fio_gen, student_word

# ================= ШАБЛОНЫ DOCX / XLSX =================
def ensure_material_aid_template():
    """Создает стандартный DOCX-шаблон заявления, если его еще нет."""
    template_path = TEMPLATES / "Шаблон_Заявление_на_матпомощь.docx"
    if template_path.exists():
        return str(template_path)

    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(0.8)

    header_lines = [
        "Ректору ГГТУ",
        "доценту Скударевой Г.Н.",
        "{{СловоСтудент}} {{Курс}} курса,",
        "группы {{Группа}}",
        "Ликино-Дулевского",
        "политехнического колледжа-филиала ГГТУ",
        "{{ФИО_Родительный}}"
    ]
    for line in header_lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.05
        run = p.add_run(line)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = p_title.add_run("заявление.")
    run_t.font.name = "Times New Roman"
    run_t.font.size = Pt(13)
    run_t.bold = True
    p_title.paragraph_format.space_after = Pt(12)

    p_body = doc.add_paragraph()
    p_body.paragraph_format.first_line_indent = Inches(0.5)
    p_body.paragraph_format.line_spacing = 1.25
    p_body.paragraph_format.space_after = Pt(6)
    r1 = p_body.add_run("Прошу разрешить оказать мне единовременную материальную помощь в связи с тяжелым материальным положением: ")
    r1.font.name = "Times New Roman"; r1.font.size = Pt(12)
    r2 = p_body.add_run("{{Причина}}.")
    r2.font.name = "Times New Roman"; r2.font.size = Pt(12)

    p_doc = doc.add_paragraph()
    p_doc.paragraph_format.first_line_indent = Inches(0.5)
    p_doc.paragraph_format.space_after = Pt(20)
    r_doc = p_doc.add_run("Необходимые документы прилагаются.")
    r_doc.font.name = "Times New Roman"; r_doc.font.size = Pt(12)

    p_date = doc.add_paragraph()
    p_date.paragraph_format.space_after = Pt(36)
    p_date.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_date = p_date.add_run("Дата: {{Дата}}          Подпись: ________________")
    r_date.font.name = "Times New Roman"; r_date.font.size = Pt(12)

    signs = [
        ("Директор ЛДПК-филиала ГГТУ", "Д.Р. Сабитова"),
        ("Социальный педагог", "В.В. Лытькова"),
        ("Классный руководитель", "О.М. Селиверстова"),
        ("Староста группы", "{{Староста}}")
    ]
    table = doc.add_table(rows=len(signs), cols=3)
    table.autofit = True
    for idx, (role, person) in enumerate(signs):
        row = table.rows[idx]
        p0 = row.cells[0].paragraphs[0]
        r = p0.add_run(role); r.font.name = "Times New Roman"; r.font.size = Pt(11)
        p1 = row.cells[1].paragraphs[0]
        r = p1.add_run("________________"); r.font.name = "Times New Roman"; r.font.size = Pt(11)
        p2 = row.cells[2].paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = p2.add_run(person); r.font.name = "Times New Roman"; r.font.size = Pt(11)

    doc.save(template_path)
    return str(template_path)

def ensure_social_passport_blank_template():
    """Создает пустой чистый бланк социального паспорта."""
    template_path = TEMPLATES / "Шаблон_Социальный_паспорт.xlsx"
    if template_path.exists():
        return str(template_path)
    # Создаем пустой шаблон с 25 пустыми строками
    generate_social_passport_xlsx("_________ (название группы)", [], str(template_path), blank_rows=25)
    return str(template_path)

def fill_docx(template_path, output_path, values):
    """Заполняет плейсхолдеры, не пересоздавая абзацы и не сбрасывая оформление Word."""
    doc = Document(template_path)

    def replace_token_in_paragraph(paragraph, token, replacement):
        # Токен может быть разбит Word на несколько runs. Собираем текст,
        # находим диапазон и меняем только затронутые runs, сохраняя их стиль.
        replacement = str(replacement or "")
        while True:
            runs = paragraph.runs
            full_text = "".join(run.text for run in runs)
            start = full_text.find(token)
            if start < 0:
                break
            end = start + len(token)
            offsets = []
            cursor = 0
            for run in runs:
                offsets.append((cursor, cursor + len(run.text)))
                cursor += len(run.text)

            first_idx = next((i for i, (a, b) in enumerate(offsets) if a <= start < b), None)
            last_idx = next((i for i, (a, b) in enumerate(offsets) if a < end <= b), None)
            if first_idx is None or last_idx is None:
                break

            first_start = start - offsets[first_idx][0]
            last_end = end - offsets[last_idx][0]
            if first_idx == last_idx:
                text = runs[first_idx].text
                runs[first_idx].text = text[:first_start] + replacement + text[last_end:]
            else:
                first_text = runs[first_idx].text
                last_text = runs[last_idx].text
                runs[first_idx].text = first_text[:first_start] + replacement
                for idx in range(first_idx + 1, last_idx):
                    runs[idx].text = ""
                runs[last_idx].text = last_text[last_end:]

    def iter_paragraphs(container):
        for paragraph in container.paragraphs:
            yield paragraph
        for table in container.tables:
            for row in table.rows:
                for cell in row.cells:
                    yield from iter_paragraphs(cell)

    for paragraph in iter_paragraphs(doc):
        for key, value in values.items():
            replace_token_in_paragraph(paragraph, "{{" + key + "}}", value)

    # Плейсхолдеры в колонтитулах тоже заполняются без изменения форматирования.
    for section in doc.sections:
        for part in (section.header, section.footer, section.first_page_header,
                     section.first_page_footer, section.even_page_header, section.even_page_footer):
            for paragraph in iter_paragraphs(part):
                for key, value in values.items():
                    replace_token_in_paragraph(paragraph, "{{" + key + "}}", value)

    doc.save(output_path)
    return output_path

def fill_xlsx(template_path, output_path, values):
    wb = load_workbook(template_path)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    val = cell.value
                    for k, v in values.items():
                        val = val.replace("{{" + k + "}}", str(v or ""))
                    cell.value = val
    wb.save(output_path)
    return output_path

# ================= СОЦИАЛЬНЫЙ ПАСПОРТ ГРУППЫ (EXCEL) =================
def generate_social_passport_xlsx(group_name, students, output_path, cur_year="2025-2026", blank_rows=0):
    wb = Workbook()
    ws = wb.active
    ws.title = "Социальный паспорт"
    ws.views.sheetView[0].showGridLines = True

    font_inst = Font(name="Calibri", size=9, bold=True, color="555555")
    font_title = Font(name="Calibri", size=13, bold=True)
    font_h = Font(name="Calibri", size=9, bold=True)
    font_data = Font(name="Calibri", size=10)
    font_itogo = Font(name="Calibri", size=10, bold=True)
    fill_h = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    fill_itogo = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='A0AEC0'), right=Side(style='thin', color='A0AEC0'),
        top=Side(style='thin', color='A0AEC0'), bottom=Side(style='thin', color='A0AEC0')
    )
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='center')

    # Инструкция
    ws.merge_cells("A1:V1")
    ws["A1"] = 'ЗАПОЛНИТЕ ТАБЛИЦУ, УКАЖИТЕ НАПРОТИВ КАЖДОГО СТУДЕНТА "1" ЕСЛИ СООТВЕТСТВУЕТ, ОСТАВЬТЕ ПУСТУЮ ЯЧЕЙКУ, ЕСЛИ НЕ СООТВЕТСТВУЕТ.'
    ws["A1"].font = font_inst
    ws.row_dimensions[1].height = 22

    # Заголовок
    ws.merge_cells("A2:V2")
    ws["A2"] = f"Сведения о студентах группы {group_name} на {cur_year} учебный год"
    ws["A2"].font = font_title
    ws.row_dimensions[2].height = 28

    # Двухэтажная шапка
    headers_top = [
        ("A4:A5", "№"),
        ("B4:B5", "ФИО (полностью)"),
        ("C4:C5", "несовершеннолетний"),
        ("D4:F4", "Неполная семья"),
        ("G4:G5", "Многодетная семья"),
        ("H4:H5", "малообеспеченные"),
        ("I4:I5", "Ребенок-инвалид"),
        ("J4:J5", "Ребенок-сирота"),
        ("K4:K5", "Неблагополучная семья"),
        ("L4:L5", "Студенты из семей «Чернобыльцев»"),
        ("M4:M5", "Студенты из семей переселенцев"),
        ("N4:N5", "Охвачены доп. образованием"),
        ("O4:Q4", "Студентов, получающих стипендию"),
        ("R4:R5", "Студенческие семьи"),
        ("S4:S5", "Студенты, имеющие детей"),
        ("T4:T5", "Семьи, где родители-инвалиды"),
        ("U4:U5", "Семьи с родителями пенсионерами"),
        ("V4:V5", "Группа риска")
    ]
    for cell_range, text in headers_top:
        ws.merge_cells(cell_range)
        ws[cell_range.split(":")[0]].value = text

    ws["D5"] = "родители разведены"
    ws["E5"] = "мать-одиночка"
    ws["F5"] = "Потеря кормильца"
    ws["O5"] = "академическую"
    ws["P5"] = "социальную"
    ws["Q5"] = "Губернатора"

    ws.row_dimensions[4].height = 28
    ws.row_dimensions[5].height = 40
    for r in range(4, 6):
        for col in range(1, 23):
            c = ws.cell(row=r, column=col)
            c.font = font_h; c.fill = fill_h; c.border = thin_border; c.alignment = align_center

    # Заполнение студентов
    start_row = 6
    today = date.today()
    total_count = len(students) if students else blank_rows

    for idx in range(1, total_count + 1):
        curr_row = start_row + idx - 1
        fio = ""
        is_minor = ""

        if students and idx <= len(students):
            s = students[idx - 1]
            fio = " ".join(filter(None, [s["last_name"], s["first_name"], s.get("middle_name", "")]))
            bdate = s.get("birth_date")
            if bdate:
                age = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
                if age < 18:
                    is_minor = 1

        ws.cell(row=curr_row, column=1, value=idx)
        ws.cell(row=curr_row, column=2, value=fio)
        ws.cell(row=curr_row, column=3, value=is_minor)

        for col in range(1, 23):
            cell = ws.cell(row=curr_row, column=col)
            cell.font = font_data
            cell.border = thin_border
            cell.alignment = align_left if col == 2 else align_center
        ws.row_dimensions[curr_row].height = 20

    end_row = max(start_row + total_count - 1, start_row)

    # ИТОГО
    itogo_row = end_row + 1
    ws.cell(row=itogo_row, column=1, value="итого:")
    ws.cell(row=itogo_row, column=2, value=f"=COUNTA(B{start_row}:B{end_row})")

    for col in range(3, 23):
        col_letter = get_column_letter(col)
        ws.cell(row=itogo_row, column=col, value=f"=SUM({col_letter}{start_row}:{col_letter}{end_row})")

    for col in range(1, 23):
        c = ws.cell(row=itogo_row, column=col)
        c.font = font_itogo; c.fill = fill_itogo; c.border = thin_border; c.alignment = align_center
    ws.row_dimensions[itogo_row].height = 22

    # Подписи
    sign_row = itogo_row + 2
    ws.cell(row=sign_row, column=2, value="Классный руководитель: __________________ / Селиверстова О.М. /").font = font_data
    ws.cell(row=sign_row + 2, column=2, value=f"Число: « {today.strftime('%d')} » {today.strftime('%m %Y')} г.").font = font_data

    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 16
    for c in range(4, 23):
        ws.column_dimensions[get_column_letter(c)].width = 13

    wb.save(output_path)
    return output_path

def student_values(student, group, reason="", aid_fio_gen="", student_word=""):
    full_name = " ".join(filter(None, [
        student.get("last_name", ""), student.get("first_name", ""), student.get("middle_name", "")
    ]))
    birth = student.get("birth_date")
    age = ""
    if birth:
        today = date.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))

    today_str = date.today().strftime("« %d » %m %Y г.")

    return {
        "ФИО": full_name,
        "ФИО_Родительный": aid_fio_gen or full_name,
        "СловоСтудент": student_word or "студента",
        "Причина": reason,
        "Дата": today_str,
        "Староста": "С.Ю. Дрожжина",
        "Фамилия": student.get("last_name", ""),
        "Имя": student.get("first_name", ""),
        "Отчество": student.get("middle_name", ""),
        "Группа": group.get("name", "") if group else "",
        "Курс": group.get("course", "") if group else "",
        "ДатаРождения": birth.strftime("%d.%m.%Y") if birth else "",
        "Возраст": age,
        "Номер": student.get("student_number", ""),
        "СНИЛС": student.get("snils", ""),
        "Телефон": student.get("phone", ""),
        "Email": student.get("email", ""),
        "Специальность": group.get("specialty_name", "") if group else "",
        "Адрес": student.get("address", ""),
    }