import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import date, datetime
import customtkinter as ctk

import db
import documents

APP_TITLE = "СтудУчет — рабочее место классного руководителя"

ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

COLOR_PRIMARY = "#2563EB"       # Синий
COLOR_PRIMARY_HOVER = "#1D4ED8"
COLOR_SUCCESS = "#059669"       # Зеленый
COLOR_SUCCESS_HOVER = "#047857"
COLOR_WARNING = "#D97706"       # Оранжевый / Янтарный
COLOR_WARNING_HOVER = "#B45309"
COLOR_DANGER = "#DC2626"        # Красный
COLOR_DANGER_HOVER = "#B91C1C"
COLOR_NEUTRAL = "#475569"       # Серый
COLOR_NEUTRAL_HOVER = "#334155"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1280x800")
        self.minsize(1050, 680)

        self.selected_student_id = None
        self._sort_reverse = {}

        self._style_treeview()
        self._build_ui()
        self._seed_default_templates()
        self.refresh_all()

    def _seed_default_templates(self):
        """Гарантирует наличие шаблонов соц. паспорта и заявления в базе."""
        doc_aid = documents.ensure_material_aid_template()
        doc_soc = documents.ensure_social_passport_blank_template()

        existing = db.query("SELECT name FROM document_templates", fetch=True) or []
        names = {row["name"] for row in existing}

        if "Заявление на материальную помощь" not in names:
            db.query("""INSERT INTO document_templates(name, file_name, file_path, file_type, description)
                VALUES(%s, %s, %s, %s, %s)""",
                     ("Заявление на материальную помощь", Path(doc_aid).name, doc_aid, "docx", "Официальное заявление ректору ГГТУ с подписями"))

        if "Социальный паспорт группы" not in names:
            db.query("""INSERT INTO document_templates(name, file_name, file_path, file_type, description)
                VALUES(%s, %s, %s, %s, %s)""",
                     ("Социальный паспорт группы", Path(doc_soc).name, doc_soc, "xlsx", "Таблица социального паспорта группы со всеми категориями"))

    def _style_treeview(self):
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except tk.TclError: pass

        style.configure("Treeview",
                        background="#FFFFFF",
                        foreground="#0F172A",
                        fieldbackground="#FFFFFF",
                        borderwidth=1,
                        rowheight=32,
                        font=("Segoe UI", 10))

        style.map("Treeview",
                  background=[("selected", "#DBEAFE")],
                  foreground=[("selected", "#1E3A8A")])

        style.configure("Treeview.Heading",
                        background="#E2E8F0",
                        foreground="#1E293B",
                        relief="flat",
                        padding=8,
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview.Heading", background=[("active", "#CBD5E1")])

    def _build_ui(self):
        header = ctk.CTkFrame(self, fg_color="#FFFFFF", height=65, corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(brand, text="СтудУчет", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                     text_color="#1E293B").pack(side="left")

        badge = ctk.CTkLabel(brand, text="  КЛАССНЫЙ РУКОВОДИТЕЛЬ  ", fg_color="#EFF6FF", text_color="#2563EB",
                             font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), corner_radius=6)
        badge.pack(side="left", padx=12)

        nav_bar = ctk.CTkFrame(self, fg_color="#F8FAFC", height=50, corner_radius=0)
        nav_bar.pack(fill="x", side="top", padx=15, pady=(8, 0))

        self.tab_buttons = {}
        tabs = [
            ("students", "👨‍🎓 Студенты"),
            ("groups", "👥 Учебные группы"),
            ("specialties", "📚 Специальности"),
            ("docs", "📁 Документы студентов"),
            ("templates", "📄 Шаблоны"),
            ("archive", "🗄️ Архив")
        ]

        for tab_id, tab_label in tabs:
            btn = ctk.CTkButton(
                nav_bar, text=tab_label, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                height=38, corner_radius=8, fg_color="transparent", text_color="#475569",
                hover_color="#E2E8F0", command=lambda tid=tab_id: self._switch_tab(tid)
            )
            btn.pack(side="left", padx=4, pady=6)
            self.tab_buttons[tab_id] = btn

        self.status = tk.StringVar(value="Готово к работе")
        status_bar = ctk.CTkLabel(self, textvariable=self.status, anchor="w", fg_color="#FFFFFF",
                                  text_color="#64748B", height=28, padx=15, font=("Segoe UI", 11))
        status_bar.pack(side="bottom", fill="x")

        self.container = ctk.CTkFrame(self, fg_color="#F1F5F9", corner_radius=0)
        self.container.pack(fill="both", expand=True, padx=15, pady=10)

        self.pages = {}
        for tab_id, _ in tabs:
            p = ctk.CTkFrame(self.container, fg_color="transparent")
            self.pages[tab_id] = p

        self._build_students_page()
        self._build_groups_page()
        self._build_specialties_page()
        self._build_docs_page()
        self._build_templates_page()
        self._build_archive_page()

        self._switch_tab("students")

    def _switch_tab(self, tab_id):
        for tid, page in self.pages.items(): page.pack_forget()
        for tid, btn in self.tab_buttons.items():
            if tid == tab_id: btn.configure(fg_color="#2563EB", text_color="#FFFFFF", hover_color="#1D4ED8")
            else: btn.configure(fg_color="transparent", text_color="#475569", hover_color="#E2E8F0")
        self.pages[tab_id].pack(fill="both", expand=True)

    def _tree(self, parent, columns, headings, widths=None):
        frame = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=8)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
        tree["displaycolumns"] = [c for c in columns if c != "id"]

        for i, col in enumerate(columns):
            tree.heading(col, text=headings[i], command=lambda _c=col, _t=tree: self._sort_column(_t, _c))
            tree.column(col, width=(widths[i] if widths else 120), anchor="w")

        y = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        x = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=y.set, xscrollcommand=x.set)

        tree.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=1)
        y.grid(row=0, column=1, sticky="ns")
        x.grid(row=1, column=0, sticky="ew")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    def _sort_column(self, tree, col):
        items = [(tree.set(k, col), k) for k in tree.get_children("")]
        reverse = self._sort_reverse.get(col, False)
        def convert(val):
            try: return float(val)
            except ValueError:
                try: return datetime.strptime(val, "%d.%m.%Y")
                except ValueError: return val.lower()
        items.sort(key=lambda t: convert(t[0]), reverse=reverse)
        for index, (_, k) in enumerate(items):
            tree.move(k, "", index)
        self._sort_reverse[col] = not reverse

    # ==================== СТУДЕНТЫ ====================
    def _build_students_page(self):
        page = self.pages["students"]

        filter_card = ctk.CTkFrame(page, fg_color="#FFFFFF", corner_radius=8)
        filter_card.pack(fill="x", pady=(0, 10), padx=2, ipady=6)

        ctk.CTkLabel(filter_card, text="Поиск:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.search_var = tk.StringVar()
        s_entry = ctk.CTkEntry(filter_card, textvariable=self.search_var, placeholder_text="ФИО / Номер / СНИЛС...", width=240)
        s_entry.pack(side="left", padx=4)
        s_entry.bind("<Return>", lambda e: self.refresh_students())

        ctk.CTkLabel(filter_card, text="Группа:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.group_filter = ctk.CTkComboBox(filter_card, values=["Все"], width=130, command=lambda _: self.refresh_students())
        self.group_filter.pack(side="left", padx=4)

        ctk.CTkLabel(filter_card, text="Возраст:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.age_filter = ctk.CTkComboBox(filter_card, width=175, command=lambda _: self.refresh_students(),
                                          values=["Все", "Совершеннолетние (18+)", "Несовершеннолетние (<18)"])
        self.age_filter.set("Все")
        self.age_filter.pack(side="left", padx=4)

        self.aid_filter = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(filter_card, text="Мат. помощь", variable=self.aid_filter,
                        command=self.refresh_students).pack(side="left", padx=12)

        ctk.CTkButton(filter_card, text="Найти", fg_color=COLOR_NEUTRAL, hover_color=COLOR_NEUTRAL_HOVER,
                      width=90, command=self.refresh_students).pack(side="right", padx=(4, 12))

        self.students_tree = self._tree(page,
                                        ("id", "number", "fio", "group", "birth", "snils", "phone", "email", "age", "aid"),
                                        ("ID", "Номер", "ФИО Студента", "Группа", "Дата рожд.", "СНИЛС", "Телефон", "Email", "Возраст", "Мат. помощь"),
                                        (0, 80, 240, 110, 110, 140, 120, 190, 70, 100))
        self.students_tree.bind("<<TreeviewSelect>>", self._student_selected)
        self.students_tree.bind("<Double-1>", lambda e: self.student_profile())

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))

        buttons = [
            ("Добавить студента", self.add_student, COLOR_SUCCESS, COLOR_SUCCESS_HOVER),
            ("Импорт из Excel", self.import_students_excel, COLOR_SUCCESS, COLOR_SUCCESS_HOVER),
            ("Профиль студента", self.student_profile, COLOR_PRIMARY, COLOR_PRIMARY_HOVER),
            ("Редактировать", self.edit_student, COLOR_WARNING, COLOR_WARNING_HOVER),
            ("Печать всех документов", self.print_student_docs, COLOR_NEUTRAL, COLOR_NEUTRAL_HOVER),
            ("Сформировать для выбранных", self.generate_bulk_documents, COLOR_PRIMARY, COLOR_PRIMARY_HOVER),
            ("Удалить", self.delete_student, COLOR_DANGER, COLOR_DANGER_HOVER),
        ]
        for text, cmd, bg, hbg in buttons:
            ctk.CTkButton(actions, text=text, command=cmd, fg_color=bg, hover_color=hbg).pack(side="left", padx=(0, 6))

    # ==================== УЧЕБНЫЕ ГРУППЫ ====================
    def _build_groups_page(self):
        page = self.pages["groups"]

        filter_card = ctk.CTkFrame(page, fg_color="#FFFFFF", corner_radius=8)
        filter_card.pack(fill="x", pady=(0, 10), padx=2, ipady=6)

        ctk.CTkLabel(filter_card, text="Поиск группы:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.group_search_var = tk.StringVar()
        g_entry = ctk.CTkEntry(filter_card, textvariable=self.group_search_var, width=200, placeholder_text="Название...")
        g_entry.pack(side="left", padx=4)
        g_entry.bind("<Return>", lambda e: self.refresh_groups())

        ctk.CTkLabel(filter_card, text="Курс:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.group_course_filter = ctk.CTkComboBox(filter_card, values=["Все", "1", "2", "3", "4", "5", "6"], width=100,
                                                   command=lambda _: self.refresh_groups())
        self.group_course_filter.set("Все")
        self.group_course_filter.pack(side="left", padx=4)

        ctk.CTkButton(filter_card, text="Фильтровать", fg_color=COLOR_NEUTRAL, hover_color=COLOR_NEUTRAL_HOVER,
                      width=110, command=self.refresh_groups).pack(side="right", padx=(4, 12))

        self.groups_tree = self._tree(page, ("id", "name", "course", "specialty", "count"),
                                      ("ID", "Название группы", "Курс", "Специальность", "Количество студентов"), (0, 240, 90, 400, 150))

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(actions, text="Добавить группу", command=self.add_group, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Редактировать", command=self.edit_group, fg_color=COLOR_WARNING, hover_color=COLOR_WARNING_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Показать студентов", command=self.show_group_students, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Удалить группу", command=self.delete_group, fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER).pack(side="left", padx=(0, 6))

    # ==================== СПЕЦИАЛЬНОСТИ ====================
    def _build_specialties_page(self):
        page = self.pages["specialties"]

        filter_card = ctk.CTkFrame(page, fg_color="#FFFFFF", corner_radius=8)
        filter_card.pack(fill="x", pady=(0, 10), padx=2, ipady=6)

        ctk.CTkLabel(filter_card, text="Поиск специальности:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.spec_search_var = tk.StringVar()
        sp_entry = ctk.CTkEntry(filter_card, textvariable=self.spec_search_var, width=280, placeholder_text="Название или код специальности...")
        sp_entry.pack(side="left", padx=4)
        sp_entry.bind("<Return>", lambda e: self.refresh_specialties())

        ctk.CTkButton(filter_card, text="Найти", fg_color=COLOR_NEUTRAL, hover_color=COLOR_NEUTRAL_HOVER,
                      width=90, command=self.refresh_specialties).pack(side="right", padx=(4, 12))

        self.specialties_tree = self._tree(page, ("id", "name", "code"),
                                           ("ID", "Название специальности", "Код специальности"), (0, 550, 200))

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(actions, text="Добавить специальность", command=self.add_specialty, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Редактировать", command=self.edit_specialty, fg_color=COLOR_WARNING, hover_color=COLOR_WARNING_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Удалить", command=self.delete_specialty, fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER).pack(side="left", padx=(0, 6))

    # ==================== ДОКУМЕНТЫ СТУДЕНТОВ ====================
    def _build_docs_page(self):
        page = self.pages["docs"]

        filter_card = ctk.CTkFrame(page, fg_color="#FFFFFF", corner_radius=8)
        filter_card.pack(fill="x", pady=(0, 10), padx=2, ipady=6)

        ctk.CTkLabel(filter_card, text="Поиск документа:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.doc_search_var = tk.StringVar()
        d_entry = ctk.CTkEntry(filter_card, textvariable=self.doc_search_var, width=240, placeholder_text="ФИО студента или название документа...")
        d_entry.pack(side="left", padx=4)
        d_entry.bind("<Return>", lambda e: self.refresh_docs())

        ctk.CTkLabel(filter_card, text="Категория:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.doc_aid_filter = ctk.CTkComboBox(filter_card, values=["Все", "Только мат. помощь", "Без мат. помощи"], width=170,
                                              command=lambda _: self.refresh_docs())
        self.doc_aid_filter.set("Все")
        self.doc_aid_filter.pack(side="left", padx=4)

        ctk.CTkButton(filter_card, text="Фильтровать", fg_color=COLOR_NEUTRAL, hover_color=COLOR_NEUTRAL_HOVER,
                      width=110, command=self.refresh_docs).pack(side="right", padx=(4, 12))

        self.docs_tree = self._tree(page, ("id", "student", "title", "file", "aid", "date"),
                                    ("ID", "Студент", "Название документа", "Файл", "Мат. помощь", "Дата загрузки"), (0, 240, 240, 240, 110, 150))

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(actions, text="Загрузить документ студенту", command=self.upload_student_doc, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Открыть", command=self.open_selected_doc, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Скачать копию", command=self.download_selected_doc, fg_color=COLOR_NEUTRAL, hover_color=COLOR_NEUTRAL_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Печать", command=self.print_selected_doc, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Удалить", command=self.delete_selected_doc, fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER).pack(side="left", padx=(0, 6))

    # ==================== ШАБЛОНЫ (ЦЕНТР УПРАВЛЕНИЯ) ====================
    def _build_templates_page(self):
        page = self.pages["templates"]

        filter_card = ctk.CTkFrame(page, fg_color="#FFFFFF", corner_radius=8)
        filter_card.pack(fill="x", pady=(0, 10), padx=2, ipady=6)

        ctk.CTkLabel(filter_card, text="Поиск шаблона:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.template_search_var = tk.StringVar()
        t_entry = ctk.CTkEntry(filter_card, textvariable=self.template_search_var, width=240, placeholder_text="Название / описание...")
        t_entry.pack(side="left", padx=4)
        t_entry.bind("<Return>", lambda e: self.refresh_templates())

        ctk.CTkLabel(filter_card, text="Формат:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.template_format_filter = ctk.CTkComboBox(filter_card, values=["Все", "DOCX", "XLSX"], width=100,
                                                      command=lambda _: self.refresh_templates())
        self.template_format_filter.set("Все")
        self.template_format_filter.pack(side="left", padx=4)

        ctk.CTkButton(filter_card, text="Найти", fg_color=COLOR_NEUTRAL, hover_color=COLOR_NEUTRAL_HOVER,
                      width=90, command=self.refresh_templates).pack(side="right", padx=(4, 12))

        self.templates_tree = self._tree(page, ("id", "name", "type", "file", "description"),
                                         ("ID", "Название шаблона", "Формат", "Имя файла", "Описание"), (0, 260, 80, 240, 360))
        self.templates_tree.bind("<Double-1>", lambda e: self.fill_selected_template())

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))

        # Основные кнопки управления шаблонами
        ctk.CTkButton(actions, text="✨ Заполнить для студента / группы", command=self.fill_selected_template,
                      fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="📥 Скачать пустой шаблон", command=self.download_template,
                      fg_color=COLOR_NEUTRAL, hover_color=COLOR_NEUTRAL_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="👁️ Открыть шаблон", command=self.open_template,
                      fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="➕ Загрузить новый", command=self.upload_template,
                      fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Удалить шаблон", command=self.delete_template,
                      fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER).pack(side="left", padx=(0, 6))

    # ==================== АРХИВ ====================
    def _build_archive_page(self):
        page = self.pages["archive"]

        filter_card = ctk.CTkFrame(page, fg_color="#FFFFFF", corner_radius=8)
        filter_card.pack(fill="x", pady=(0, 10), padx=2, ipady=6)

        ctk.CTkLabel(filter_card, text="Поиск в архиве:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.archive_search = tk.StringVar()
        a_entry = ctk.CTkEntry(filter_card, textvariable=self.archive_search, width=240, placeholder_text="Название, группа, ФИО...")
        a_entry.pack(side="left", padx=4)
        a_entry.bind("<Return>", lambda e: self.refresh_archive())

        ctk.CTkLabel(filter_card, text="Категория:", font=("Segoe UI", 12, "bold")).pack(side="left", padx=(12, 4))
        self.archive_cat_filter = ctk.CTkComboBox(filter_card, values=["Все"], width=170, command=lambda _: self.refresh_archive())
        self.archive_cat_filter.pack(side="left", padx=4)

        ctk.CTkButton(filter_card, text="Найти", fg_color=COLOR_NEUTRAL, hover_color=COLOR_NEUTRAL_HOVER,
                      width=90, command=self.refresh_archive).pack(side="right", padx=(4, 12))

        self.archive_tree = self._tree(page, ("id", "title", "category", "file", "group", "student", "date"),
                                       ("ID", "Название", "Категория", "Файл документа", "Группа", "Студент", "Дата архивации"), (0, 240, 150, 220, 100, 200, 150))

        actions = ctk.CTkFrame(page, fg_color="transparent")
        actions.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(actions, text="Загрузить готовый документ", command=self.upload_archive, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Открыть", command=self.open_archive, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Скачать копию", command=self.download_archive, fg_color=COLOR_NEUTRAL, hover_color=COLOR_NEUTRAL_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Печать", command=self.print_archive, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER).pack(side="left", padx=(0, 6))
        ctk.CTkButton(actions, text="Удалить из архива", command=self.delete_archive, fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER).pack(side="left", padx=(0, 6))

    # ==================== УМНОЕ ЗАПОЛНЕНИЕ ШАБЛОНА ====================
    def fill_selected_template(self):
        tid = self._selected_id(self.templates_tree, "шаблон")
        if tid is None: return

        template = db.one("SELECT * FROM document_templates WHERE id=%s", (tid,))
        if not template: return

        # 1. Если это Социальный паспорт
        if "социальный паспорт" in template["name"].lower():
            self._fill_social_passport_dialog()
            return

        # 2. Если это Заявление на матпомощь
        if "материальн" in template["name"].lower():
            self._fill_material_aid_dialog(template)
            return

        # 3. Для любых других шаблонов — запрос студента
        self._fill_generic_template_dialog(template)

    def _fill_social_passport_dialog(self):
        groups = self.run_db(self.get_groups)
        if not groups:
            messagebox.showinfo("Нет групп", "Сначала создайте учебную группу."); return

        win = ctk.CTkToplevel(self)
        win.title("Формирование социального паспорта")
        win.geometry("450x200")
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="Выберите группу:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 4))
        names = [g["name"] for g in groups]
        combo = ctk.CTkComboBox(win, values=names, width=410)
        combo.pack(padx=20, pady=4)

        def make():
            grp = next((g for g in groups if g["name"] == combo.get()), None)
            win.destroy()
            students = db.query("SELECT * FROM students WHERE group_id=%s ORDER BY last_name,first_name,middle_name", (grp["id"],), fetch=True)
            if not students:
                messagebox.showinfo("Нет студентов", "В выбранной группе пока нет студентов."); return

            out = filedialog.asksaveasfilename(
                title="Сохранить социальный паспорт",
                initialfile=f'Социальный_паспорт_{documents.safe_name(grp["name"])}.xlsx',
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")]
            )
            if not out: return
            try:
                documents.generate_social_passport_xlsx(grp["name"], students, out)
                stored = documents.copy_into(out, documents.ARCHIVE)
                db.query("""INSERT INTO archive_documents(group_id,title,file_name,file_path,category)
                    VALUES(%s,%s,%s,%s,%s)""", (grp["id"], f"Соц. паспорт {grp['name']}", Path(stored).name, stored, "Социальные паспорта"))
                self.refresh_archive()
                if messagebox.askyesno("Готово", "Социальный паспорт сформирован и добавлен в архив!\nОткрыть готовый Excel?"):
                    documents.open_file(out)
            except Exception as e: messagebox.showerror("Ошибка", str(e))

        ctk.CTkButton(win, text="Сформировать для группы", command=make, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, width=200).pack(pady=20)

    def _fill_material_aid_dialog(self, template):
        students = db.query("""SELECT s.*, g.name AS group_name, g.course, sp.name AS specialty_name
            FROM students s JOIN study_groups g ON g.id=s.group_id
            LEFT JOIN specialties sp ON sp.id=g.specialty_id ORDER BY s.last_name, s.first_name""", fetch=True)
        if not students:
            messagebox.showinfo("Нет студентов", "В базе нет зарегистрированных студентов."); return

        win = ctk.CTkToplevel(self)
        win.title("Формирование заявления на материальную помощь")
        win.geometry("540x510")
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="Выберите студента:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 2))
        st_map = {f'{s["last_name"]} {s["first_name"]} {s.get("middle_name","")} ({s["group_name"]})': s for s in students}
        st_combo = ctk.CTkComboBox(win, values=list(st_map.keys()), width=490)
        st_combo.pack(padx=20, pady=2)

        ctk.CTkLabel(win, text="ФИО в родительном падеже (Кого?):", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(8, 2))
        fio_entry = ctk.CTkEntry(win, width=490)
        fio_entry.pack(padx=20, pady=2)

        ctk.CTkLabel(win, text="Студента или студентки:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(8, 2))
        word_combo = ctk.CTkComboBox(win, values=["студента", "студентки"], width=490)
        word_combo.pack(padx=20, pady=2)

        def update_st_fields(*args):
            s = st_map.get(st_combo.get())
            if s:
                f_gen, word = documents.inflect_fio_genitive(s["last_name"], s["first_name"], s.get("middle_name", ""))
                fio_entry.delete(0, "end"); fio_entry.insert(0, f_gen)
                word_combo.set(word)

        st_combo.configure(command=lambda _: update_st_fields())
        update_st_fields()

        ctk.CTkLabel(win, text="Причина материальной помощи:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(8, 2))
        reason_combo = ctk.CTkComboBox(win, values=documents.AID_REASONS, width=490)
        reason_combo.pack(padx=20, pady=2)
        reason_combo.set("проживаю в неполной семье")

        custom_reason = ctk.CTkEntry(win, width=490, placeholder_text="Или введите свою причину вручную...")
        custom_reason.pack(padx=20, pady=4)

        def proceed():
            s = st_map[st_combo.get()]
            g = {"id": s["group_id"], "name": s["group_name"], "course": s["course"], "specialty_name": s["specialty_name"]}
            chosen_reason = custom_reason.get().strip() or reason_combo.get()
            final_fio_gen = fio_entry.get().strip()
            final_word = word_combo.get()
            win.destroy()

            out = filedialog.asksaveasfilename(
                title="Сохранить заявление",
                initialfile=f'Заявление_{documents.safe_name(s["last_name"])}_матпомощь.docx',
                defaultextension=".docx",
                filetypes=[("Word", "*.docx")]
            )
            if not out: return
            try:
                vals = documents.student_values(s, g, reason=chosen_reason, aid_fio_gen=final_fio_gen, student_word=final_word)
                documents.fill_docx(template["file_path"], out, vals)
                stored = documents.copy_into(out, documents.ARCHIVE)
                title = f"Заявление на мат. помощь ({s['last_name']})"
                db.query("""INSERT INTO archive_documents(group_id,student_id,title,file_name,file_path,category)
                    VALUES(%s,%s,%s,%s,%s,%s)""", (g["id"], s["id"], title, Path(stored).name, stored, "Заявления на матпомощь"))
                db.query("""INSERT INTO student_documents(student_id,title,file_name,file_path,file_type,is_material_aid)
                    VALUES(%s,%s,%s,%s,%s,TRUE)""",
                    (s["id"], title, Path(stored).name, stored, Path(stored).suffix.lower().lstrip(".")))
                self.refresh_all()
                if messagebox.askyesno("Готово", "Заявление сформировано и сохранено в архив!\nОткрыть готовый Word?"):
                    documents.open_file(out)
            except Exception as e: messagebox.showerror("Ошибка", str(e))

        ctk.CTkButton(win, text="Сформировать заявление", command=proceed, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, width=220).pack(pady=20)

    def _fill_generic_template_dialog(self, template):
        students = db.query("""SELECT s.*, g.name AS group_name, g.course, sp.name AS specialty_name
            FROM students s JOIN study_groups g ON g.id=s.group_id
            LEFT JOIN specialties sp ON sp.id=g.specialty_id ORDER BY s.last_name, s.first_name""", fetch=True)
        if not students:
            messagebox.showinfo("Нет студентов", "В базе нет зарегистрированных студентов."); return

        win = ctk.CTkToplevel(self)
        win.title("Заполнение шаблона")
        win.geometry("460x200")
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="Выберите студента:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 4))
        st_map = {f'{s["last_name"]} {s["first_name"]} {s.get("middle_name","")} ({s["group_name"]})': s for s in students}
        st_combo = ctk.CTkComboBox(win, values=list(st_map.keys()), width=420)
        st_combo.pack(padx=20, pady=4)

        def proceed():
            s = st_map[st_combo.get()]
            g = {"id": s["group_id"], "name": s["group_name"], "course": s["course"], "specialty_name": s["specialty_name"]}
            win.destroy()
            out = filedialog.asksaveasfilename(
                title="Сохранить документ",
                initialfile=f'{documents.safe_name(s["last_name"])}_{documents.safe_name(template["name"])}.{template["file_type"]}',
                defaultextension="." + template["file_type"],
                filetypes=[(template["file_type"].upper(), "*." + template["file_type"])]
            )
            if not out: return
            try:
                vals = documents.student_values(s, g)
                if template["file_type"] == "docx": documents.fill_docx(template["file_path"], out, vals)
                else: documents.fill_xlsx(template["file_path"], out, vals)
                stored = documents.copy_into(out, documents.ARCHIVE)
                db.query("""INSERT INTO archive_documents(group_id,student_id,title,file_name,file_path,category)
                    VALUES(%s,%s,%s,%s,%s,%s)""", (g["id"], s["id"], template["name"], Path(stored).name, stored, "Сформированные документы"))
                self.refresh_archive()
                if messagebox.askyesno("Готово", "Документ сформирован и сохранен в архив!\nОткрыть файл?"):
                    documents.open_file(out)
            except Exception as e: messagebox.showerror("Ошибка", str(e))

        ctk.CTkButton(win, text="Сформировать файл", command=proceed, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, width=180).pack(pady=20)

    # ==================== ОПЕРАЦИИ БАЗЫ ДАННЫХ ====================
    def run_db(self, fn, success="Готово"):
        try:
            result = fn()
            self.status.set(success)
            return result
        except Exception as exc:
            messagebox.showerror("Ошибка", f"{exc}\n\nПроверьте базу данных.")
            self.status.set("Ошибка базы данных")
            return None

    def refresh_all(self):
        self.refresh_specialties()
        self.refresh_groups()
        self.refresh_students()
        self.refresh_docs()
        self.refresh_templates()
        self.refresh_archive()

    def get_groups(self):
        return db.query("""SELECT g.*,sp.name AS specialty_name FROM study_groups g
            LEFT JOIN specialties sp ON sp.id=g.specialty_id ORDER BY g.name""", fetch=True)

    def _selected_id(self, tree, label):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Выбор не сделан", f"Пожалуйста, выберите {label} в таблице.")
            return None
        return int(tree.item(sel[0], "values")[0])

    def refresh_specialties(self):
        term = self.spec_search_var.get().strip() if hasattr(self, "spec_search_var") else ""
        sql = "SELECT id,name,code FROM specialties WHERE 1=1"
        params = []
        if term:
            sql += " AND (name ILIKE %s OR code ILIKE %s)"
            params.extend([f"%{term}%", f"%{term}%"])
        sql += " ORDER BY name"
        rows = self.run_db(lambda: db.query(sql, params, fetch=True))
        if rows is None: return
        self.specialties_tree.delete(*self.specialties_tree.get_children())
        for r in rows:
            self.specialties_tree.insert("", "end", values=(r["id"], r["name"], r["code"] or ""))

    def _specialty_dialog(self, title, row=None):
        win = ctk.CTkToplevel(self); win.title(title); win.geometry("450x240"); win.transient(self); win.grab_set()
        ctk.CTkLabel(win, text="Название специальности:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(15, 2))
        name = ctk.CTkEntry(win, width=410); name.pack(padx=20, pady=4)
        ctk.CTkLabel(win, text="Код специальности (необязательно):", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(10, 2))
        code = ctk.CTkEntry(win, width=410); code.pack(padx=20, pady=4)
        if row: name.insert(0, row.get("name", "")); code.insert(0, row.get("code", "") or "")
        def save():
            val = name.get().strip()
            if not val: messagebox.showerror("Ошибка", "Введите название специальности.", parent=win); return
            try:
                if row: db.query("UPDATE specialties SET name=%s,code=%s WHERE id=%s", (val, code.get().strip(), row["id"]))
                else: db.query("INSERT INTO specialties(name,code) VALUES(%s,%s)", (val, code.get().strip()))
                win.destroy(); self.refresh_all()
            except Exception as e: messagebox.showerror("Ошибка", str(e), parent=win)
        ctk.CTkButton(win, text="Сохранить", command=save, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, width=140).pack(pady=15)

    def add_specialty(self): self._specialty_dialog("Добавление специальности")
    def edit_specialty(self):
        sid = self._selected_id(self.specialties_tree, "специальность")
        if sid is None: return
        r = db.one("SELECT * FROM specialties WHERE id=%s", (sid,))
        if r: self._specialty_dialog("Редактирование специальности", r)
    def delete_specialty(self):
        sid = self._selected_id(self.specialties_tree, "специальность")
        if sid is None: return
        if not messagebox.askyesno("Подтверждение", "Удалить специальность? Сначала отвяжите от неё группы."): return
        self.run_db(lambda: db.query("DELETE FROM specialties WHERE id=%s", (sid,)), "Специальность удалена")
        self.refresh_all()

    def refresh_groups(self):
        term = self.group_search_var.get().strip() if hasattr(self, "group_search_var") else ""
        course = self.group_course_filter.get() if hasattr(self, "group_course_filter") else "Все"
        sql = """SELECT g.id,g.name,g.course,COALESCE(sp.name,'') AS specialty,COUNT(s.id) AS count
            FROM study_groups g LEFT JOIN specialties sp ON sp.id=g.specialty_id LEFT JOIN students s ON s.group_id=g.id WHERE 1=1"""
        params = []
        if term: sql += " AND g.name ILIKE %s"; params.append(f"%{term}%")
        if course != "Все": sql += " AND g.course = %s"; params.append(int(course))
        sql += " GROUP BY g.id,sp.name ORDER BY g.name"
        rows = self.run_db(lambda: db.query(sql, params, fetch=True))
        if rows is None: return
        self.groups_tree.delete(*self.groups_tree.get_children())
        for r in rows:
            self.groups_tree.insert("", "end", values=(r["id"], r["name"], r["course"], r["specialty"], r["count"]))
        all_groups = self.run_db(self.get_groups) or []
        opts = ["Все"] + [g["name"] for g in all_groups]
        curr = self.group_filter.get()
        self.group_filter.configure(values=opts)
        self.group_filter.set(curr if curr in opts else "Все")

    def _group_dialog(self, title, row=None):
        specialties = db.query("SELECT id,name FROM specialties ORDER BY name", fetch=True)
        if not specialties: messagebox.showwarning("Нет специальностей", "Сначала создайте специальность во вкладке «Специальности»."); return
        win = ctk.CTkToplevel(self); win.title(title); win.geometry("450x300"); win.transient(self); win.grab_set()
        ctk.CTkLabel(win, text="Название группы:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(15, 2))
        name = ctk.CTkEntry(win, width=410); name.pack(padx=20, pady=2)
        if row: name.insert(0, row.get("name", ""))
        ctk.CTkLabel(win, text="Курс (1-6):", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(8, 2))
        course = ctk.CTkEntry(win, width=410); course.pack(padx=20, pady=2)
        course.insert(0, str(row.get("course", 1) if row else 1))
        ctk.CTkLabel(win, text="Специальность:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(8, 2))
        sp_names = [sp["name"] for sp in specialties]
        combo = ctk.CTkComboBox(win, values=sp_names, width=410); combo.pack(padx=20, pady=2)
        by_name = {sp["name"]: sp["id"] for sp in specialties}
        current = row.get("specialty_name") if row else None
        combo.set(current if current in by_name else specialties[0]["name"])
        def save():
            g_name = name.get().strip()
            try: c_num = int(course.get())
            except ValueError: messagebox.showerror("Ошибка", "Курс должен быть числом.", parent=win); return
            if not g_name or not 1 <= c_num <= 6: messagebox.showerror("Ошибка", "Укажите название и курс 1-6.", parent=win); return
            try:
                sp_id = by_name[combo.get()]
                if row: db.query("UPDATE study_groups SET name=%s,course=%s,specialty_id=%s WHERE id=%s", (g_name, c_num, sp_id, row["id"]))
                else: db.query("INSERT INTO study_groups(name,course,specialty_id) VALUES(%s,%s,%s)", (g_name, c_num, sp_id))
                win.destroy(); self.refresh_all()
            except Exception as e: messagebox.showerror("Ошибка", str(e), parent=win)
        ctk.CTkButton(win, text="Сохранить", command=save, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, width=140).pack(pady=15)

    def add_group(self): self._group_dialog("Добавление группы")
    def edit_group(self):
        gid = self._selected_id(self.groups_tree, "группу")
        if gid is None: return
        r = db.one("SELECT g.*,sp.name AS specialty_name FROM study_groups g LEFT JOIN specialties sp ON sp.id=g.specialty_id WHERE g.id=%s", (gid,))
        if r: self._group_dialog("Редактирование группы", r)
    def delete_group(self):
        gid = self._selected_id(self.groups_tree, "группу")
        if gid is None: return
        if not messagebox.askyesno("Подтверждение", "Удалить группу? Нельзя удалить группу со студентами."): return
        self.run_db(lambda: db.query("DELETE FROM study_groups WHERE id=%s", (gid,)), "Группа удалена")
        self.refresh_all()
    def show_group_students(self):
        gid = self._selected_id(self.groups_tree, "группу")
        if gid is None: return
        r = db.one("SELECT name FROM study_groups WHERE id=%s", (gid,))
        if r:
            self.group_filter.set(r["name"])
            self._switch_tab("students")
            self.refresh_students()

    def refresh_students(self):
        def load():
            sql = """SELECT s.*,g.name AS group_name,g.course,sp.name AS specialty_name,
                CASE WHEN s.birth_date IS NULL THEN NULL ELSE EXTRACT(YEAR FROM age(current_date,s.birth_date))::int END AS age,
                (EXISTS(SELECT 1 FROM student_documents d WHERE d.student_id=s.id AND d.is_material_aid)
                 OR EXISTS(SELECT 1 FROM archive_documents a WHERE a.student_id=s.id
                    AND (a.category ILIKE '%матпомощ%' OR a.category ILIKE '%мат. помощь%'
                         OR a.title ILIKE '%материальн%помощ%'))) AS has_aid
                FROM students s JOIN study_groups g ON g.id=s.group_id
                LEFT JOIN specialties sp ON sp.id=g.specialty_id WHERE 1=1"""
            params = []
            term = self.search_var.get().strip() if hasattr(self, "search_var") else ""
            if term:
                sql += " AND (concat_ws(' ',s.last_name,s.first_name,s.middle_name) ILIKE %s OR s.student_number ILIKE %s OR s.snils ILIKE %s OR s.email ILIKE %s)"
                params.extend([f"%{term}%"] * 4)
            gf = self.group_filter.get() if hasattr(self, "group_filter") else "Все"
            if gf and gf != "Все": sql += " AND g.name=%s"; params.append(gf)
            af = self.age_filter.get() if hasattr(self, "age_filter") else "Все"
            if af.startswith("Совершеннолетние"): sql += " AND s.birth_date IS NOT NULL AND age(current_date,s.birth_date) >= interval '18 years'"
            elif af.startswith("Несовершеннолетние"): sql += " AND s.birth_date IS NOT NULL AND age(current_date,s.birth_date) < interval '18 years'"
            if hasattr(self, "aid_filter") and self.aid_filter.get():
                sql += """ AND (
                    EXISTS(SELECT 1 FROM student_documents d WHERE d.student_id=s.id AND d.is_material_aid)
                    OR EXISTS(SELECT 1 FROM archive_documents a WHERE a.student_id=s.id
                        AND (a.category ILIKE '%матпомощ%' OR a.category ILIKE '%мат. помощь%'
                             OR a.title ILIKE '%материальн%помощ%'))
                )"""
            sql += " ORDER BY s.last_name,s.first_name,s.middle_name"
            return db.query(sql, params, fetch=True)

        rows = self.run_db(load)
        if rows is None: return
        self.students_tree.delete(*self.students_tree.get_children())
        for idx, s in enumerate(rows, start=1):
            fio = " ".join(filter(None, [s["last_name"], s["first_name"], s["middle_name"]]))
            birth = s["birth_date"].strftime("%d.%m.%Y") if s["birth_date"] else ""
            num_display = s.get("student_number") or str(idx)
            self.students_tree.insert("", "end", values=(s["id"], num_display, fio, s["group_name"], birth,
                                                         s.get("snils", ""), s.get("phone", ""), s.get("email", ""),
                                                         s["age"] if s["age"] is not None else "", "Да" if s["has_aid"] else "Нет"))

    def _student_selected(self, event=None):
        sel = self.students_tree.selection()
        self.selected_student_id = int(self.students_tree.item(sel[0], "values")[0]) if sel else None

    def _student_dialog(self, title, row=None):
        groups = self.run_db(self.get_groups)
        if not groups: messagebox.showwarning("Нет групп", "Сначала создайте учебную группу."); return
        win = ctk.CTkToplevel(self); win.title(title); win.geometry("500x580"); win.transient(self); win.grab_set()
        labels = [("Номер студента:", "student_number"), ("Фамилия:", "last_name"), ("Имя:", "first_name"),
                  ("Отчество:", "middle_name"), ("Дата рождения (ГГГГ-ММ-ДД):", "birth_date"),
                  ("СНИЛС:", "snils"), ("Телефон:", "phone"), ("Email:", "email")]
        fields = {}
        for i, (label, key) in enumerate(labels):
            ctk.CTkLabel(win, text=label, font=("Segoe UI", 11, "bold")).grid(row=i, column=0, sticky="w", padx=20, pady=3)
            ent = ctk.CTkEntry(win, width=250); ent.grid(row=i, column=1, padx=20, pady=3)
            val = row.get(key, "") if row else ""
            if key == "birth_date" and val: val = val.isoformat()
            ent.insert(0, str(val or "")); fields[key] = ent
        idx = len(labels)
        ctk.CTkLabel(win, text="Учебная группа:", font=("Segoe UI", 11, "bold")).grid(row=idx, column=0, sticky="w", padx=20, pady=3)
        group_combo = ctk.CTkComboBox(win, values=[g["name"] for g in groups], width=250); group_combo.grid(row=idx, column=1, padx=20, pady=3)
        group_by_name = {g["name"]: g for g in groups}
        selected_name = next((g["name"] for g in groups if row and g["id"] == row.get("group_id")), groups[0]["name"])
        group_combo.set(selected_name)
        def save():
            last = fields["last_name"].get().strip(); first = fields["first_name"].get().strip()
            if not last or not first: messagebox.showerror("Ошибка", "Фамилия и имя обязательны.", parent=win); return
            birth_text = fields["birth_date"].get().strip()
            try:
                birth = date.fromisoformat(birth_text) if birth_text else None
                if birth and birth > date.today(): raise ValueError()
            except ValueError: messagebox.showerror("Ошибка", "Дата рождения в формате ГГГГ-ММ-ДД.", parent=win); return
            vals = (fields["student_number"].get().strip(), group_by_name[group_combo.get()]["id"], last, first,
                    fields["middle_name"].get().strip(), birth, fields["snils"].get().strip(),
                    fields["phone"].get().strip(), fields["email"].get().strip())
            try:
                if row: db.query("""UPDATE students SET student_number=%s,group_id=%s,last_name=%s,first_name=%s,middle_name=%s,
                        birth_date=%s,snils=%s,phone=%s,email=%s WHERE id=%s""", vals + (row["id"],))
                else: db.query("""INSERT INTO students(student_number,group_id,last_name,first_name,middle_name,birth_date,snils,phone,email)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""", vals)
                win.destroy(); self.refresh_all()
            except Exception as e: messagebox.showerror("Ошибка", str(e), parent=win)
        ctk.CTkButton(win, text="Сохранить", command=save, fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, width=140).grid(row=idx+1, column=0, columnspan=2, pady=18)

    def add_student(self): self._student_dialog("Добавление студента")
    def edit_student(self):
        sid = self._selected_id(self.students_tree, "студента")
        if sid is None: return
        r = db.one("SELECT * FROM students WHERE id=%s", (sid,))
        if r: self._student_dialog("Редактирование студента", r)
    def delete_student(self):
        sid = self._selected_id(self.students_tree, "студента")
        if sid is None: return
        if not messagebox.askyesno("Подтверждение", "Удалить студента и связанные документы?"): return
        self.run_db(lambda: db.query("DELETE FROM students WHERE id=%s", (sid,)), "Студент удален")
        self.refresh_all()

    def student_profile(self):
        sid = self._selected_id(self.students_tree, "студента")
        if sid is None: return
        s = db.one("""SELECT s.*, g.name AS group_name, g.course, sp.name AS specialty_name FROM students s
            JOIN study_groups g ON g.id=s.group_id LEFT JOIN specialties sp ON sp.id=g.specialty_id WHERE s.id=%s""", (sid,))
        if not s: return
        win = ctk.CTkToplevel(self); win.title("Карточка студента"); win.geometry("780x640"); win.transient(self); win.grab_set()
        fio = " ".join(filter(None, [s["last_name"], s["first_name"], s["middle_name"]]))
        top_card = ctk.CTkFrame(win, fg_color="#FFFFFF", corner_radius=10); top_card.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(top_card, text="👨‍🎓", font=("Segoe UI", 42)).pack(side="left", padx=16, pady=12)
        info_block = ctk.CTkFrame(top_card, fg_color="transparent"); info_block.pack(side="left", fill="both", expand=True, pady=10)
        ctk.CTkLabel(info_block, text=fio, font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#1E293B", anchor="w").pack(fill="x")
        ctk.CTkLabel(info_block, text=f"Группа: {s['group_name']}  |  Курс: {s['course']}  |  Специальность: {s.get('specialty_name') or 'Не указана'}",
                     font=("Segoe UI", 12), text_color="#64748B", anchor="w").pack(fill="x", pady=(2, 0))

        grid_card = ctk.CTkFrame(win, fg_color="#FFFFFF", corner_radius=10); grid_card.pack(fill="x", padx=16, pady=(0, 12))
        details = [
            ("Номер студента:", s.get("student_number", "-")),
            ("Дата рождения:", s["birth_date"].strftime("%d.%m.%Y") if s["birth_date"] else "-"),
            ("СНИЛС:", s.get("snils", "-")),
            ("Телефон:", s.get("phone", "-")),
            ("Email:", s.get("email", "-")),
            ("Адрес:", s.get("address", "-"))
        ]
        for idx, (label, val) in enumerate(details):
            r, c = divmod(idx, 2)
            cell = ctk.CTkFrame(grid_card, fg_color="transparent")
            cell.grid(row=r, column=c, sticky="w", padx=20, pady=8)
            ctk.CTkLabel(cell, text=label, font=("Segoe UI", 11, "bold"), text_color="#64748B").pack(anchor="w")
            ctk.CTkLabel(cell, text=str(val or "-"), font=("Segoe UI", 12), text_color="#0F172A").pack(anchor="w")
        grid_card.columnconfigure(0, weight=1); grid_card.columnconfigure(1, weight=1)

        doc_header = ctk.CTkFrame(win, fg_color="transparent"); doc_header.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(doc_header, text="Прикреплённые документы", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(side="left")
        doc_frame = ctk.CTkFrame(win, fg_color="#FFFFFF", corner_radius=10); doc_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        doc_tree = ttk.Treeview(doc_frame, columns=("id", "title", "file", "date", "aid"), show="headings", height=6)
        doc_tree["displaycolumns"] = ("title", "file", "date", "aid")
        doc_tree.heading("title", text="Название"); doc_tree.heading("file", text="Имя файла")
        doc_tree.heading("date", text="Дата"); doc_tree.heading("aid", text="Мат. помощь")
        doc_tree.pack(fill="both", expand=True, padx=8, pady=8)

        docs = db.query("SELECT * FROM student_documents WHERE student_id=%s ORDER BY uploaded_at DESC", (sid,), fetch=True)
        for d in docs:
            doc_tree.insert("", "end", values=(d["id"], d["title"], d["file_name"], d["uploaded_at"].strftime("%d.%m.%Y"), "Да" if d["is_material_aid"] else "Нет"))

        btn_bar = ctk.CTkFrame(win, fg_color="transparent"); btn_bar.pack(fill="x", padx=16, pady=(0, 16))
        def open_p_doc():
            sel = doc_tree.selection()
            if not sel: return
            did = doc_tree.item(sel[0], "values")[0]
            doc = db.one("SELECT * FROM student_documents WHERE id=%s", (did,))
            if doc: documents.open_file(doc["file_path"])

        ctk.CTkButton(btn_bar, text="Открыть документ", command=open_p_doc, fg_color=COLOR_PRIMARY, width=140).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_bar, text="Закрыть", command=win.destroy, fg_color="#E2E8F0", text_color="#1E293B", hover_color="#CBD5E1", width=100).pack(side="right")

    def import_students_excel(self):
        from openpyxl import load_workbook
        path = filedialog.askopenfilename(title="Выберите Excel-файл со списком студентов", filetypes=[("Excel XLSX", "*.xlsx")])
        if not path: return
        try:
            wb = load_workbook(path, data_only=True, read_only=True)
            ws = wb.active; rows = ws.iter_rows(values_only=True); header = next(rows, None)
            if not header: wb.close(); messagebox.showerror("Ошибка импорта", "Excel-файл пуст."); return

            def norm(value): return "".join(str(value or "").strip().lower().replace("ё", "е").split()).replace("_", "")
            aliases = {
                "номер": "number", "№": "number", "студент": "student", "фио": "student",
                "группа": "group", "учебнаягруппа": "group", "датарождения": "birth_date",
                "снилс": "snils", "телефон": "phone", "email": "email", "почта": "email"
            }
            mapping = {aliases[norm(cell)]: idx for idx, cell in enumerate(header) if norm(cell) in aliases}
            if {"student", "group"} - set(mapping):
                wb.close(); messagebox.showerror("Ошибка импорта", "В файле обязательно должны быть столбцы: 'Студент' и 'Группа'."); return

            db_groups = self.get_groups()
            group_map = {g["name"].strip().lower(): g for g in db_groups}

            all_rows = [r for r in rows if r and any(v is not None and str(v).strip() for v in r)]
            file_groups_summary = {}
            for r in all_rows:
                g_val = str(r[mapping["group"]] or "").strip()
                if not g_val: continue
                file_groups_summary[g_val] = file_groups_summary.get(g_val, 0) + 1

            missing_groups = [g for g in file_groups_summary if g.lower() not in group_map]
            if missing_groups:
                wb.close()
                msg = "Внимание! Импорт остановлен, чтобы не перепутать группы.\n\nВ файле указаны группы, которых НЕТ в базе:\n"
                msg += "\n".join(f"• «{g}»" for g in missing_groups)
                msg += "\n\nСоздайте эти группы во вкладке «Учебные группы»."
                messagebox.showerror("Несовпадение групп", msg); return

            confirm_msg = "В файле обнаружены следующие группы:\n\n"
            for g_name, count in file_groups_summary.items():
                db_g = group_map[g_name.lower()]
                confirm_msg += f"• Из файла: «{g_name}» ➔ В базу: «{db_g['name']}» ({count} студ.)\n"
            confirm_msg += "\nСтуденты будут распределены строго по указанным группам. Продолжить?"

            if not messagebox.askyesno("Подтверждение импорта групп", confirm_msg):
                wb.close(); return

            imported, skipped = 0, []
            for excel_row, values in enumerate(all_rows, start=2):
                def val(field):
                    idx = mapping.get(field)
                    return values[idx] if idx is not None and idx < len(values) else None

                group_name = str(val("group") or "").strip()
                full_name = " ".join(str(val("student") or "").replace("\n", " ").split())
                if not group_name or not full_name: skipped.append(f"Строка {excel_row}: пусто."); continue

                db_group = group_map.get(group_name.lower())
                parts = full_name.split()
                last_name = parts[0]
                first_name = parts[1] if len(parts) > 1 else ""
                middle_name = " ".join(parts[2:]) if len(parts) > 2 else ""

                if not first_name: skipped.append(f"Строка {excel_row}: не заполнено имя."); continue
                birth_raw, birth = val("birth_date"), None
                if birth_raw not in (None, ""):
                    try:
                        if isinstance(birth_raw, datetime): birth = birth_raw.date()
                        elif isinstance(birth_raw, date): birth = birth_raw
                        else:
                            raw = str(birth_raw).strip()
                            try: birth = date.fromisoformat(raw)
                            except ValueError: birth = datetime.strptime(raw, "%d.%m.%Y").date()
                        if birth > date.today(): raise ValueError()
                    except Exception: skipped.append(f"Строка {excel_row}: неверная дата."); continue

                def txt(field):
                    v = val(field)
                    if v is None: return ""
                    if field in ("number", "snils") and isinstance(v, float) and v.is_integer(): v = int(v)
                    return str(v).strip()

                db.query("""INSERT INTO students(student_number,group_id,last_name,first_name,middle_name,birth_date,snils,phone,email)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                         (txt("number"), db_group["id"], last_name, first_name, middle_name, birth, txt("snils"), txt("phone"), txt("email")))
                imported += 1

            wb.close(); self.refresh_all()
            summary = f"Успешно импортировано студентов: {imported}."
            if skipped: summary += f"\nПропущено строк: {len(skipped)}."
            messagebox.showinfo("Импорт завершен", summary)
        except Exception as exc: messagebox.showerror("Ошибка при чтении Excel", str(exc))

    def print_student_docs(self):
        sid = self._selected_id(self.students_tree, "студента")
        if sid is None: return
        docs = db.query("SELECT * FROM student_documents WHERE student_id=%s ORDER BY id", (sid,), fetch=True)
        if not docs: messagebox.showinfo("Нет документов", "У студента нет загруженных документов."); return
        if not messagebox.askyesno("Печать", f"Отправить на печать все {len(docs)} документа(ов)?"): return
        for d in docs:
            try: documents.print_file(d["file_path"])
            except Exception as e: print(f"Ошибка печати: {e}")
        messagebox.showinfo("Печать", "Задания отправлены в очередь печати.")

    def generate_bulk_documents(self):
        """Формирует выбранный шаблон для всех выделенных студентов и сохраняет файлы в архиве."""
        selected = self.students_tree.selection()
        if not selected:
            messagebox.showwarning("Выбор не сделан", "Выделите одного или нескольких студентов в таблице.")
            return

        student_ids = [int(self.students_tree.item(item, "values")[0]) for item in selected]
        templates = db.query("SELECT * FROM document_templates ORDER BY name", fetch=True) or []
        if not templates:
            messagebox.showinfo("Нет шаблонов", "Сначала добавьте шаблон во вкладке «Шаблоны».")
            return

        win = ctk.CTkToplevel(self)
        win.title("Массовое формирование документов")
        win.geometry("560x330")
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text=f"Выбрано студентов: {len(student_ids)}", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(18, 6))
        ctk.CTkLabel(win, text="Шаблон:").pack(anchor="w", padx=20)
        template_map = {f'{t["name"]} ({t["file_type"].upper()})': t for t in templates}
        template_combo = ctk.CTkComboBox(win, values=list(template_map), width=510)
        template_combo.pack(padx=20, pady=(3, 10))
        template_combo.set(next(iter(template_map)))

        ctk.CTkLabel(win, text="Причина материальной помощи (для соответствующего шаблона):").pack(anchor="w", padx=20)
        reason_combo = ctk.CTkComboBox(win, values=documents.AID_REASONS, width=510)
        reason_combo.pack(padx=20, pady=(3, 10))
        reason_combo.set(documents.AID_REASONS[0])

        print_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(win, text="Отправить сформированные документы на печать", variable=print_var).pack(anchor="w", padx=20, pady=8)

        def generate():
            template = template_map.get(template_combo.get())
            if not template:
                messagebox.showwarning("Шаблон", "Выберите шаблон из списка.")
                return
            is_aid = "материальн" in template["name"].lower()
            reason = reason_combo.get().strip()
            if is_aid and not reason:
                messagebox.showwarning("Причина", "Выберите причину материальной помощи.")
                return

            placeholders = ",".join(["%s"] * len(student_ids))
            students = db.query(f"""SELECT s.*, g.name AS group_name, g.course, sp.name AS specialty_name
                FROM students s JOIN study_groups g ON g.id=s.group_id
                LEFT JOIN specialties sp ON sp.id=g.specialty_id
                WHERE s.id IN ({placeholders})
                ORDER BY s.last_name,s.first_name,s.middle_name""", tuple(student_ids), fetch=True) or []
            if not students:
                messagebox.showinfo("Нет студентов", "Выбранные студенты не найдены.")
                return

            win.destroy()
            created, errors, print_paths = 0, [], []
            for student in students:
                group = {"id": student["group_id"], "name": student["group_name"],
                         "course": student["course"], "specialty_name": student["specialty_name"]}
                fio = documents.safe_name(" ".join(filter(None, [student["last_name"], student["first_name"], student.get("middle_name", "")])))
                try:
                    values = documents.student_values(student, group, reason=reason if is_aid else "")
                    if is_aid:
                        genitive, student_word = documents.inflect_fio_genitive(
                            student["last_name"], student["first_name"], student.get("middle_name", ""))
                        values = documents.student_values(student, group, reason=reason,
                                                           aid_fio_gen=genitive, student_word=student_word)

                    filename = f"{student['id']}_{fio}_{documents.safe_name(template['name'])}.{template['file_type']}"
                    output = documents.ARCHIVE / filename
                    if template["file_type"] == "docx":
                        documents.fill_docx(template["file_path"], output, values)
                    else:
                        documents.fill_xlsx(template["file_path"], output, values)

                    stored = str(output.resolve())
                    title = f"{template['name']} — {student['last_name']} {student['first_name']}"
                    category = "Заявления на матпомощь" if is_aid else "Сформированные документы"
                    db.query("""INSERT INTO archive_documents(group_id,student_id,title,file_name,file_path,category)
                        VALUES(%s,%s,%s,%s,%s,%s)""",
                        (student["group_id"], student["id"], title, Path(stored).name, stored, category))
                    db.query("""INSERT INTO student_documents(student_id,title,file_name,file_path,file_type,is_material_aid)
                        VALUES(%s,%s,%s,%s,%s,%s)""",
                        (student["id"], title, Path(stored).name, stored,
                         template["file_type"], is_aid))
                    created += 1
                    print_paths.append(stored)
                except Exception as exc:
                    errors.append(f"{fio}: {exc}")

            self.refresh_all()
            if print_var.get() and print_paths:
                for path in print_paths:
                    try:
                        documents.print_file(path)
                    except Exception as exc:
                        errors.append(f"Печать {Path(path).name}: {exc}")

            summary = f"Сформировано документов: {created} из {len(students)}."
            if errors:
                summary += "\n\nОшибки:\n" + "\n".join(errors[:10])
            messagebox.showinfo("Массовое формирование завершено", summary)

        ctk.CTkButton(win, text="Сформировать документы", command=generate,
                      fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, width=220).pack(pady=16)

    def refresh_docs(self):
        term = self.doc_search_var.get().strip() if hasattr(self, "doc_search_var") else ""
        aid_f = self.doc_aid_filter.get() if hasattr(self, "doc_aid_filter") else "Все"
        sql = """SELECT d.*,concat_ws(' ',s.last_name,s.first_name,s.middle_name) AS student_name
            FROM student_documents d JOIN students s ON s.id=d.student_id WHERE 1=1"""
        params = []
        if term:
            sql += " AND (concat_ws(' ',s.last_name,s.first_name,s.middle_name) ILIKE %s OR d.title ILIKE %s)"
            params.extend([f"%{term}%", f"%{term}%"])
        if aid_f == "Только мат. помощь": sql += " AND d.is_material_aid = TRUE"
        elif aid_f == "Без мат. помощи": sql += " AND d.is_material_aid = FALSE"
        sql += " ORDER BY d.uploaded_at DESC"
        rows = self.run_db(lambda: db.query(sql, params, fetch=True))
        if rows is None: return
        self.docs_tree.delete(*self.docs_tree.get_children())
        for d in rows:
            self.docs_tree.insert("", "end", values=(d["id"], d["student_name"], d["title"], d["file_name"],
                                                     "Да" if d["is_material_aid"] else "Нет", d["uploaded_at"].strftime("%d.%m.%Y %H:%M")))

    def upload_student_doc(self):
        sid = self._selected_id(self.students_tree, "студента")
        if sid is None:
            self._switch_tab("students")
            messagebox.showinfo("Выбор студента", "Сначала выберите студента в списке, затем нажмите «Загрузить документ»."); return
        path = filedialog.askopenfilename(title="Выберите документ", filetypes=[("Документы", "*.docx *.xlsx *.pdf *.doc *.xls"), ("Все файлы", "*.*")])
        if not path: return
        title = ctk.CTkInputDialog(title="Название", text="Введите название документа:").get_input()
        if not title: return
        aid = messagebox.askyesno("Мат. помощь", "Относится ли документ к материальной помощи?")
        try:
            stored = documents.copy_into(path, documents.DOCS, f"student_{sid}_")
            db.query("""INSERT INTO student_documents(student_id,title,file_name,file_path,file_type,is_material_aid)
                VALUES(%s,%s,%s,%s,%s,%s)""", (sid, title, Path(stored).name, stored, Path(stored).suffix.lower().lstrip("."), aid))
            self.refresh_all(); messagebox.showinfo("Успешно", "Документ загружен студенту.")
        except Exception as exc: messagebox.showerror("Ошибка загрузки", str(exc))

    def _doc_record(self):
        did = self._selected_id(self.docs_tree, "документ")
        return db.one("SELECT * FROM student_documents WHERE id=%s", (did,)) if did is not None else None
    def open_selected_doc(self):
        d = self._doc_record()
        if d: documents.open_file(d["file_path"])
    def download_selected_doc(self):
        d = self._doc_record()
        if d: self._save_copy(d["file_path"], d["file_name"])
    def print_selected_doc(self):
        d = self._doc_record()
        if d: documents.print_file(d["file_path"])
    def delete_selected_doc(self):
        d = self._doc_record()
        if not d: return
        if not messagebox.askyesno("Удаление", "Удалить выбранный документ студента?"): return
        db.query("DELETE FROM student_documents WHERE id=%s", (d["id"],))
        try: Path(d["file_path"]).unlink(missing_ok=True)
        except OSError: pass
        self.refresh_all()

    def refresh_templates(self):
        term = self.template_search_var.get().strip() if hasattr(self, "template_search_var") else ""
        fmt = self.template_format_filter.get() if hasattr(self, "template_format_filter") else "Все"
        sql = "SELECT * FROM document_templates WHERE 1=1"
        params = []
        if term:
            sql += " AND (name ILIKE %s OR description ILIKE %s)"
            params.extend([f"%{term}%", f"%{term}%"])
        if fmt != "Все": sql += " AND file_type = %s"; params.append(fmt.lower())
        sql += " ORDER BY name"
        rows = self.run_db(lambda: db.query(sql, params, fetch=True))
        if rows is None: return
        self.templates_tree.delete(*self.templates_tree.get_children())
        for t in rows:
            self.templates_tree.insert("", "end", values=(t["id"], t["name"], t["file_type"].upper(), t["file_name"], t["description"]))

    def _template_record(self):
        tid = self._selected_id(self.templates_tree, "шаблон")
        return db.one("SELECT * FROM document_templates WHERE id=%s", (tid,)) if tid is not None else None
    def upload_template(self):
        path = filedialog.askopenfilename(title="Выберите шаблон", filetypes=[("Шаблоны Word/Excel", "*.docx *.xlsx")])
        if not path: return
        ext = Path(path).suffix.lower().lstrip(".")
        name = ctk.CTkInputDialog(title="Название", text="Введите название шаблона:").get_input()
        if not name: return
        desc = ctk.CTkInputDialog(title="Описание", text="Описание шаблона (необязательно):").get_input() or ""
        try:
            stored = documents.copy_into(path, documents.TEMPLATES)
            db.query("""INSERT INTO document_templates(name,file_name,file_path,file_type,description)
                VALUES(%s,%s,%s,%s,%s)""", (name, Path(stored).name, stored, ext, desc))
            self.refresh_templates()
        except Exception as exc: messagebox.showerror("Ошибка", str(exc))

    def download_template(self):
        t = self._template_record()
        if t: self._save_copy(t["file_path"], t["file_name"])
    def open_template(self):
        t = self._template_record()
        if t: documents.open_file(t["file_path"])
    def delete_template(self):
        t = self._template_record()
        if not t: return
        if not messagebox.askyesno("Удаление", "Удалить шаблон из базы и хранилища?"): return
        db.query("DELETE FROM document_templates WHERE id=%s", (t["id"],))
        try: Path(t["file_path"]).unlink(missing_ok=True)
        except OSError: pass
        self.refresh_templates()

    def refresh_archive(self):
        term = self.archive_search.get().strip() if hasattr(self, "archive_search") else ""
        cat = self.archive_cat_filter.get() if hasattr(self, "archive_cat_filter") else "Все"
        sql = """SELECT a.*,g.name AS group_name,concat_ws(' ',s.last_name,s.first_name,s.middle_name) AS student_name
            FROM archive_documents a LEFT JOIN study_groups g ON g.id=a.group_id LEFT JOIN students s ON s.id=a.student_id WHERE 1=1"""
        params = []
        if term:
            sql += " AND (a.title ILIKE %s OR a.file_name ILIKE %s OR concat_ws(' ',s.last_name,s.first_name,s.middle_name) ILIKE %s)"
            params.extend([f"%{term}%", f"%{term}%", f"%{term}%"])
        if cat != "Все": sql += " AND a.category = %s"; params.append(cat)
        sql += " ORDER BY a.archived_at DESC"
        rows = self.run_db(lambda: db.query(sql, params, fetch=True))
        if rows is None: return
        self.archive_tree.delete(*self.archive_tree.get_children())
        for a in rows:
            self.archive_tree.insert("", "end", values=(a["id"], a["title"], a["category"], a["file_name"],
                                                        a["group_name"] or "", a["student_name"] or "", a["archived_at"].strftime("%d.%m.%Y %H:%M")))
        cats = db.query("SELECT DISTINCT category FROM archive_documents WHERE category IS NOT NULL", fetch=True) or []
        opts = ["Все"] + [c["category"] for c in cats]
        cur = self.archive_cat_filter.get()
        self.archive_cat_filter.configure(values=opts)
        self.archive_cat_filter.set(cur if cur in opts else "Все")

    def upload_archive(self):
        path = filedialog.askopenfilename(title="Выберите документ", filetypes=[("Документы", "*.docx *.xlsx *.pdf"), ("Все файлы", "*.*")])
        if not path: return
        title = ctk.CTkInputDialog(title="Название", text="Введите название для архива:").get_input()
        if not title: return
        cat = ctk.CTkInputDialog(title="Категория", text="Категория (например, Соцпаспорт, Отчет):").get_input() or "Общие документы"
        try:
            stored = documents.copy_into(path, documents.ARCHIVE)
            db.query("""INSERT INTO archive_documents(title,file_name,file_path,category) VALUES(%s,%s,%s,%s)""",
                     (title, Path(stored).name, stored, cat))
            self.refresh_archive(); messagebox.showinfo("Архив", "Файл успешно архивирован.")
        except Exception as exc: messagebox.showerror("Ошибка", str(exc))

    def _archive_record(self):
        aid = self._selected_id(self.archive_tree, "архивный документ")
        return db.one("SELECT * FROM archive_documents WHERE id=%s", (aid,)) if aid is not None else None
    def open_archive(self):
        a = self._archive_record()
        if a: documents.open_file(a["file_path"])
    def download_archive(self):
        a = self._archive_record()
        if a: self._save_copy(a["file_path"], a["file_name"])
    def print_archive(self):
        a = self._archive_record()
        if a: documents.print_file(a["file_path"])
    def delete_archive(self):
        a = self._archive_record()
        if not a: return
        if not messagebox.askyesno("Удаление", f"Удалить «{a['title']}» из архива?"): return
        db.query("DELETE FROM archive_documents WHERE id=%s", (a["id"],))
        try: Path(a["file_path"]).unlink(missing_ok=True)
        except OSError: pass
        self.refresh_archive()

    def _save_copy(self, source, suggested):
        if not Path(source).exists():
            messagebox.showerror("Файл не найден", f"Файл не найден на диске:\n{source}"); return
        target = filedialog.asksaveasfilename(title="Сохранить копию", initialfile=suggested)
        if target:
            try:
                shutil.copy2(source, target)
                messagebox.showinfo("Готово", "Копия успешно сохранена.")
            except Exception as e: messagebox.showerror("Ошибка сохранения", str(e))


if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as exc:
        messagebox.showerror("Ошибка запуска", f"{exc}\n\nПроверьте настройки PostgreSQL в db.py.")