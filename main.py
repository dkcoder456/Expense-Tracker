# Dorm Monthly Expense Tracker
# Importing libaries and modules for the expense tracker application
from __future__ import annotations

import json
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, asdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional

DATA_FILE = Path(__file__).with_name("expenses.json")

# Change the starting monthly budget here:
DEFAULT_BUDGET = Decimal("1200.00")

# Edit your categories below. You can add or remove categories as you like.
# Keep the quotes and commas in the right places.
CATEGORIES = [
    "Rent",
    "Food",
    "Utilities",
    "Transport",
    "Study Supplies",
    "Social",
    "Health",
    "Personal",
    "Other",
]

# Format a monetary amount as a string
def format_money(amount: Decimal) -> str:
    return f"${amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"

# Parse a string into a Decimal, ensuring it's a valid monetary amount
def parse_money(value: str) -> Decimal:
    try:
        return Decimal(value.strip().replace("$", "")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("Enter a valid number like 12.50")

# Parse a date string in YYYY-MM-DD format
def parse_date(value: str) -> date:
    if not value.strip():
        return date.today()
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Enter a date in YYYY-MM-DD format") from exc

# Play a sound on Windows systems that is made by default in Windows. This function is a no-op on non-Windows platforms.
def _play_windows_sound(sound_name: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import winsound
        winsound.PlaySound(sound_name, winsound.SND_ALIAS | winsound.SND_ASYNC)
    except Exception:
        pass

# Play different types of sounds for success, error, and info notifications
# Play a success sound for notifications
def play_success_sound() -> None:
    _play_windows_sound("SystemAsterisk")

# Play an error sound for notifications
def play_error_sound() -> None:
    _play_windows_sound("SystemHand")

# Play an informational sound for notifications
def play_info_sound() -> None:
    _play_windows_sound("SystemQuestion")

# Data class representing an expense entry
@dataclass
class Expense:
    id: str
    date: date
    category: str
    description: str
    amount: Decimal
    recurring: bool = False
    # Convert the Expense object to a dictionary for JSON serialization
    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "category": self.category,
            "description": self.description,
            "amount": str(self.amount),
            "recurring": self.recurring,
        }
    # Create an Expense object from a dictionary, typically loaded from JSON
    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Expense":
        # Support expense files created by the earlier version of the project,
        # which stored a single "name" field instead of category/description.
        legacy_name = str(data.get("name", ""))
        legacy_categories = {
            "groceries": "Food",
            "utilities": "Utilities",
            "transportation": "Transport",
        }
        category = str(data.get("category") or legacy_categories.get(legacy_name.lower(), "Other"))
        description = str(data.get("description") or legacy_name or "No description")
        return cls(
            id=str(data["id"]),
            date=parse_date(str(data["date"])),
            category=category,
            description=description,
            amount=parse_money(str(data["amount"])),
            recurring=bool(data.get("recurring", False)),
        )

# Class to manage the expense tracker, including loading, saving, and manipulating expenses
class ExpenseTracker:
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.expenses: List[Expense] = []
        self.budget = DEFAULT_BUDGET
        self.load()

    def load(self) -> None:
        if not self.storage_path.exists():
            self.save()
            return
        # Load the expense data from the JSON file, handling potential errors gracefully
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            saved_budget = parse_money(str(payload.get("budget", DEFAULT_BUDGET)))
            saved_default = payload.get("default_budget")
            self.expenses = [Expense.from_dict(item) for item in payload.get("expenses", [])]
            # If there are no expenses, set the budget to the default and save it back to the file
            if not self.expenses:
                self.budget = DEFAULT_BUDGET
                payload["budget"] = str(DEFAULT_BUDGET)
                payload["default_budget"] = str(DEFAULT_BUDGET)
                self.storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            elif saved_default is None:
                self.budget = saved_budget
                payload["default_budget"] = str(DEFAULT_BUDGET)
                self.storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            else:
                try:
                    default_at_save = parse_money(str(saved_default))
                except ValueError:
                    default_at_save = DEFAULT_BUDGET
                if saved_budget == default_at_save and default_at_save != DEFAULT_BUDGET:
                    self.budget = DEFAULT_BUDGET
                else:
                    self.budget = saved_budget
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            print("Warning: Could not read expense file. Starting fresh.")
            self.expenses = []
            self.budget = DEFAULT_BUDGET
    # Save the current state of the expense tracker to the JSON file
    def save(self) -> None:
        self.storage_path.write_text(
            json.dumps(
                {
                    "budget": str(self.budget),
                    "default_budget": str(DEFAULT_BUDGET),
                    "expenses": [expense.to_dict() for expense in self.expenses],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    # Add a new expense to the tracker and save the updated state
    def add_expense(self, expense: Expense) -> None:
        self.expenses.append(expense)
        self.save()
    # Remove an expense by its ID from the tracker and save the updated state
    def remove_expense(self, expense_id: str) -> bool:
        original_length = len(self.expenses)
        self.expenses = [expense for expense in self.expenses if expense.id != expense_id]
        if len(self.expenses) < original_length:
            self.save()
            return True
        return False
    # Retrieve all expenses for a specific month and year
    def monthly_expenses(self, year: int, month: int) -> List[Expense]:
        return [expense for expense in self.expenses if expense.date.year == year and expense.date.month == month]
    # Calculate the total expenses for each category from a list of expenses
    def category_totals(self, expenses: List[Expense]) -> Dict[str, Decimal]:
        totals: Dict[str, Decimal] = {category: Decimal("0.00") for category in CATEGORIES}
        totals["Other"] = totals.get("Other", Decimal("0.00"))
        for expense in expenses:
            totals[expense.category] = totals.get(expense.category, Decimal("0.00")) + expense.amount
        return totals
    # Set a new budget amount and save the updated state
    def set_budget(self, amount: Decimal) -> None:
        self.budget = amount
        self.save()
    # Get the expense with the highest amount from a list of expenses
    def get_highest_expense(self, expenses: List[Expense]) -> Optional[Expense]:
        return max(expenses, key=lambda e: e.amount) if expenses else None
    # Get the category with the highest total spending from a list of expenses
    def get_most_spent_category(self, expenses: List[Expense]) -> Optional[tuple]:
        totals = self.category_totals(expenses)
        if not totals or all(v == Decimal("0.00") for v in totals.values()):
            return None
        category, amount = max(totals.items(), key=lambda item: item[1])
        return (category, amount) if amount > Decimal("0.00") else None
    # Calculate the average daily spending for a given list of expenses and number of days in the month
    def get_avg_daily_spending(self, expenses: List[Expense], month_days: int) -> Decimal:
        if not expenses or month_days == 0:
            return Decimal("0.00")
        total = sum((e.amount for e in expenses), Decimal("0.00"))
        return (total / Decimal(str(month_days))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # Calculate the total expenses for the previous month based on the current year and month
    def get_previous_month_total(self, year: int, month: int) -> Decimal:
        if month == 1:
            prev_month, prev_year = 12, year - 1
        else:
            prev_month, prev_year = month - 1, year
        expenses = self.monthly_expenses(prev_year, prev_month)
        return sum((e.amount for e in expenses), Decimal("0.00"))

# UI Functions for Command-Line Interface (CLI)
def print_header(title: str) -> None:
    pass


def prompt_choice(prompt: str, options: List[str]) -> str:
    pass


def list_expenses(expenses: List[Expense]) -> None:
    pass


def show_month_summary(tracker: ExpenseTracker) -> None:
    pass


def add_expense_flow(tracker: ExpenseTracker) -> None:
    pass


def remove_expense_flow(tracker: ExpenseTracker) -> None:
    pass


def set_budget_flow(tracker: ExpenseTracker) -> None:
    pass

# UI Class for Graphical User Interface (GUI) using Tkinter
class ExpenseTrackerApp:
    def __init__(self, root: tk.Tk, tracker: ExpenseTracker):
        self.root = root
        self.tracker = tracker
        self.root.title("Dorm Monthly Expense Tracker")
        self.root.geometry("980x660")
        self.root.minsize(900, 620)
        self.root.resizable(True, True)
        self.root.configure(background="#e2e8f0")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#e2e8f0")
        style.configure("Card.TFrame", background="#ffffff", relief="flat", borderwidth=1)
        style.configure("Section.TFrame", background="#f8fbff", relief="flat", borderwidth=1)
        style.configure("Header.TFrame", background="#0f172a")
        style.configure("Header.TLabel", font=("Arial", 18, "bold"), background="#0f172a", foreground="#f8fafc")
        style.configure("Header.Subtitle.TLabel", font=("Arial", 10), background="#0f172a", foreground="#cbd5e1")
        style.configure("TLabel", background="#e2e8f0", font=("Arial", 11), foreground="#1f2937")
        style.configure("Heading.TLabel", font=("Arial", 20, "bold"), background="#e2e8f0", foreground="#0f172a")
        style.configure("Subheading.TLabel", font=("Arial", 13, "bold"), background="#e2e8f0", foreground="#0f172a")
        style.configure("Accent.TButton", background="#0ea5e9", foreground="#ffffff", font=("Arial", 11, "bold"), padding=10, borderwidth=0)
        style.map(
            "Accent.TButton",
            background=[("active", "#0284c7"), ("pressed", "#0369a1")],
            foreground=[("disabled", "#cbd5e1")],
        )
        style.configure("Nav.TButton", background="#f8fbff", foreground="#0f172a", font=("Arial", 10, "bold"), padding=6, borderwidth=1, relief="flat")
        style.map(
            "Nav.TButton",
            background=[("active", "#bae6fd"), ("pressed", "#7dd3fc")],
        )
        style.configure("TButton", padding=10)
        style.configure("TEntry", fieldbackground="#f8fbff", background="#f8fbff", foreground="#0f172a")
        style.configure("TCombobox", fieldbackground="#f8fbff", background="#f8fbff", foreground="#0f172a")
        style.configure("Accent.TLabel", font=("Arial", 12, "bold"), background="#e2e8f0", foreground="#0f172a")
        style.configure("NavStat.TLabel", font=("Arial", 10), background="#0f172a", foreground="#cbd5e1")
        style.configure("NavStatValue.TLabel", font=("Arial", 11, "bold"), background="#0f172a", foreground="#0ea5e9")
        style.configure("CardValue.TLabel", font=("Arial", 22, "bold"), background="#ffffff", foreground="#0f172a")
        style.configure("Hint.TLabel", font=("Arial", 10), background="#f8fbff", foreground="#64748b")
        style.configure("Info.TLabel", font=("Arial", 10), background="#e2e8f0", foreground="#475569")
        style.configure("Treeview", font=("Arial", 10), rowheight=30, background="#ffffff", fieldbackground="#ffffff", foreground="#1f2937")
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#4a6282", foreground="#0f172a")
        style.map("Treeview", background=[("selected", "#bae6fd")], foreground=[("selected", "#0f172a")])
        style.configure("TNotebook", background="#e2e8f0")
        style.configure("TNotebook.Tab", padding=[14, 10], font=("Arial", 11, "bold"), background="#f8fbff")
        style.configure("TLabelframe", background="#e2e8f0")
        style.configure("TLabelframe.Label", font=("Arial", 12, "bold"), background="#e2e8f0", foreground="#0f172a")
        style.configure("TSeparator", background="#cbd5e1")

        self.setup_ui()
        self.refresh_all()

    def setup_ui(self) -> None:
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Enhanced Header with Navigation Bar
        header_frame = ttk.Frame(main_frame, padding=18, style="Header.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 0))
        
        # Top section: Title and Quick Stats
        title_frame = ttk.Frame(header_frame, style="Header.TFrame")
        title_frame.pack(fill=tk.X)
        ttk.Label(title_frame, text="💰💵 Dorm Monthly Expense Tracker", style="Header.TLabel").pack(side=tk.LEFT)
        
        # Quick stats on the right
        self.nav_budget_label = ttk.Label(title_frame, text="Budget: --", style="NavStatValue.TLabel")
        self.nav_budget_label.pack(side=tk.RIGHT, padx=(20, 0))
        self.nav_spent_label = ttk.Label(title_frame, text="Spent: --", style="NavStatValue.TLabel")
        self.nav_spent_label.pack(side=tk.RIGHT, padx=20)
        
        # Subtitle
        ttk.Label(
            header_frame,
            text="A modern finance dashboard for dorm life: smart, simple and easy to use.",
            style="Header.Subtitle.TLabel",
            wraplength=860,
        ).pack(anchor=tk.W, pady=(8, 0))
        
        # Navigation buttons bar
        nav_bar_frame = ttk.Frame(main_frame, style="Header.TFrame", padding=(18, 12, 18, 12))
        nav_bar_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(nav_bar_frame, text="📊 Summary", style="Nav.TButton", command=lambda: self.notebook.select(0)).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_bar_frame, text="➕ Add Expense", style="Nav.TButton", command=lambda: self.notebook.select(1)).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_bar_frame, text="📋 View All", style="Nav.TButton", command=lambda: self.notebook.select(2)).pack(side=tk.LEFT, padx=4)
        ttk.Button(nav_bar_frame, text="💳 Budget", style="Nav.TButton", command=lambda: self.notebook.select(3)).pack(side=tk.LEFT, padx=4)
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 16))

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.summary_tab = ttk.Frame(self.notebook)
        self.add_tab = ttk.Frame(self.notebook)
        self.view_tab = ttk.Frame(self.notebook)
        self.budget_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.summary_tab, text="Summary")
        self.notebook.add(self.add_tab, text="Add Expense")
        self.notebook.add(self.view_tab, text="View Expenses")
        self.notebook.add(self.budget_tab, text="Budget")

        self.setup_summary_tab()
        self.setup_add_tab()
        self.setup_view_tab()
        self.setup_budget_tab()

    def setup_summary_tab(self) -> None:
        frame = ttk.Frame(self.summary_tab, padding=18, style="Section.TFrame")
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=8)

        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, pady=(0, 12))

        month_frame = ttk.Frame(top_frame)
        month_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(month_frame, text="Select Month:", style="Subheading.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        self.month_var = tk.StringVar(value=f"{date.today().year}-{date.today().month:02d}")
        ttk.Entry(month_frame, textvariable=self.month_var, width=12).pack(side=tk.LEFT)
        ttk.Button(month_frame, text="Refresh", style="Accent.TButton", command=self.refresh_summary).pack(side=tk.LEFT, padx=10)

        quick_add_frame = ttk.Frame(top_frame)
        quick_add_frame.pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(quick_add_frame, text="➕ Quick Add", style="Accent.TButton", command=self.switch_to_add_tab).pack()

        self.progress_var = tk.DoubleVar(value=0.0)
        progress_frame = ttk.Frame(top_frame)
        progress_frame.pack(side=tk.RIGHT, anchor=tk.E)
        ttk.Label(progress_frame, text="Budget health:", style="Subheading.TLabel").pack(anchor=tk.E)
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=220, variable=self.progress_var, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(6, 0))

        card_frame = ttk.Frame(frame)
        card_frame.pack(fill=tk.X, pady=(0, 12))

        self.cards = {}
        for index, label in enumerate(["Budget", "Spent", "Remaining"]):
            card = ttk.Frame(card_frame, style="Card.TFrame", padding=18)
            card.grid(row=0, column=index, sticky=tk.NSEW, padx=6)
            card_frame.columnconfigure(index, weight=1)
            ttk.Label(card, text=label, style="Subheading.TLabel").pack(anchor=tk.W)
            value_label = ttk.Label(card, text="$0.00", style="CardValue.TLabel")
            value_label.pack(anchor=tk.W, pady=(10, 0))
            self.cards[label.lower()] = value_label

        stats_card_frame = ttk.Frame(frame)
        stats_card_frame.pack(fill=tk.X, pady=(0, 12))

        self.stats_cards = {}
        for index, label in enumerate(["Highest Expense", "Daily Average", "Top Category"]):
            stat_card = ttk.Frame(stats_card_frame, style="Card.TFrame", padding=18)
            stat_card.grid(row=0, column=index, sticky=tk.NSEW, padx=6)
            stats_card_frame.columnconfigure(index, weight=1)
            ttk.Label(stat_card, text=label, style="Subheading.TLabel").pack(anchor=tk.W)
            stat_value = ttk.Label(stat_card, text="—", font=("Arial", 14, "bold"), background="#ffffff", foreground="#0f172a")
            stat_value.pack(anchor=tk.W, pady=(10, 0))
            self.stats_cards[label.lower().replace(" ", "_")] = stat_value

        insight_frame = ttk.Frame(frame, style="Card.TFrame", padding=14)
        insight_frame.pack(fill=tk.X, pady=(0, 12))
        self.status_label = ttk.Label(insight_frame, text="Budget status: Ready", font=("Arial", 12, "bold"), foreground="#16a34a")
        self.status_label.pack(anchor=tk.W)
        self.insight_label = ttk.Label(insight_frame, text="Add your first expense to start tracking your dorm spending.", style="Hint.TLabel", wraplength=820)
        self.insight_label.pack(anchor=tk.W, pady=(6, 0))

        content_frame = ttk.Frame(frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        breakdown_frame = ttk.LabelFrame(content_frame, text="Category Breakdown", padding=10)
        breakdown_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6), pady=6)
        self.breakdown_text = tk.Text(breakdown_frame, width=35, height=18, state=tk.DISABLED, bg="#f8fbff", bd=0, relief=tk.FLAT, highlightthickness=0, padx=10, pady=10)
        self.breakdown_text.pack(fill=tk.BOTH, expand=True)

        recent_frame = ttk.LabelFrame(content_frame, text="Recent Expenses", padding=10)
        recent_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        self.recent_text = tk.Text(recent_frame, width=45, height=18, state=tk.DISABLED, bg="#f8fafd", bd=0, relief=tk.FLAT, highlightthickness=0, padx=10, pady=10)
        self.recent_text.tag_configure("heading", font=("Arial", 10, "bold"), foreground="#0f172a")
        self.recent_text.tag_configure("amount", foreground="#2563eb")
        self.recent_text.pack(fill=tk.BOTH, expand=True)

        comparison_frame = ttk.Frame(frame, style="Card.TFrame", padding=14)
        comparison_frame.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(comparison_frame, text="📊 Month Comparison", style="Subheading.TLabel").pack(anchor=tk.W)
        self.comparison_text = tk.Text(comparison_frame, width=80, height=3, state=tk.DISABLED, bg="#f8fbff", bd=0, relief=tk.FLAT, highlightthickness=0, padx=10, pady=8)
        self.comparison_text.tag_configure("increase", foreground="#dc2626")
        self.comparison_text.tag_configure("decrease", foreground="#16a34a")
        self.comparison_text.pack(fill=tk.BOTH, expand=True)
    # Setup the "Add Expense" tab with input fields and buttons
    def setup_add_tab(self) -> None:
        frame = ttk.Frame(self.add_tab, padding=18, style="Section.TFrame")
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=8)

        header_frame = ttk.Frame(frame)
        header_frame.pack(fill=tk.X, pady=(0, 14))
        ttk.Label(header_frame, text="Add a new expense", style="Heading.TLabel").pack(anchor=tk.W)
        ttk.Label(header_frame, text="Capture spending quickly so your budget stays clear and realistic.", style="Hint.TLabel").pack(anchor=tk.W, pady=(4, 0))

        content_frame = ttk.Frame(frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        form_frame = ttk.Frame(content_frame, style="Card.TFrame", padding=16)
        form_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        form_frame.columnconfigure(1, weight=1)

        ttk.Label(form_frame, text="Date (YYYY-MM-DD):", style="Subheading.TLabel").grid(row=0, column=0, sticky=tk.W, pady=8)
        self.add_date_var = tk.StringVar(value=str(date.today()))
        ttk.Entry(form_frame, textvariable=self.add_date_var, width=30).grid(row=0, column=1, sticky=tk.EW, pady=8)

        ttk.Label(form_frame, text="Category:", style="Subheading.TLabel").grid(row=1, column=0, sticky=tk.W, pady=8)
        self.add_category_var = tk.StringVar(value=CATEGORIES[0])
        category_combo = ttk.Combobox(form_frame, textvariable=self.add_category_var, values=CATEGORIES, state="readonly", width=28)
        category_combo.grid(row=1, column=1, sticky=tk.EW, pady=8)

        ttk.Label(form_frame, text="Description:", style="Subheading.TLabel").grid(row=2, column=0, sticky=tk.W, pady=8)
        self.add_desc_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.add_desc_var, width=30).grid(row=2, column=1, sticky=tk.EW, pady=8)

        ttk.Label(form_frame, text="Amount ($):", style="Subheading.TLabel").grid(row=3, column=0, sticky=tk.W, pady=8)
        self.add_amount_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.add_amount_var, width=30).grid(row=3, column=1, sticky=tk.EW, pady=8)

        ttk.Label(form_frame, text="Recurring Monthly:", style="Subheading.TLabel").grid(row=4, column=0, sticky=tk.W, pady=8)
        self.add_recurring_var = tk.BooleanVar()
        ttk.Checkbutton(form_frame, variable=self.add_recurring_var).grid(row=4, column=1, sticky=tk.W, pady=8)

        action_frame = ttk.Frame(form_frame)
        action_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(16, 0))
        ttk.Button(action_frame, text="Add Expense", style="Accent.TButton", command=self.add_expense).pack(side=tk.LEFT)

        help_frame = ttk.Frame(content_frame, style="Card.TFrame", padding=16)
        help_frame.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Label(help_frame, text="Helpful tips", style="Subheading.TLabel").pack(anchor=tk.W)
        ttk.Label(help_frame, text="• Use short and clear descriptions.", style="Hint.TLabel", wraplength=240).pack(anchor=tk.W, pady=(8, 4))
        ttk.Label(help_frame, text="• Group purchases by category for better insight.", style="Hint.TLabel", wraplength=240).pack(anchor=tk.W, pady=4)
        ttk.Label(help_frame, text="• Add recurring costs once to keep your tracking easy.", style="Hint.TLabel", wraplength=240).pack(anchor=tk.W, pady=4)

    def setup_view_tab(self) -> None:
        frame = ttk.Frame(self.view_tab, padding=16, style="Section.TFrame")
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=8)

        header_frame = ttk.Frame(frame, style="Card.TFrame", padding=12)
        header_frame.pack(fill=tk.X, pady=(0, 12))
        self.view_summary_label = ttk.Label(header_frame, text="Showing all expenses", style="Subheading.TLabel")
        self.view_summary_label.pack(anchor=tk.W)

        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(search_frame, text="🔍 Search:", style="Subheading.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        search_entry.bind("<KeyRelease>", lambda e: self.filter_expenses())
        ttk.Label(search_frame, text="Quick filter by category or description", style="Hint.TLabel").pack(side=tk.LEFT)

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Button(button_frame, text="Refresh", style="Accent.TButton", command=self.refresh_view).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Remove Selected", style="Accent.TButton", command=self.remove_expense).pack(side=tk.LEFT, padx=5)

        self.tree = ttk.Treeview(
            frame,
            columns=("Date", "Category", "Amount", "Recurring", "Description"),
            height=20,
            show="tree headings",
        )
        self.tree.column("#0", width=0, stretch=tk.NO)
        self.tree.column("Date", anchor=tk.W, width=110)
        self.tree.column("Category", anchor=tk.W, width=130)
        self.tree.column("Amount", anchor=tk.E, width=90)
        self.tree.column("Recurring", anchor=tk.CENTER, width=90)
        self.tree.column("Description", anchor=tk.W, width=360)

        self.tree.heading("Date", text="Date")
        self.tree.heading("Category", text="Category")
        self.tree.heading("Amount", text="Amount")
        self.tree.heading("Recurring", text="Recurring")
        self.tree.heading("Description", text="Description")

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("oddrow", background="#f8fafc")
        self.tree.tag_configure("evenrow", background="#ffffff")
    # Setup the "Budget" tab with current budget display and update functionality
    def setup_budget_tab(self) -> None:
        frame = ttk.Frame(self.budget_tab, padding=18, style="Section.TFrame")
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=8)

        heading_frame = ttk.Frame(frame)
        heading_frame.pack(fill=tk.X, pady=(0, 18))
        ttk.Label(heading_frame, text="Monthly Budget", style="Heading.TLabel").pack(anchor=tk.W)
        ttk.Label(
            heading_frame,
            text="Keep your dorm spending in check with a clear budget target.",
            font=("Arial", 10),
            foreground="#555555",
        ).pack(anchor=tk.W, pady=(4, 0))

        current_frame = ttk.Frame(frame, style="Card.TFrame", padding=14)
        current_frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(current_frame, text="Current Budget:", font=("Arial", 11, "bold")).pack(anchor=tk.W)
        self.budget_display_var = tk.StringVar(value=format_money(self.tracker.budget))
        self.budget_display = ttk.Label(current_frame, textvariable=self.budget_display_var, font=("Arial", 22, "bold"))
        self.budget_display.pack(anchor=tk.W, pady=(8, 0))

        entry_frame = ttk.Frame(frame)
        entry_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(entry_frame, text="New Budget Amount ($):", style="Subheading.TLabel").grid(row=0, column=0, sticky=tk.W)
        self.budget_amount_var = tk.StringVar(value=str(self.tracker.budget))
        ttk.Entry(entry_frame, textvariable=self.budget_amount_var, width=24).grid(row=0, column=1, sticky=tk.W, padx=8)
        ttk.Button(entry_frame, text="Update Budget", style="Accent.TButton", command=self.update_budget).grid(row=0, column=2, padx=12)

        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        info_label = ttk.Label(
            info_frame,
            text="Tip: Set a realistic budget for rent, food, utilities and fun. Review this page every month.",
            wraplength=760,
            font=("Arial", 10),
            foreground="#555555",
        )
        info_label.pack(anchor=tk.W)

    def refresh_all(self) -> None:
        self.refresh_summary()
        self.refresh_view()
        self.sync_budget_display()
        self.update_nav_stats()

    def refresh_summary(self) -> None:
        try:
            month_str = self.month_var.get().strip()
            year, month = map(int, month_str.split("-"))
        except ValueError:
            messagebox.showerror("Error", "Use YYYY-MM format")
            play_error_sound()
            return

        expenses = self.tracker.monthly_expenses(year, month)
        total = sum((expense.amount for expense in expenses), Decimal("0.00"))
        category_totals = self.tracker.category_totals(expenses)
        remaining = self.tracker.budget - total
        usage_percent = min(float((total / self.tracker.budget) * Decimal("100.00")) if self.tracker.budget > Decimal("0.00") else 0.0, 100.0)

        self.cards["budget"].config(text=format_money(self.tracker.budget))
        self.cards["spent"].config(text=format_money(total))
        self.cards["remaining"].config(text=format_money(max(remaining, Decimal("0.00"))))
        self.progress_var.set(usage_percent)

        highest = self.tracker.get_highest_expense(expenses)
        self.stats_cards["highest_expense"].config(text=format_money(highest.amount) if highest else "—")

        days_in_month = (date(year, month + 1, 1) - date(year, month, 1)).days if month < 12 else (date(year + 1, 1, 1) - date(year, 12, 1)).days
        avg_daily = self.tracker.get_avg_daily_spending(expenses, days_in_month)
        self.stats_cards["daily_average"].config(text=format_money(avg_daily))

        most_spent = self.tracker.get_most_spent_category(expenses)
        category_text = f"{most_spent[0]}" if most_spent else "—"
        self.stats_cards["top_category"].config(text=category_text)

        self.breakdown_text.config(state=tk.NORMAL)
        self.breakdown_text.delete(1.0, tk.END)
        if not any(amount > Decimal("0.00") for amount in category_totals.values()):
            self.breakdown_text.insert(tk.END, "No expenses recorded yet for this month.")
        else:
            for category, amount in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
                if amount > Decimal("0.00"):
                    self.breakdown_text.insert(tk.END, f"{category:18} {format_money(amount)}\n")
        self.breakdown_text.config(state=tk.DISABLED)

        self.recent_text.config(state=tk.NORMAL)
        self.recent_text.delete(1.0, tk.END)
        if not expenses:
            self.recent_text.insert(tk.END, "No recent expenses for this month.")
        else:
            for expense in sorted(expenses, key=lambda item: item.date, reverse=True)[:10]:
                self.recent_text.insert(
                    tk.END,
                    f"{expense.date.isoformat()}  •  {expense.category}  •  {format_money(expense.amount)}\n{expense.description}\n\n",
                )
        self.recent_text.config(state=tk.DISABLED)

        usage_ratio = total / self.tracker.budget if self.tracker.budget > Decimal("0.00") else Decimal("0.00")
        if usage_ratio >= Decimal("1.00"):
            status_text = "Budget status: Over budget"
            status_color = "#dc2626"
            insight_text = "Spending is above your monthly target. Trim a few non-essential purchases."
        elif usage_ratio >= Decimal("0.80"):
            status_text = "Budget status: Near your limit"
            status_color = "#d97706"
            insight_text = "You are close to your limit. Keep the next expenses small and planned."
        else:
            status_text = "Budget status: On track"
            status_color = "#16a34a"
            insight_text = "You are staying within budget. Keep up the good pace."

        self.status_label.config(text=status_text, foreground=status_color)
        self.insight_label.config(text=insight_text)

        prev_month_total = self.tracker.get_previous_month_total(year, month)
        self.comparison_text.config(state=tk.NORMAL)
        self.comparison_text.delete(1.0, tk.END)
        if prev_month_total == Decimal("0.00"):
            self.comparison_text.insert(tk.END, "No data from previous month to compare.")
        else:
            diff = total - prev_month_total
            change_pct = ((diff / prev_month_total) * Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if prev_month_total > Decimal("0.00") else Decimal("0.00")
            trend = "📈 UP" if diff > Decimal("0.00") else "📉 DOWN" if diff < Decimal("0.00") else "➡️ SAME"
            tag = "increase" if diff > Decimal("0.00") else "decrease" if diff < Decimal("0.00") else "amount"
            self.comparison_text.insert(tk.END, f"This Month: {format_money(total)}  •  Last Month: {format_money(prev_month_total)}  •  {trend}  {format_money(abs(diff))} ({abs(change_pct)}%)", tag)
        self.comparison_text.config(state=tk.DISABLED)
    # Synchronize the budget display in the UI with the current budget value
    def sync_budget_display(self) -> None:
        self.budget_display_var.set(format_money(self.tracker.budget))
        self.budget_amount_var.set(str(self.tracker.budget))
    # Refresh the expense view in the "View Expenses" tab, clearing and repopulating the treeview with current expenses
    def refresh_view(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        expenses = sorted(self.tracker.expenses, key=lambda x: x.date, reverse=True)
        for index, expense in enumerate(expenses):
            self.tree.insert(
                "",
                tk.END,
                iid=expense.id,
                tags=("evenrow",) if index % 2 == 0 else ("oddrow",),
                values=(
                    expense.date.isoformat(),
                    expense.category,
                    format_money(expense.amount),
                    "Yes" if expense.recurring else "No",
                    expense.description,
                ),
            )

        self.view_summary_label.config(text=f"Showing {len(expenses)} expense(s)")
    # Filter expenses in the treeview based on the search term entered by the user, matching against category and description
    def filter_expenses(self) -> None:
        search_term = self.search_var.get().lower().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)

        filtered_expenses = [
            e for e in sorted(self.tracker.expenses, key=lambda x: x.date, reverse=True)
            if search_term in e.category.lower() or search_term in e.description.lower()
        ] if search_term else sorted(self.tracker.expenses, key=lambda x: x.date, reverse=True)

        for index, expense in enumerate(filtered_expenses):
            self.tree.insert(
                "",
                tk.END,
                iid=expense.id,
                tags=("evenrow",) if index % 2 == 0 else ("oddrow",),
                values=(
                    expense.date.isoformat(),
                    expense.category,
                    format_money(expense.amount),
                    "Yes" if expense.recurring else "No",
                    expense.description,
                ),
            )

        if search_term:
            self.view_summary_label.config(text=f"Showing {len(filtered_expenses)} matching expense(s)")
        else:
            self.view_summary_label.config(text=f"Showing {len(self.tracker.expenses)} expense(s)")
    # Add a new expense to the tracker based on user input from the "Add Expense" tab, validating and parsing the input fields
    def add_expense(self) -> None:
        try:
            expense_date = parse_date(self.add_date_var.get())
            category = self.add_category_var.get()
            description = self.add_desc_var.get().strip() or "No description"
            amount = parse_money(self.add_amount_var.get())
            recurring = self.add_recurring_var.get()

            expense_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[-12:]
            self.tracker.add_expense(
                Expense(
                    id=expense_id,
                    date=expense_date,
                    category=category,
                    description=description,
                    amount=amount,
                    recurring=recurring,
                )
            )
            # Show success message and play sound 
            messagebox.showinfo("Success", "Expense added!")
            play_success_sound()
            self.add_date_var.set(str(date.today()))
            self.add_desc_var.set("")
            self.add_amount_var.set("")
            self.add_recurring_var.set(False)
            self.refresh_all()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            play_error_sound()
    # Remove the selected expense from the tracker, confirming selection and updating the view accordingly
    def remove_expense(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select an expense to remove.")
            play_info_sound()
            return

        expense_id = selected[0]
        if self.tracker.remove_expense(expense_id):
            messagebox.showinfo("Success", "Expense removed!")
            play_success_sound()
            self.refresh_all()
        else:
            messagebox.showerror("Error", "Could not remove expense.")
            play_error_sound()
    # Update the budget amount in the tracker based on user input from the "Budget" tab, validating and parsing the input field
    def update_budget(self) -> None:
        try:
            amount = parse_money(self.budget_amount_var.get())
            self.tracker.set_budget(amount)
            self.sync_budget_display()
            messagebox.showinfo("Success", f"Budget updated to {format_money(amount)}")
            play_success_sound()
            self.refresh_all()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            play_error_sound()
    # Switch to the "Add Expense" tab in the notebook for quick access to adding a new expense
    def switch_to_add_tab(self) -> None:
        self.notebook.select(1)
    # Update the quick stats displayed in the navigation bar, reflecting the current budget and total spent for the current month
    def update_nav_stats(self) -> None:
        """Update the quick stats in the navigation bar."""
        try:
            year = date.today().year
            month = date.today().month
            expenses = self.tracker.monthly_expenses(year, month)
            total = sum((expense.amount for expense in expenses), Decimal("0.00"))
            self.nav_budget_label.config(text=f"Budget: {format_money(self.tracker.budget)}")
            self.nav_spent_label.config(text=f"Spent: {format_money(total)}")
        except Exception:
            pass

# Main function to initialize the Tkinter application and start the main event loop
def main() -> None:
    root = tk.Tk()
    tracker = ExpenseTracker(DATA_FILE)
    app = ExpenseTrackerApp(root, tracker)
    root.mainloop()

# Entry point of the application, calling the main function to start the expense tracker GUI
if __name__== "__main__":
    main()

# Project made by DIV(dkcoder456)
# Youtube channel: https://www.youtube.com/@DIVsCodingVerse
# Github: https://github.com/dkcoder456
# No Social Media Accounts, No Discord Server, No Telegram Group, No Reddit Community, No Facebook Page, No Instagram Account, No Twitter Account, No LinkedIn Profile, No TikTok Account, No Snapchat Account, No Pinterest Account, No Quora Profile, No Medium Profile, No Stack Overflow Profile, No Dev.to Profile, No Hashnode Profile, No CodePen Profile, No JSFiddle Profile, No Glitch Profile, No Heroku Account, No Netlify Account, No Vercel Account.
