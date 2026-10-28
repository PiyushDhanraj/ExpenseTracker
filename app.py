import csv
import io
import os
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# -----------------------------
# Page setup and file locations
# -----------------------------
st.set_page_config(
    page_title="Personal Expense Tracker",
    page_icon="💰",
    layout="wide",
)

DATA_DIR = Path(".")
EXPENSES_FILE = DATA_DIR / "expenses.csv"
BUDGET_FILE = DATA_DIR / "budget.csv"
SAVINGS_FILE = DATA_DIR / "savings.csv"

MONTHS = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December",
]
CATEGORIES = ["Food", "Travel", "Shopping", "College", "Other"]
PAYMENT_METHODS = [
    "Cash", "UPI", "Debit Card", "Credit Card",
    "Net Banking", "Wallet", "Other",
]


# -----------------------------
# CSV helpers
# -----------------------------
def load_expenses():
    """Load expenses from CSV, skipping malformed rows safely."""
    expenses = []
    if not EXPENSES_FILE.exists():
        return expenses

    try:
        with EXPENSES_FILE.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    expense_date = date.fromisoformat(row["date"])
                    amount = float(row["amount"])
                    if amount < 0:
                        continue
                    expenses.append(
                        {
                            "date": expense_date,
                            "amount": amount,
                            "description": row.get("description", ""),
                            "category": row.get("category", "Other") or "Other",
                            "payment_method": row.get("payment_method", "Other") or "Other",
                        }
                    )
                except (KeyError, TypeError, ValueError):
                    # Ignore rows that cannot be read instead of crashing the app.
                    continue
    except (OSError, csv.Error):
        st.warning("Could not read expenses.csv. You can continue, but check the file.")
    return expenses


def save_expenses(expenses):
    """Replace the expenses CSV with the current list."""
    with EXPENSES_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["date", "amount", "description", "category", "payment_method"])
        for expense in expenses:
            writer.writerow(
                [
                    expense["date"].isoformat(),
                    expense["amount"],
                    expense["description"],
                    expense["category"],
                    expense.get("payment_method", "Other"),
                ]
            )


def load_budgets():
    budgets = {}
    if not BUDGET_FILE.exists():
        return budgets

    try:
        with BUDGET_FILE.open("r", newline="", encoding="utf-8-sig") as file:
            for row in csv.DictReader(file):
                try:
                    key = f"{int(row['year'])}-{int(row['month'])}"
                    budgets[key] = max(0.0, float(row["budget"]))
                except (KeyError, TypeError, ValueError):
                    continue
    except (OSError, csv.Error):
        st.warning("Could not read budget.csv. Your budget settings may need to be re-entered.")
    return budgets


def save_budgets(budgets):
    with BUDGET_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["year", "month", "budget"])
        for key, amount in sorted(budgets.items()):
            year, month = key.split("-", maxsplit=1)
            writer.writerow([year, month, amount])


def load_savings_goal():
    if not SAVINGS_FILE.exists():
        return 0.0
    try:
        with SAVINGS_FILE.open("r", newline="", encoding="utf-8-sig") as file:
            row = next(csv.DictReader(file), None)
            return max(0.0, float(row["goal"])) if row and row.get("goal") else 0.0
    except (OSError, csv.Error, TypeError, ValueError, KeyError):
        st.warning("Could not read savings.csv. Your savings goal may need to be re-entered.")
        return 0.0


def save_savings_goal(goal):
    with SAVINGS_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["goal"])
        writer.writerow([goal])


