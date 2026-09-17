import time
import calendar
import tkinter as tk

from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox

import numpy as np
import pandas as pd

# =========================================================
# LOAD DATA
# =========================================================

PROJECT_FOLDER = Path(__file__).resolve().parent
DATA_FOLDER = PROJECT_FOLDER / "Data"
VALID_FILE = DATA_FOLDER / "valid_transactions.csv"


def load_transactions():
    """Load the cleaned transaction dataset."""

    if not VALID_FILE.exists():
        raise FileNotFoundError(
            f"Could not find the data file:\n{VALID_FILE}"
        )

    data = pd.read_csv(
        VALID_FILE,
        dtype={
            "transaction_id": "string",
            "card_last4": "string"
        },
        parse_dates=["transaction_date"]
    )

    return data


# =========================================================
# MATCHING ENGINE
# =========================================================

def search_transactions(
    data,
    card_last4=None,
    amount_rm=None,
    transaction_date=None,
    folio_no=None,
    room_no=None,
    maximum_results=10,
    minimum_score=40
):
    """Search and rank possible transaction matches."""

    search_inputs = [
        card_last4,
        amount_rm,
        transaction_date,
        folio_no,
        room_no
    ]

    if all(value in [None, ""] for value in search_inputs):
        raise ValueError(
            "Enter at least one search criterion."
        )

    results = data.copy()
    results["match_score"] = 0
    results["match_reasons"] = ""

    # Card digits: 40 points
    if card_last4 not in [None, ""]:
        card_value = str(card_last4).strip()

        if not card_value.isdigit() or len(card_value) != 4:
            raise ValueError(
                "Card information must contain exactly four digits."
            )

        card_match = (
            results["card_last4"].astype("string")
            == card_value
        )

        results.loc[
            card_match,
            "match_score"
        ] += 40

        results.loc[
            card_match,
            "match_reasons"
        ] += "Card matched; "

    # Amount: 30 points
    if amount_rm not in [None, ""]:
        try:
            amount_value = float(amount_rm)
        except ValueError:
            raise ValueError(
                "Transaction amount must be a valid number."
            )

        if amount_value <= 0:
            raise ValueError(
                "Transaction amount must be greater than zero."
            )

        amount_match = np.isclose(
            results["amount_rm"],
            amount_value,
            atol=0.01
        )

        results.loc[
            amount_match,
            "match_score"
        ] += 30

        results.loc[
            amount_match,
            "match_reasons"
        ] += "Amount matched; "

    # Date: 20 points
    if transaction_date not in [None, ""]:
        date_value = pd.to_datetime(
            transaction_date,
            errors="coerce"
        )

        if pd.isna(date_value):
            raise ValueError(
                "Select a valid transaction date."
            )

        date_match = (
            results["transaction_date"].dt.normalize()
            == date_value.normalize()
        )

        results.loc[
            date_match,
            "match_score"
        ] += 20

        results.loc[
            date_match,
            "match_reasons"
        ] += "Date matched; "

    # Folio number: 5 points
    if folio_no not in [None, ""]:
        try:
            folio_value = int(folio_no)
        except ValueError:
            raise ValueError(
                "Folio number must contain digits only."
            )

        folio_match = (
            results["folio_no"] == folio_value
        )

        results.loc[
            folio_match,
            "match_score"
        ] += 5

        results.loc[
            folio_match,
            "match_reasons"
        ] += "Folio matched; "

    # Room number: 5 points
    if room_no not in [None, ""]:
        try:
            room_value = int(room_no)
        except ValueError:
            raise ValueError(
                "Room number must contain digits only."
            )

        room_match = (
            results["room_no"] == room_value
        )

        results.loc[
            room_match,
            "match_score"
        ] += 5

        results.loc[
            room_match,
            "match_reasons"
        ] += "Room matched; "

    # Remove weak candidates
    results = results[
        results["match_score"] >= minimum_score
    ].copy()

    results["confidence_level"] = pd.cut(
        results["match_score"],
        bins=[0, 49, 79, 100],
        labels=[
            "Low Confidence",
            "Possible Match",
            "High Confidence"
        ],
        include_lowest=True
    )

    results = results.sort_values(
        by=["match_score", "transaction_date"],
        ascending=[False, False]
    ).head(maximum_results)

    return results[
        [
            "transaction_id",
            "guest_name",
            "room_no",
            "folio_no",
            "transaction_date",
            "amount_rm",
            "card_last4",
            "payment_method",
            "match_score",
            "confidence_level",
            "match_reasons"
        ]
    ]


