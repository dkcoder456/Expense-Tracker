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
DEFAULT_BUDGET = Decimal("1900.00")

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


def format_money(amount: Decimal) -> str:
    return f"${amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def parse_money(value: str) -> Decimal:
    try:
        return Decimal(value.strip().replace("$", "")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError("Enter a valid number like 12.50")


def parse_date(value: str) -> date:
    if not value.strip():
        return date.today()
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Enter a date in YYYY-MM-DD format") from exc


def _play_windows_sound(sound_name: str) -> None:
    if sys.platform != "win32":
        return
    try:
        import winsound
        winsound.PlaySound(sound_name, winsound.SND_ALIAS | winsound.SND_ASYNC)
    except Exception:
        pass


def play_success_sound() -> None:
    _play_windows_sound("SystemAsterisk")


def play_error_sound() -> None:
    _play_windows_sound("SystemHand")


def play_info_sound() -> None:
    _play_windows_sound("SystemQuestion")


@dataclass
class Expense:
    id: str
    date: date
    category: str
    description: str
    amount: Decimal
    recurring: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "category": self.category,
            "description": self.description,
            "amount": str(self.amount),
            "recurring": self.recurring,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "Expense":
        return cls(
            id=str(data["id"]),
            date=parse_date(str(data["date"])),
            category=str(data["category"]),
            description=str(data["description"]),
            amount=parse_money(str(data["amount"])),
            recurring=bool(data.get("recurring", False)),
        )


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

        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            saved_budget = parse_money(str(payload.get("budget", DEFAULT_BUDGET)))
            saved_default = payload.get("default_budget")
            self.expenses = [Expense.from_dict(item) for item in payload.get("expenses", [])]

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
        except (json.JSONDecodeError, ValueError):
            print("Warning: Could not read expense file. Starting fresh.")
            self.expenses = []
            self.budget = DEFAULT_BUDGET

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

    def add_expense(self, expense: Expense) -> None:
        self.expenses.append(expense)
        self.save()

    def remove_expense(self, expense_id: str) -> bool:
        original_length = len(self.expenses)
        self.expenses = [expense for expense in self.expenses if expense.id != expense_id]
        if len(self.expenses) < original_length:
            self.save()
            return True
        return False

    def monthly_expenses(self, year: int, month: int) -> List[Expense]:
        return [expense for expense in self.expenses if expense.date.year == year and expense.date.month == month]

    def category_totals(self, expenses: List[Expense]) -> Dict[str, Decimal]:
        totals: Dict[str, Decimal] = {category: Decimal("0.00") for category in CATEGORIES}
        totals["Other"] = totals.get("Other", Decimal("0.00"))
        for expense in expenses:
            totals[expense.category] = totals.get(expense.category, Decimal("0.00")) + expense.amount
        return totals

    def set_budget(self, amount: Decimal) -> None:
        self.budget = amount
        self.save()


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


class ExpenseTrackerApp:
    def __init__(self, root: tk.Tk, tracker: ExpenseTracker):
        self.root = root
        self.tracker = tracker
        self.root.title("Dorm Monthly Expense Tracker")
        self.root.geometry("980x660")
        self.root.minsize(900, 620)
        self.root.resizable(True, True)
        self.root.configure(background="#eef3f7")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#eef3f7")
        style.configure("Card.TFrame", background="#ffffff", relief="flat", borderwidth=1)
        style.configure("Section.TFrame", background="#f8fbff", relief="flat", borderwidth=1)
        style.configure("CardHeader.TFrame", background="#4a90e2")
        style.configure("CardHeader.TLabel", font=("Arial", 16, "bold"), background="#4a90e2", foreground="#ffffff")
        style.configure("TLabel", background="#eef3f7", font=("Arial", 11), foreground="#1f2937")
        style.configure("Heading.TLabel", font=("Arial", 18, "bold"), background="#eef3f7", foreground="#111827")
        style.configure("Subheading.TLabel", font=("Arial", 12, "bold"), background="#eef3f7", foreground="#1f2937")
        style.configure("Accent.TButton", background="#3b82f6", foreground="#ffffff", font=("Arial", 10, "bold"), padding=8, borderwidth=0)
        style.map(
            "Accent.TButton",
            background=[("active", "#2563eb"), ("pressed", "#1d4ed8")],
            foreground=[("disabled", "#a0a0a0")],
        )
        style.configure("TButton", padding=8)
        style.configure("TEntry", fieldbackground="#f8fbff", background="#f8fbff", foreground="#1f2937")
        style.configure("TCombobox", fieldbackground="#f8fbff", background="#f8fbff", foreground="#1f2937")
        style.configure("Accent.TLabel", font=("Arial", 12, "bold"), background="#eef3f7", foreground="#1f2937")
        style.configure("Value.TLabel", font=("Arial", 16, "bold"), background="#ffffff", foreground="#111827")
        style.configure("Info.TLabel", font=("Arial", 10), background="#eef3f7", foreground="#475569")
        style.configure("Treeview", font=("Arial", 10), rowheight=26, background="#ffffff", fieldbackground="#ffffff", foreground="#111827")
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#e2e8f0", foreground="#111827")
        style.map("Treeview", background=[("selected", "#93c5fd")], foreground=[("selected", "#111827")])
        style.configure("TNotebook", background="#eef3f7")
        style.configure("TNotebook.Tab", padding=[12, 10], font=("Arial", 10, "bold"))
        style.configure("TLabelframe", background="#eef3f7")
        style.configure("TLabelframe.Label", font=("Arial", 12, "bold"), background="#eef3f7")
        style.configure("TSeparator", background="#cbd5e1")

        self.setup_ui()
        self.refresh_all()

    def setup_ui(self) -> None:
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        header_frame = ttk.Frame(main_frame, padding=16, style="CardHeader.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header_frame, text="Dorm Monthly Expense Tracker", style="CardHeader.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header_frame,
            text="A clean student budget dashboard for rent, food, utilities and weekly spending.",
            font=("Arial", 10),
            background="#4a90e2",
            foreground="#eef2ff",
            wraplength=860,
        ).pack(anchor=tk.W, pady=(6, 0))
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(10, 10))

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.summary_tab = ttk.Frame(notebook)
        self.add_tab = ttk.Frame(notebook)
        self.view_tab = ttk.Frame(notebook)
        self.budget_tab = ttk.Frame(notebook)

        notebook.add(self.summary_tab, text="Summary")
        notebook.add(self.add_tab, text="Add Expense")
        notebook.add(self.view_tab, text="View Expenses")
        notebook.add(self.budget_tab, text="Budget")

        self.setup_summary_tab()
        self.setup_add_tab()
        self.setup_view_tab()
        self.setup_budget_tab()

    def setup_summary_tab(self) -> None:
        frame = ttk.Frame(self.summary_tab, padding=14, style="Card.TFrame")
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=8)

        top_frame = ttk.Frame(frame)
        top_frame.pack(fill=tk.X, pady=(0, 12))

        month_frame = ttk.Frame(top_frame)
        month_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(month_frame, text="Select Month:", style="Subheading.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        self.month_var = tk.StringVar(value=f"{date.today().year}-{date.today().month:02d}")
        ttk.Entry(month_frame, textvariable=self.month_var, width=12).pack(side=tk.LEFT)
        ttk.Button(month_frame, text="Refresh", style="Accent.TButton", command=self.refresh_summary).pack(side=tk.LEFT, padx=10)

        self.progress_var = tk.DoubleVar(value=0.0)
        progress_frame = ttk.Frame(top_frame)
        progress_frame.pack(side=tk.RIGHT, anchor=tk.E)
        ttk.Label(progress_frame, text="Budget usage:", style="Subheading.TLabel").pack(anchor=tk.E)
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=220, variable=self.progress_var, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(6, 0))

        card_frame = ttk.Frame(frame)
        card_frame.pack(fill=tk.X, pady=(0, 12))

        self.cards = {}
        for index, label in enumerate(["Budget", "Spent", "Remaining"]):
            card = ttk.Frame(card_frame, style="Card.TFrame", padding=12)
            card.grid(row=0, column=index, sticky=tk.NSEW, padx=6)
            card_frame.columnconfigure(index, weight=1)
            ttk.Label(card, text=label, style="Subheading.TLabel").pack(anchor=tk.W)
            value_label = ttk.Label(card, text="$0.00", font=("Arial", 16, "bold"))
            value_label.pack(anchor=tk.W, pady=(8, 0))
            self.cards[label.lower()] = value_label

        content_frame = ttk.Frame(frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        breakdown_frame = ttk.LabelFrame(content_frame, text="Category Breakdown", padding=10)
        breakdown_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6), pady=6)
        self.breakdown_text = tk.Text(breakdown_frame, width=35, height=18, state=tk.DISABLED, bg="#f8fafd", bd=0, relief=tk.FLAT, highlightthickness=0, padx=10, pady=10)
        self.breakdown_text.pack(fill=tk.BOTH, expand=True)

        recent_frame = ttk.LabelFrame(content_frame, text="Recent Expenses", padding=10)
        recent_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0), pady=6)
        self.recent_text = tk.Text(recent_frame, width=45, height=18, state=tk.DISABLED, bg="#f8fafd", bd=0, relief=tk.FLAT, highlightthickness=0, padx=10, pady=10)
        self.recent_text.tag_configure("heading", font=("Arial", 10, "bold"), foreground="#0f172a")
        self.recent_text.tag_configure("amount", foreground="#2563eb")
        self.recent_text.pack(fill=tk.BOTH, expand=True)

    def setup_add_tab(self) -> None:
        frame = ttk.Frame(self.add_tab, padding=18, style="Card.TFrame")
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=8)

        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
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

        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, pady=(20, 0))
        ttk.Button(action_frame, text="Add Expense", style="Accent.TButton", command=self.add_expense).pack(side=tk.LEFT)
        ttk.Label(action_frame, text="Tip: Use clear descriptions like 'Groceries' or 'Laundry'.", font=("Arial", 10), foreground="#475569").pack(side=tk.LEFT, padx=12)

    def setup_view_tab(self) -> None:
        frame = ttk.Frame(self.view_tab, padding=12, style="Card.TFrame")
        frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=8)

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

    def setup_budget_tab(self) -> None:
        frame = ttk.Frame(self.budget_tab, padding=18, style="Card.TFrame")
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

    def sync_budget_display(self) -> None:
        self.budget_display_var.set(format_money(self.tracker.budget))
        self.budget_amount_var.set(str(self.tracker.budget))

    def refresh_view(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for index, expense in enumerate(sorted(self.tracker.expenses, key=lambda x: x.date, reverse=True)):
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


def main() -> None:
    root = tk.Tk()
    tracker = ExpenseTracker(DATA_FILE)
    app = ExpenseTrackerApp(root, tracker)
    root.mainloop()



if __name__== "__main__":
    main()