def write_csv_download(rows):
    """Create a properly escaped CSV download in memory."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["date", "amount", "description", "category", "payment_method"])
    for expense in rows:
        writer.writerow(
            [
                expense["date"].isoformat(),
                expense["amount"],
                expense["description"],
                expense["category"],
                expense.get("payment_method", "Other"),
            ]
        )
    return buffer.getvalue()


# -----------------------------
# Initialize session state
# -----------------------------
if "expenses" not in st.session_state:
    st.session_state.expenses = load_expenses()

if "budgets" not in st.session_state:
    st.session_state.budgets = load_budgets()

if "savings_goal" not in st.session_state:
    st.session_state.savings_goal = load_savings_goal()

if "editing" not in st.session_state:
    st.session_state.editing = None


def selected_month_number():
    return MONTHS.index(st.session_state.selected_month) + 1


# -----------------------------
# App header and dashboard
# -----------------------------
st.title("💰 Personal Expense Tracker")
st.caption("Track, analyze, and manage your personal spending.")
st.divider()

all_expenses = st.session_state.expenses
today = date.today()

dashboard_total = sum(item["amount"] for item in all_expenses)
dashboard_monthly = sum(
    item["amount"]
    for item in all_expenses
    if item["date"].year == today.year and item["date"].month == today.month
)
dashboard_count = len(all_expenses)

payment_counts = {}
for item in all_expenses:
    method = item.get("payment_method", "Other")
    payment_counts[method] = payment_counts.get(method, 0) + 1
top_payment = max(payment_counts, key=payment_counts.get) if payment_counts else "None"

st.subheader("📊 Dashboard")
st.caption("A quick overview of your spending")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💰 Total Spent", f"₹{dashboard_total:,.2f}")
with col2:
    st.metric("📅 This Month", f"₹{dashboard_monthly:,.2f}")
with col3:
    st.metric("🧾 Total Expenses", dashboard_count)
with col4:
    st.metric("💳 Most Used Payment", top_payment)


# -----------------------------
# Add expense
# -----------------------------
with st.expander("➕ Add New Expense", expanded=True):
    st.caption("Enter the details of your expense below.")
    with st.form("add_expense_form", clear_on_submit=True):
        amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=10.0, format="%.2f")
        description = st.text_input("📝 Description")
        category = st.selectbox("🏷️ Category", CATEGORIES)
        payment_method = st.selectbox("💳 Payment Method", PAYMENT_METHODS)
        expense_date = st.date_input("📅 Date", value=today)
        add_submitted = st.form_submit_button("➕ Add Expense", type="primary")

    if add_submitted:
        if amount <= 0:
            st.error("Please enter an amount greater than ₹0.")
        elif not description.strip():
            st.error("Please enter a description for the expense.")
        else:
            new_expense = {
                "date": expense_date,
                "amount": float(amount),
                "description": description.strip(),
                "category": category,
                "payment_method": payment_method,
            }
            st.session_state.expenses.append(new_expense)
            try:
                save_expenses(st.session_state.expenses)
                st.success("Expense added successfully!")
                st.rerun()
            except OSError as exc:
                st.error(f"Could not save the expense to CSV: {exc}")


# -----------------------------
# Month/year selection
# -----------------------------
st.divider()
st.subheader("📅 Select Month")
st.caption("Choose the month and year you want to view.")

current_year = today.year
years = list(range(min(2025, current_year - 4), max(2027, current_year + 2) + 1))
col_month, col_year = st.columns(2)
with col_month:
    selected_month = st.selectbox(
        "Choose a month",
        MONTHS,
        index=today.month - 1,
        key="selected_month",
    )
with col_year:
    selected_year = st.selectbox(
        "Choose a year",
        years,
        index=years.index(current_year),
        key="selected_year",
    )

month_number = MONTHS.index(selected_month) + 1
selected_expenses = [
    item for item in st.session_state.expenses
    if item["date"].year == selected_year and item["date"].month == month_number
]
selected_month_total = sum(item["amount"] for item in selected_expenses)


# -----------------------------
# Spending insights
# -----------------------------
st.divider()
st.subheader("💡 Spending Insights")
st.caption("A quick look at your spending habits for the selected month.")

if selected_expenses:
    highest_expense = max(selected_expenses, key=lambda item: item["amount"])
    average_expense = selected_month_total / len(selected_expenses)
    insight_category_totals = {}
    for item in selected_expenses:
        insight_category_totals[item["category"]] = (
            insight_category_totals.get(item["category"], 0.0) + item["amount"]
        )
    highest_category = max(insight_category_totals, key=insight_category_totals.get)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💸 Highest Expense", f"₹{highest_expense['amount']:,.2f}")
        st.write(f"📝 {highest_expense['description']}")
    with col2:
        st.metric("📊 Average Expense", f"₹{average_expense:,.2f}")
    with col3:
        st.metric("🏷️ Highest Category", highest_category)
else:
    st.info(f"No expenses found for {selected_month} {selected_year}.")


# -----------------------------
# Monthly budget and savings goal
# -----------------------------
st.subheader("💰 Monthly Budget")
st.caption("Set and track your spending limit for the selected month.")
budget_key = f"{selected_year}-{month_number}"
current_budget = st.session_state.budgets.get(budget_key, 0.0)

monthly_budget = st.number_input(
    "Set your monthly budget",
    min_value=0.0,
    step=500.0,
    value=float(current_budget),
    format="%.2f",
    key=f"budget_input_{budget_key}",
)

if monthly_budget != current_budget:
    st.session_state.budgets[budget_key] = float(monthly_budget)
    try:
        save_budgets(st.session_state.budgets)
    except OSError as exc:
        st.error(f"Could not save the budget: {exc}")

st.divider()
st.subheader("🎯 Savings Goal")
st.caption("Set a savings target and track the amount remaining in your monthly budget.")

savings_goal = st.number_input(
    "Set your savings goal",
    min_value=0.0,
    step=500.0,
    value=float(st.session_state.savings_goal),
    format="%.2f",
    key="savings_goal_input",
)
if savings_goal != st.session_state.savings_goal:
    st.session_state.savings_goal = float(savings_goal)
    try:
        save_savings_goal(savings_goal)
        st.success("Savings goal updated!")
    except OSError as exc:
        st.error(f"Could not save the savings goal: {exc}")

if savings_goal > 0:
    st.write(f"🎯 Your savings goal is ₹{savings_goal:,.2f}")
    remaining_budget_for_goal = monthly_budget - selected_month_total
    goal_progress = max(0.0, min(remaining_budget_for_goal / savings_goal, 1.0))
    st.progress(goal_progress)
    st.write(f"💵 Remaining from this month's budget: ₹{remaining_budget_for_goal:,.2f}")
    st.write(f"🎯 Goal: ₹{savings_goal:,.2f}")
    if remaining_budget_for_goal >= savings_goal:
        st.success("🎉 The amount remaining from your budget meets your goal.")
    elif remaining_budget_for_goal > 0:
        st.info(f"₹{savings_goal - remaining_budget_for_goal:,.2f} more of your budget would need to remain to meet this goal.")
    else:
        st.warning("Your spending has reached or exceeded your monthly budget. This is budget progress, not a calculation of actual savings.")


# -----------------------------
# Search, filter, edit and delete
# -----------------------------
st.subheader("Your Expenses")
st.caption("Search, filter, edit, or delete your recorded expenses.")

filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    search_text = st.text_input("🔍 Search expenses", placeholder="Search by description...")
    filter_category = st.selectbox("📂 Filter by category", ["All"] + CATEGORIES)
with filter_col2:
    filter_payment = st.selectbox("💳 Filter by payment method", ["All"] + PAYMENT_METHODS)

filtered_expenses = []
for index, item in enumerate(st.session_state.expenses):
    matches = (
        item["date"].year == selected_year
        and item["date"].month == month_number
        and search_text.casefold() in item["description"].casefold()
        and (filter_category == "All" or item["category"] == filter_category)
        and (filter_payment == "All" or item.get("payment_method", "Other") == filter_payment)
    )
    if matches:
        filtered_expenses.append((index, item))

if not st.session_state.expenses:
    st.info("No expenses added yet.")
elif not filtered_expenses:
    st.info("No expenses match your selected month and filters.")
else:
    for index, item in filtered_expenses:
        col_item, col_actions = st.columns([4, 1])
        with col_item:
            st.markdown(f"### 💰 ₹{item['amount']:,.2f}")
            st.write(
                f"📅 {item['date']}  •  📝 {item['description']}  •  "
                f"🏷️ {item['category']}  •  💳 {item.get('payment_method', 'Other')}"
            )
        with col_actions:
            edit_col, delete_col = st.columns(2)
            with edit_col:
                if st.button("✏️", key=f"edit_{index}", help="Edit this expense"):
                    st.session_state.editing = index
                    st.rerun()
            with delete_col:
                if st.button("🗑️", key=f"delete_{index}", help="Delete this expense"):
                    st.session_state.expenses.pop(index)
                    if st.session_state.editing == index:
                        st.session_state.editing = None
                    elif isinstance(st.session_state.editing, int) and st.session_state.editing > index:
                        st.session_state.editing -= 1
                    try:
                        save_expenses(st.session_state.expenses)
                        st.success("Expense deleted.")
                    except OSError as exc:
                        st.error(f"Could not save the deletion: {exc}")
                    st.rerun()

# Edit form is shown only while the selected index remains valid.
editing_index = st.session_state.editing
if isinstance(editing_index, int) and 0 <= editing_index < len(st.session_state.expenses):
    item = st.session_state.expenses[editing_index]
    st.divider()
    st.subheader("✏️ Edit Expense")
    with st.form(f"edit_expense_form_{editing_index}"):
        new_amount = st.number_input(
            "Amount (₹)", min_value=0.01, value=float(item["amount"]),
            step=10.0, format="%.2f"
        )
        new_description = st.text_input("Description", value=item["description"])
        new_category = st.selectbox(
            "Category", CATEGORIES,
            index=CATEGORIES.index(item["category"]) if item["category"] in CATEGORIES else CATEGORIES.index("Other"),
        )
        old_payment = item.get("payment_method", "Other")
        new_payment_method = st.selectbox(
            "Payment Method", PAYMENT_METHODS,
            index=PAYMENT_METHODS.index(old_payment) if old_payment in PAYMENT_METHODS else PAYMENT_METHODS.index("Other"),
        )
        new_date = st.date_input("Date", value=item["date"])
        save_changes = st.form_submit_button("Save Changes", type="primary")
        cancel_edit = st.form_submit_button("Cancel")

    if cancel_edit:
        st.session_state.editing = None
        st.rerun()

    if save_changes:
        if not new_description.strip():
            st.error("Description cannot be empty.")
        else:
            updated = {
                "date": new_date,
                "amount": float(new_amount),
                "description": new_description.strip(),
                "category": new_category,
                "payment_method": new_payment_method,
            }
            previous = st.session_state.expenses[editing_index]
            st.session_state.expenses[editing_index] = updated
            try:
                save_expenses(st.session_state.expenses)
                st.session_state.editing = None
                st.success("Expense updated successfully!")
                st.rerun()
            except OSError as exc:
                st.session_state.expenses[editing_index] = previous
                st.error(f"Could not save the update: {exc}")
elif editing_index is not None:
    st.session_state.editing = None


# -----------------------------
# Expense overview and budget status
# -----------------------------
st.divider()
st.subheader("💵 Expense Overview")
st.caption("A summary of your spending for the selected month.")

all_time_total = sum(item["amount"] for item in st.session_state.expenses)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Spent (All Time)", f"₹{all_time_total:,.2f}")
with col2:
    st.metric("Selected Month", f"₹{selected_month_total:,.2f}")
with col3:
    st.metric("Number of Expenses", len(st.session_state.expenses))

st.divider()
st.subheader("💰 Budget Status")
st.caption("See how your spending compares with your monthly budget.")
remaining_budget = monthly_budget - selected_month_total
if monthly_budget > 0:
    budget_used = selected_month_total / monthly_budget
    st.progress(min(budget_used, 1.0))
    st.write(f"{budget_used * 100:.1f}% of your budget used")
if remaining_budget >= 0:
    st.success(f"🟢 You have ₹{remaining_budget:,.2f} remaining this month.")
else:
    st.error(f"🔴 You have exceeded your budget by ₹{abs(remaining_budget):,.2f}.")


# -----------------------------
# Category and payment summaries
# -----------------------------
st.divider()
st.subheader("📊 Category Summary")
st.caption("See how your spending is distributed across all recorded expenses.")
category_totals = {}
for item in st.session_state.expenses:
    category_totals[item["category"]] = category_totals.get(item["category"], 0.0) + item["amount"]
for category_name, amount_value in category_totals.items():
    st.write(f"**{category_name}:** ₹{amount_value:,.2f}")
if category_totals:
    st.bar_chart(category_totals)
else:
    st.info("No category data available yet.")

st.divider()
st.subheader(f"📅 {selected_month} {selected_year} Category Summary")
st.caption("Category-wise breakdown of your spending for the selected month.")
monthly_category_totals = {}
for item in selected_expenses:
    monthly_category_totals[item["category"]] = (
        monthly_category_totals.get(item["category"], 0.0) + item["amount"]
    )
if monthly_category_totals:
    for category_name, amount_value in monthly_category_totals.items():
        st.write(f"**{category_name}:** ₹{amount_value:,.2f}")
    st.bar_chart(monthly_category_totals)
else:
    st.info(f"No expenses found for {selected_month} {selected_year}.")

st.divider()
st.subheader("💳 Payment Method Summary")
st.caption("See how you usually pay for expenses in the selected month.")
payment_totals = {}
for item in selected_expenses:
    method = item.get("payment_method", "Other")
    payment_totals[method] = payment_totals.get(method, 0.0) + item["amount"]
if payment_totals:
    for method, amount_value in payment_totals.items():
        st.write(f"**{method}:** ₹{amount_value:,.2f}")
    st.bar_chart(payment_totals)
else:
    st.info("No payment data available for this month.")


# -----------------------------
# Monthly spending trends
# -----------------------------
st.divider()
st.subheader("📈 Spending Trends")
st.caption("Track how your spending changes month to month for the selected year.")

year_expenses = [item for item in st.session_state.expenses if item["date"].year == selected_year]
monthly_totals = {month_name: 0.0 for month_name in MONTHS}
for item in year_expenses:
    month_name = item["date"].strftime("%B")
    monthly_totals[month_name] += item["amount"]

monthly_data = pd.DataFrame(
    {"Month": MONTHS, "Amount": [monthly_totals[month_name] for month_name in MONTHS]}
)
if monthly_data["Amount"].sum() > 0:
    chart = alt.Chart(monthly_data).mark_bar().encode(
        x=alt.X("Month:N", sort=MONTHS, title="Month"),
        y=alt.Y("Amount:Q", title="Amount (₹)"),
        tooltip=[
            alt.Tooltip("Month:N", title="Month"),
            alt.Tooltip("Amount:Q", title="Amount", format=",.2f"),
        ],
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info(f"No spending trend data available for {selected_year}.")

if month_number > 1:
    previous_month = MONTHS[month_number - 2]
    current_spending = monthly_totals[selected_month]
    previous_spending = monthly_totals[previous_month]
    if current_spending > previous_spending:
        st.warning(
            f"📈 You spent ₹{current_spending - previous_spending:,.2f} more than {previous_month} in {selected_year}."
        )
    elif current_spending < previous_spending:
        st.success(
            f"📉 You spent ₹{previous_spending - current_spending:,.2f} less than {previous_month} in {selected_year}."
        )
    else:
        st.info(f"➡️ Your spending is the same as {previous_month} in {selected_year}.")
else:
    st.info("January has no previous month within the selected year to compare.")


# -----------------------------
# CSV export
# -----------------------------
st.divider()
st.subheader("📥 Export Expenses")
st.caption("Download your filtered expenses as a CSV file.")
export_rows = [item for _, item in filtered_expenses]
csv_data = write_csv_download(export_rows)
st.download_button(
    label="📥 Download Filtered Expenses",
    data=csv_data,
    file_name=f"expenses_{selected_year}_{month_number:02d}.csv",
    mime="text/csv",
)
st.write(f"**{len(export_rows)} expense(s) ready to download.**")


# -----------------------------
# Clear data
# -----------------------------
st.divider()
st.subheader("⚠️ Manage Data")
st.caption("Manage or clear your saved expense data.")

if "confirm_clear" not in st.session_state:
    st.session_state.confirm_clear = False

if st.button("Clear All Expenses", type="secondary"):
    st.session_state.confirm_clear = True

if st.session_state.confirm_clear:
    st.warning("This will permanently remove all recorded expenses from the current CSV file.")
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Yes, clear all expenses", type="primary"):
            st.session_state.expenses = []
            st.session_state.editing = None
            try:
                save_expenses(st.session_state.expenses)
                st.session_state.confirm_clear = False
                st.success("All expenses have been cleared.")
                st.rerun()
            except OSError as exc:
                st.error(f"Could not clear saved expenses: {exc}")
    with cancel_col:
        if st.button("Cancel clearing"):
            st.session_state.confirm_clear = False
            st.rerun()

st.divider()
st.caption("💰 Personal Expense Tracker • Created by Piyush Dhanraj")