# =========================================================
# CALENDAR
# =========================================================

def open_calendar(parent, date_variable):
    """Open a calendar for choosing a transaction date."""

    calendar_window = tk.Toplevel(parent)
    calendar_window.title("Choose Transaction Date")
    calendar_window.resizable(False, False)
    calendar_window.transient(parent)
    calendar_window.grab_set()

    try:
        starting_date = datetime.strptime(
            date_variable.get(),
            "%Y-%m-%d"
        )
    except ValueError:
        starting_date = datetime(2025, 3, 14)

    displayed_year = starting_date.year
    displayed_month = starting_date.month

    calendar_frame = tk.Frame(
        calendar_window,
        padx=12,
        pady=12
    )
    calendar_frame.pack()

    def select_date(day):
        date_variable.set(
            f"{displayed_year}-"
            f"{displayed_month:02d}-"
            f"{day:02d}"
        )
        calendar_window.destroy()

    def change_month(change):
        nonlocal displayed_year, displayed_month

        displayed_month += change

        if displayed_month == 13:
            displayed_month = 1
            displayed_year += 1

        elif displayed_month == 0:
            displayed_month = 12
            displayed_year -= 1

        draw_calendar()

    def draw_calendar():
        for widget in calendar_frame.winfo_children():
            widget.destroy()

        tk.Button(
            calendar_frame,
            text="<",
            width=4,
            command=lambda: change_month(-1)
        ).grid(row=0, column=0)

        tk.Label(
            calendar_frame,
            text=(
                f"{calendar.month_name[displayed_month]} "
                f"{displayed_year}"
            ),
            font=("Arial", 12, "bold"),
            width=22
        ).grid(
            row=0,
            column=1,
            columnspan=5
        )

        tk.Button(
            calendar_frame,
            text=">",
            width=4,
            command=lambda: change_month(1)
        ).grid(row=0, column=6)

        weekdays = [
            "Mon", "Tue", "Wed", "Thu",
            "Fri", "Sat", "Sun"
        ]

        for column_number, weekday in enumerate(weekdays):
            tk.Label(
                calendar_frame,
                text=weekday,
                font=("Arial", 9, "bold"),
                width=5
            ).grid(
                row=1,
                column=column_number,
                pady=5
            )

        month_days = calendar.monthcalendar(
            displayed_year,
            displayed_month
        )

        for row_number, week in enumerate(
            month_days,
            start=2
        ):
            for column_number, day in enumerate(week):

                if day != 0:
                    tk.Button(
                        calendar_frame,
                        text=str(day),
                        width=4,
                        command=lambda selected_day=day:
                            select_date(selected_day)
                    ).grid(
                        row=row_number,
                        column=column_number,
                        padx=2,
                        pady=2
                    )

    draw_calendar()


# =========================================================
# DESKTOP APPLICATION
# =========================================================

def open_search_window(transactions):
    """Open the transaction-search desktop application."""

    window = tk.Tk()
    window.title("Credit Card Transaction Search")
    window.geometry("1200x650")
    window.configure(bg="#F5F7FA")

    tk.Label(
        window,
        text="Credit Card Transaction Search",
        font=("Arial", 18, "bold"),
        bg="#F5F7FA",
        fg="#243B53"
    ).pack(pady=(20, 5))

    tk.Label(
        window,
        text=(
            "Enter the available payment information. "
            "More information produces a stronger match."
        ),
        font=("Arial", 10),
        bg="#F5F7FA",
        fg="#52667A"
    ).pack(pady=(0, 15))

    input_frame = tk.Frame(
        window,
        bg="white",
        padx=20,
        pady=15
    )
    input_frame.pack(
        fill="x",
        padx=25,
        pady=5
    )

    field_names = [
        "Card Last 4 Digits",
        "Amount (RM)",
        "Transaction Date",
        "Folio Number",
        "Room Number"
    ]

    for column_number, field_name in enumerate(field_names):
        tk.Label(
            input_frame,
            text=field_name,
            bg="white",
            font=("Arial", 9, "bold")
        ).grid(
            row=0,
            column=column_number,
            padx=8,
            pady=5
        )

    card_entry = tk.Entry(input_frame, width=18)
    amount_entry = tk.Entry(input_frame, width=18)
    folio_entry = tk.Entry(input_frame, width=18)
    room_entry = tk.Entry(input_frame, width=18)

    date_variable = tk.StringVar(value="")

    date_frame = tk.Frame(
        input_frame,
        bg="white"
    )

    date_entry = tk.Entry(
        date_frame,
        width=12,
        textvariable=date_variable,
        state="readonly"
    )
    date_entry.pack(side="left")

    tk.Button(
        date_frame,
        text="Calendar",
        command=lambda: open_calendar(
            window,
            date_variable
        )
    ).pack(
        side="left",
        padx=(4, 0)
    )

    card_entry.grid(row=1, column=0, padx=8, pady=5)
    amount_entry.grid(row=1, column=1, padx=8, pady=5)
    date_frame.grid(row=1, column=2, padx=8, pady=5)
    folio_entry.grid(row=1, column=3, padx=8, pady=5)
    room_entry.grid(row=1, column=4, padx=8, pady=5)

    result_frame = tk.Frame(
        window,
        bg="#F5F7FA"
    )
    result_frame.pack(
        fill="both",
        expand=True,
        padx=25,
        pady=15
    )

    columns = [
        "transaction_id",
        "guest_name",
        "room_no",
        "folio_no",
        "transaction_date",
        "amount_rm",
        "card_last4",
        "match_score",
        "confidence_level",
        "match_reasons"
    ]

    headings = {
        "transaction_id": "Transaction ID",
        "guest_name": "Guest",
        "room_no": "Room",
        "folio_no": "Folio",
        "transaction_date": "Date",
        "amount_rm": "Amount (RM)",
        "card_last4": "Card Last 4",
        "match_score": "Score",
        "confidence_level": "Confidence",
        "match_reasons": "Matching Reasons"
    }

    widths = {
        "transaction_id": 110,
        "guest_name": 110,
        "room_no": 70,
        "folio_no": 80,
        "transaction_date": 100,
        "amount_rm": 100,
        "card_last4": 90,
        "match_score": 65,
        "confidence_level": 120,
        "match_reasons": 300
    }

    result_table = ttk.Treeview(
        result_frame,
        columns=columns,
        show="headings"
    )

    for column in columns:
        result_table.heading(
            column,
            text=headings[column]
        )
        result_table.column(
            column,
            width=widths[column],
            anchor="center"
        )

    vertical_scrollbar = ttk.Scrollbar(
        result_frame,
        orient="vertical",
        command=result_table.yview
    )

    horizontal_scrollbar = ttk.Scrollbar(
        result_frame,
        orient="horizontal",
        command=result_table.xview
    )

    result_table.configure(
        yscrollcommand=vertical_scrollbar.set,
        xscrollcommand=horizontal_scrollbar.set
    )

    result_table.grid(row=0, column=0, sticky="nsew")
    vertical_scrollbar.grid(row=0, column=1, sticky="ns")
    horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

    result_frame.rowconfigure(0, weight=1)
    result_frame.columnconfigure(0, weight=1)

    status_label = tk.Label(
        window,
        text="Enter search information to begin.",
        font=("Arial", 10),
        bg="#F5F7FA",
        fg="#52667A"
    )
    status_label.pack(pady=(0, 15))

    def perform_search():
        for item in result_table.get_children():
            result_table.delete(item)

        try:
            start_time = time.perf_counter()

            results = search_transactions(
                data=transactions,
                card_last4=card_entry.get().strip() or None,
                amount_rm=amount_entry.get().strip() or None,
                transaction_date=date_variable.get().strip() or None,
                folio_no=folio_entry.get().strip() or None,
                room_no=room_entry.get().strip() or None,
                minimum_score=40
            )

            elapsed_time = time.perf_counter() - start_time

            if results.empty:
                status_label.config(
                    text=(
                        "No sufficiently strong match was found. "
                        f"Search time: {elapsed_time:.6f} seconds."
                    ),
                    fg="#C0392B"
                )
                return

            for _, row in results.iterrows():
                displayed_date = pd.to_datetime(
                    row["transaction_date"]
                ).strftime("%Y-%m-%d")

                result_table.insert(
                    "",
                    "end",
                    values=(
                        row["transaction_id"],
                        row["guest_name"],
                        row["room_no"],
                        row["folio_no"],
                        displayed_date,
                        f"{row['amount_rm']:.2f}",
                        row["card_last4"],
                        row["match_score"],
                        str(row["confidence_level"]),
                        row["match_reasons"]
                    )
                )

            status_label.config(
                text=(
                    f"{len(results)} possible match(es) found in "
                    f"{elapsed_time:.6f} seconds."
                ),
                fg="#1B7F5A"
            )

        except ValueError as error:
            messagebox.showerror(
                "Invalid Search",
                str(error)
            )

        except Exception as error:
            messagebox.showerror(
                "Unexpected Error",
                str(error)
            )
    def show_all_for_date():
        """Display every transaction recorded on the selected date."""

        for item in result_table.get_children():
            result_table.delete(item)

        selected_date = pd.to_datetime(
            date_variable.get(),
            errors="coerce"
        )

        if pd.isna(selected_date):
            messagebox.showerror(
                "Date Required",
                "Please choose a transaction date first."
            )
            return

        start_time = time.perf_counter()

        daily_results = transactions[
            transactions["transaction_date"].dt.normalize()
            == selected_date.normalize()
        ].copy()

        daily_results = daily_results.sort_values(
            by=["amount_rm", "transaction_id"],
            ascending=[False, True]
        )

        elapsed_time = time.perf_counter() - start_time

        if daily_results.empty:
            status_label.config(
                text=(
                    "No transactions were recorded on "
                    f"{selected_date.strftime('%Y-%m-%d')}."
                ),
                fg="#C0392B"
            )
            return

        for _, row in daily_results.iterrows():
            displayed_date = pd.to_datetime(
                row["transaction_date"]
            ).strftime("%Y-%m-%d")

            result_table.insert(
                "",
                "end",
                values=(
                    row["transaction_id"],
                    row["guest_name"],
                    row["room_no"],
                    row["folio_no"],
                    displayed_date,
                    f"{row['amount_rm']:.2f}",
                    row["card_last4"],
                    "-",
                    "Daily List",
                    "Selected date"
                )
            )

        daily_total = daily_results["amount_rm"].sum()

        status_label.config(
            text=(
                f"{len(daily_results)} transaction(s) found on "
                f"{selected_date.strftime('%Y-%m-%d')} | "
                f"Total value: RM {daily_total:,.2f} | "
                f"Completed in {elapsed_time:.6f} seconds."
            ),
            fg="#1B7F5A"
        )

    def clear_search():
        card_entry.delete(0, tk.END)
        amount_entry.delete(0, tk.END)
        folio_entry.delete(0, tk.END)
        room_entry.delete(0, tk.END)
        date_variable.set("")

        for item in result_table.get_children():
            result_table.delete(item)

        status_label.config(
            text="Enter search information to begin.",
            fg="#52667A"
        )

        card_entry.focus()

    button_frame = tk.Frame(
        input_frame,
        bg="white"
    )

    button_frame.grid(
        row=2,
        column=0,
        columnspan=5,
        pady=(15, 0)
    )

    tk.Button(
        button_frame,
        text="Search Transactions",
        command=perform_search,
        bg="#2A9D8F",
        fg="white",
        font=("Arial", 10, "bold"),
        padx=18,
        pady=7
    ).pack(side="left", padx=5)

    tk.Button(
        button_frame,
        text="Show All for Date",
        command=show_all_for_date,
        bg="#3B82C4",
        fg="white",
        font=("Arial", 10, "bold"),
        padx=18,
        pady=7
    ).pack(side="left", padx=5)

    tk.Button(
        button_frame,
        text="Clear",
        command=clear_search,
        bg="#DCE3EA",
        fg="#243B53",
        font=("Arial", 10),
        padx=18,
        pady=7
    ).pack(side="left", padx=5)

    card_entry.focus()
    window.mainloop()

# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":
    try:
        transaction_data = load_transactions()
        open_search_window(transaction_data)

    except Exception as error:
        messagebox.showerror(
            "Application Error",
            str(error)
        )
