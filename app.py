"""
SpendWise Student — complete Flask application.
Requires db.py with get_db_connection() and init_db(), and MySQL tables:
users, transactions, budgets, savings_goals.
"""
import os
import re
import csv
import io
import math
import calendar
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, make_response
)
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection, init_db

app = Flask(__name__)

@app.template_filter("currency")
def currency_filter(value):
    try:
        return "₹{:,.2f}".format(float(value or 0))
    except (ValueError, TypeError):
        return "₹0.00"
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-production")
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7

INCOME_CATEGORIES = ["Salary", "Freelance", "Allowance", "Scholarship", "Other"]
EXPENSE_CATEGORIES = ["Food", "Transport", "Education", "Shopping", "Bills", "Entertainment", "Other"]


def format_inr(amount):
    try:
        value = float(amount or 0)
    except (ValueError, TypeError):
        value = 0.0
    sign = "-" if value < 0 else ""
    value = abs(value)
    whole, fraction = f"{value:.2f}".split(".")
    if len(whole) > 3:
        last = whole[-3:]
        rest = whole[:-3]
        groups = []
        while rest:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        whole = ",".join(groups + [last])
    return f"{sign}₹{whole}.{fraction}"


app.jinja_env.filters["inr"] = format_inr


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def db_connection_or_redirect():
    conn = get_db_connection()
    if not conn:
        flash("Database connection failed. Please try again later.", "danger")
    return conn


def parse_amount(value):
    amount = Decimal(str(value).strip())
    if not amount.is_finite() or amount <= 0:
        raise InvalidOperation
    return amount


def valid_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    errors, values = {}, {}
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        values = {"name": name, "email": email}
        if not name or len(name) > 100:
            errors["name"] = "Enter a name of 1–100 characters."
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+$", email) or len(email) > 150:
            errors["email"] = "Enter a valid email address."
        if len(password) < 6:
            errors["password"] = "Password must contain at least 6 characters."
        if password != confirm:
            errors["confirm_password"] = "Passwords do not match."
        if not errors:
            conn = db_connection_or_redirect()
            if conn:
                try:
                    cur = conn.cursor(dictionary=True)
                    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
                    if cur.fetchone():
                        errors["email"] = "An account with this email already exists."
                    else:
                        cur.execute(
                            "INSERT INTO users (name,email,password_hash) VALUES (%s,%s,%s)",
                            (name, email, generate_password_hash(password))
                        )
                        conn.commit()
                        flash("Account created. Please log in.", "success")
                        return redirect(url_for("login"))
                except Exception as exc:
                    conn.rollback()
                    print("[signup]", exc)
                    flash("Could not create the account. Please try again.", "danger")
                finally:
                    conn.close()
    return render_template("auth/signup.html", errors=errors, values=values)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    errors, values = {}, {}
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        values = {"email": email}
        if not email:
            errors["email"] = "Email is required."
        if not password:
            errors["password"] = "Password is required."
        if not errors:
            conn = db_connection_or_redirect()
            if conn:
                try:
                    cur = conn.cursor(dictionary=True)
                    cur.execute("SELECT id,name,email,password_hash FROM users WHERE email=%s", (email,))
                    user = cur.fetchone()
                    if user and check_password_hash(user["password_hash"], password):
                        session.clear()
                        session["user_id"] = user["id"]
                        session["user_name"] = user["name"]
                        session["user_email"] = user["email"]
                        session.permanent = True
                        flash(f"Welcome back, {user['name']}!", "success")
                        return redirect(url_for("dashboard"))
                    errors["email"] = "Invalid email or password."
                except Exception as exc:
                    print("[login]", exc)
                    flash("Could not log in. Please try again.", "danger")
                finally:
                    conn.close()
    return render_template("auth/login.html", errors=errors, values=values)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


def fetch_one(query, params):
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        return cur.fetchone()
    finally:
        conn.close()


@app.route("/")
@login_required
def dashboard():
    uid = session["user_id"]
    totals = {"income": 0.0, "expense": 0.0}
    recent = []
    conn = db_connection_or_redirect()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT type, COALESCE(SUM(amount),0) total FROM transactions WHERE user_id=%s GROUP BY type",
                (uid,)
            )
            for row in cur.fetchall():
                totals[row["type"]] = float(row["total"])
            cur.execute(
                """SELECT id,title,amount,type,category,date,created_at FROM transactions
                   WHERE user_id=%s ORDER BY date DESC,id DESC LIMIT 10""", (uid,)
            )
            recent = cur.fetchall()
        except Exception as exc:
            print("[dashboard]", exc)
            flash("Could not load all dashboard data.", "danger")
        finally:
            conn.close()
    income, expense = totals["income"], totals["expense"]
    return render_template(
        "dashboard.html", total_income=income, total_expense=expense,
        total_balance=income-expense, recent_transactions=recent, now=datetime.now()
    )


def transaction_form(is_edit=False, transaction=None):
    errors, values = {}, {}
    today = date.today().isoformat()
    if transaction:
        values = {
            "title": transaction["title"], "amount": str(transaction["amount"]),
            "type": transaction["type"], "category": transaction["category"],
            "date": transaction["date"].isoformat() if hasattr(transaction["date"], "isoformat") else str(transaction["date"])
        }
    if request.method == "POST":
        values = {k: request.form.get(k, "").strip() for k in ("title", "amount", "type", "category", "date")}
        title, tx_type, category = values["title"], values["type"].lower(), values["category"]
        if not title or len(title) > 100:
            errors["title"] = "Title is required and must be at most 100 characters."
        try:
            amount = parse_amount(values["amount"])
        except (InvalidOperation, ValueError):
            errors["amount"] = "Enter an amount greater than zero."
            amount = None
        if tx_type not in ("income", "expense"):
            errors["type"] = "Choose income or expense."
        allowed = INCOME_CATEGORIES if tx_type == "income" else EXPENSE_CATEGORIES
        if tx_type in ("income", "expense") and category not in allowed:
            errors["category"] = "Choose a valid category for this transaction type."
        try:
            tx_date = valid_date(values["date"])
        except (ValueError, TypeError):
            errors["date"] = "Enter a valid date."
            tx_date = None
        if not errors:
            return values, amount, tx_date, errors
    return values, None, None, errors


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_transaction():
    today = date.today().isoformat()
    if request.method == "POST":
        values, amount, tx_date, errors = transaction_form()
        if not errors:
            conn = db_connection_or_redirect()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        """INSERT INTO transactions (user_id,title,amount,type,category,date)
                           VALUES (%s,%s,%s,%s,%s,%s)""",
                        (session["user_id"], values["title"], amount, values["type"].lower(), values["category"], tx_date)
                    )
                    conn.commit()
                    flash("Transaction added successfully.", "success")
                    return redirect(url_for("all_transactions"))
                except Exception as exc:
                    conn.rollback()
                    print("[add transaction]", exc)
                    flash("Could not save the transaction.", "danger")
                finally:
                    conn.close()
        return render_template("transaction_form.html", is_edit=False, today=today, values=values, errors=errors)
    return render_template("transaction_form.html", is_edit=False, today=today, values={}, errors={})


@app.route("/transactions")
@login_required
def all_transactions():
    uid = session["user_id"]
    page = max(1, request.args.get("page", 1, type=int))
    per_page = 10
    f_type = request.args.get("type", "all").strip().lower()
    category = request.args.get("category", "all").strip()
    search = request.args.get("search", "").strip()[:100]
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    sort = request.args.get("sort", "date_desc").strip()
    clauses, params = ["user_id=%s"], [uid]
    if f_type in ("income", "expense"):
        clauses.append("type=%s")
        params.append(f_type)
    if category in INCOME_CATEGORIES + EXPENSE_CATEGORIES:
        clauses.append("category=%s")
        params.append(category)
    if search:
        clauses.append("title LIKE %s")
        params.append(f"%{search}%")
    try:
        if start_date:
            clauses.append("date >= %s")
            params.append(valid_date(start_date))
    except ValueError:
        start_date = ""
    try:
        if end_date:
            clauses.append("date <= %s")
            params.append(valid_date(end_date))
    except ValueError:
        end_date = ""
    where_sql = " WHERE " + " AND ".join(clauses)
    sort_map = {
        "date_desc": "date DESC,id DESC", "date_asc": "date ASC,id ASC",
        "amount_desc": "amount DESC,id DESC", "amount_asc": "amount ASC,id ASC"
    }
    sort_sql = sort_map.get(sort, sort_map["date_desc"])
    rows, total_count, total_pages = [], 0, 1
    conn = db_connection_or_redirect()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT COUNT(*) total FROM transactions" + where_sql, tuple(params))
            total_count = cur.fetchone()["total"]
            total_pages = max(1, math.ceil(total_count / per_page))
            page = min(page, total_pages)
            cur.execute(
                "SELECT id,title,amount,type,category,date,created_at FROM transactions" + where_sql +
                f" ORDER BY {sort_sql} LIMIT %s OFFSET %s",
                tuple(params + [per_page, (page-1)*per_page])
            )
            rows = cur.fetchall()
        except Exception as exc:
            print("[transactions]", exc)
            flash("Could not load transactions.", "danger")
        finally:
            conn.close()
    current_filters = {
        "type": f_type, "category": category, "search": search,
        "start_date": start_date, "end_date": end_date, "sort": sort
    }
    return render_template(
        "transactions.html", transactions=rows, total_count=total_count,
        total_pages=total_pages, current_page=page, current_filters=current_filters,
        income_categories=INCOME_CATEGORIES, expense_categories=EXPENSE_CATEGORIES
    )


@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_transaction(id):
    conn = db_connection_or_redirect()
    if not conn:
        return redirect(url_for("all_transactions"))
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id,title,amount,type,category,date FROM transactions WHERE id=%s AND user_id=%s",
            (id, session["user_id"])
        )
        transaction = cur.fetchone()
        if not transaction:
            flash("Transaction not found.", "danger")
            return redirect(url_for("all_transactions"))
        if request.method == "POST":
            values, amount, tx_date, errors = transaction_form(True, transaction)
            if not errors:
                cur.execute(
                    """UPDATE transactions SET title=%s,amount=%s,type=%s,category=%s,date=%s
                       WHERE id=%s AND user_id=%s""",
                    (values["title"], amount, values["type"].lower(), values["category"], tx_date, id, session["user_id"])
                )
                conn.commit()
                flash("Transaction updated successfully.", "success")
                return redirect(url_for("all_transactions"))
            return render_template("transaction_form.html", is_edit=True, transaction=transaction, values=values, errors=errors)
        return render_template("transaction_form.html", is_edit=True, transaction=transaction, values={}, errors={})
    except Exception as exc:
        print("[edit transaction]", exc)
        flash("Could not edit the transaction.", "danger")
        return redirect(url_for("all_transactions"))
    finally:
        conn.close()


@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete_transaction(id):
    conn = db_connection_or_redirect()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM transactions WHERE id=%s AND user_id=%s", (id, session["user_id"]))
            conn.commit()
            flash("Transaction deleted." if cur.rowcount else "Transaction not found.", "success" if cur.rowcount else "warning")
        except Exception as exc:
            conn.rollback()
            print("[delete transaction]", exc)
            flash("Could not delete the transaction.", "danger")
        finally:
            conn.close()
    return redirect(url_for("all_transactions"))


@app.route("/transactions/export")
@login_required
def export_transactions():
    uid = session["user_id"]
    clauses, params = ["user_id=%s"], [uid]
    f_type = request.args.get("type", "all").strip().lower()
    category = request.args.get("category", "all").strip()
    search = request.args.get("search", "").strip()[:100]
    start_date, end_date = request.args.get("start_date", "").strip(), request.args.get("end_date", "").strip()
    if f_type in ("income", "expense"):
        clauses.append("type=%s")
        params.append(f_type)
    if category in INCOME_CATEGORIES + EXPENSE_CATEGORIES:
        clauses.append("category=%s")
        params.append(category)
    if search:
        clauses.append("title LIKE %s")
        params.append(f"%{search}%")
    try:
        if start_date:
            clauses.append("date >= %s")
            params.append(valid_date(start_date))
    except ValueError:
        pass
    try:
        if end_date:
            clauses.append("date <= %s")
            params.append(valid_date(end_date))
    except ValueError:
        pass
    conn = db_connection_or_redirect()
    if not conn:
        return redirect(url_for("all_transactions"))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT date,title,type,category,amount FROM transactions WHERE " + " AND ".join(clauses) + " ORDER BY date DESC,id DESC",
            tuple(params)
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Title", "Type", "Category", "Amount (INR)"])
        for row in cur.fetchall():
            writer.writerow([row[0], row[1], row[2], row[3], row[4]])
        response = make_response("\ufeff" + output.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = "attachment; filename=spendwise_transactions.csv"
        return response
    except Exception as exc:
        print("[export]", exc)
        flash("Could not export transactions.", "danger")
        return redirect(url_for("all_transactions"))
    finally:
        conn.close()


@app.route("/api/chart-data")
@login_required
def chart_data():
    uid = session["user_id"]
    months = []
    year, month = date.today().year, date.today().month
    for _ in range(6):
        months.append((year, month, date(year, month, 1)))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    months.reverse()
    labels = [d.strftime("%b %Y") for _, _, d in months]
    month_keys = [f"{y:04d}-{m:02d}" for y, m, _ in months]
    income, expense = [0.0]*6, [0.0]*6
    categories = {"labels": [], "data": []}
    conn = db_connection_or_redirect()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT category,SUM(amount) total FROM transactions WHERE user_id=%s AND type='expense' GROUP BY category ORDER BY total DESC",
                (uid,)
            )
            for row in cur.fetchall():
                categories["labels"].append(row["category"])
                categories["data"].append(float(row["total"]))
            start = months[0][2]
            last_y, last_m, _ = months[-1]
            last_day = calendar.monthrange(last_y, last_m)[1]
            end = date(last_y, last_m, last_day)
            cur.execute(
                """SELECT DATE_FORMAT(date,'%%Y-%%m') ym,type,SUM(amount) total
                   FROM transactions WHERE user_id=%s AND date BETWEEN %s AND %s
                   GROUP BY ym,type""", (uid, start, end)
            )
            index = {key: i for i, key in enumerate(month_keys)}
            for row in cur.fetchall():
                if row["ym"] in index:
                    i = index[row["ym"]]
                    if row["type"] == "income":
                        income[i] = float(row["total"])
                    else:
                        expense[i] = float(row["total"])
        except Exception as exc:
            print("[chart data]", exc)
        finally:
            conn.close()
    return jsonify({"categories": categories, "monthly": {"labels": labels, "income": income, "expense": expense}})


@app.route("/budgets", methods=["GET", "POST"])
@login_required
def budgets():
    uid = session["user_id"]
    today = date.today()
    errors = {}
    if request.method == "POST":
        category = request.form.get("category", "").strip()
        try:
            amount = parse_amount(request.form.get("amount", ""))
        except (InvalidOperation, ValueError):
            amount = None
            errors["amount"] = "Enter a budget greater than zero."
        try:
            month = int(request.form.get("month", today.month))
            year = int(request.form.get("year", today.year))
            if not 1 <= month <= 12 or not 2000 <= year <= 2100:
                raise ValueError
        except ValueError:
            month, year = today.month, today.year
            errors["month"] = "Choose a valid month and year."
        if category not in EXPENSE_CATEGORIES:
            errors["category"] = "Choose a valid expense category."
        if not errors:
            conn = db_connection_or_redirect()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        """INSERT INTO budgets (user_id,category,amount,month,year)
                           VALUES (%s,%s,%s,%s,%s)
                           ON DUPLICATE KEY UPDATE amount=VALUES(amount)""",
                        (uid, category, amount, month, year)
                    )
                    conn.commit()
                    flash("Budget saved.", "success")
                    return redirect(url_for("budgets", month=month, year=year))
                except Exception as exc:
                    conn.rollback()
                    print("[budget save]", exc)
                    flash("Could not save budget. Check that the budgets table exists.", "danger")
                finally:
                    conn.close()
    try:
        month = int(request.args.get("month", today.month))
        year = int(request.args.get("year", today.year))
        if not 1 <= month <= 12 or not 2000 <= year <= 2100:
            raise ValueError
    except ValueError:
        month, year = today.month, today.year
    items = []
    conn = db_connection_or_redirect()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT b.id,b.category,b.amount,
                          COALESCE(SUM(t.amount),0) AS spent
                   FROM budgets b LEFT JOIN transactions t
                     ON t.user_id=b.user_id AND t.category=b.category AND t.type='expense'
                    AND YEAR(t.date)=b.year AND MONTH(t.date)=b.month
                   WHERE b.user_id=%s AND b.month=%s AND b.year=%s
                   GROUP BY b.id,b.category,b.amount ORDER BY b.category""",
                (uid, month, year)
            )
            items = cur.fetchall()
            for item in items:
                item["amount"] = float(item["amount"])
                item["spent"] = float(item["spent"])
                item["percentage"] = min(100, round(item["spent"] / item["amount"] * 100)) if item["amount"] else 0
                item["exceeded"] = item["spent"] > item["amount"]
        except Exception as exc:
            print("[budgets]", exc)
            flash("Could not load budgets. Confirm the budgets table exists.", "danger")
        finally:
            conn.close()
    return render_template("budgets.html", budgets=items, categories=EXPENSE_CATEGORIES, month=month, year=year, errors=errors, today=today)


@app.route("/goals", methods=["GET", "POST"])
@login_required
def savings_goals():
    uid = session["user_id"]
    errors = {}
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        try:
            target = parse_amount(request.form.get("target_amount", ""))
        except (InvalidOperation, ValueError):
            target = None
            errors["target_amount"] = "Enter a target amount greater than zero."
        saved_raw = request.form.get("saved_amount", "0").strip() or "0"
        try:
            saved = Decimal(saved_raw)
            if not saved.is_finite() or saved < 0 or (target is not None and saved > target):
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            saved = Decimal("0")
            errors["saved_amount"] = "Saved amount must be zero or more and cannot exceed the target."
        target_date_raw = request.form.get("target_date", "").strip()
        try:
            target_date = valid_date(target_date_raw) if target_date_raw else None
        except ValueError:
            target_date = None
            errors["target_date"] = "Choose a valid target date."
        if not title or len(title) > 100:
            errors["title"] = "Goal title is required (maximum 100 characters)."
        if not errors:
            conn = db_connection_or_redirect()
            if conn:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        """INSERT INTO savings_goals (user_id,title,target_amount,saved_amount,target_date)
                           VALUES (%s,%s,%s,%s,%s)""",
                        (uid, title, target, saved, target_date)
                    )
                    conn.commit()
                    flash("Savings goal created.", "success")
                    return redirect(url_for("savings_goals"))
                except Exception as exc:
                    conn.rollback()
                    print("[goal create]", exc)
                    flash("Could not create goal. Check that the savings_goals table exists.", "danger")
                finally:
                    conn.close()
    goals = []
    conn = db_connection_or_redirect()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT id,title,target_amount,saved_amount,target_date,created_at
                   FROM savings_goals WHERE user_id=%s ORDER BY created_at DESC,id DESC""", (uid,)
            )
            goals = cur.fetchall()
            for goal in goals:
                goal["target_amount"] = float(goal["target_amount"])
                goal["saved_amount"] = float(goal["saved_amount"])
                goal["remaining"] = max(0, goal["target_amount"] - goal["saved_amount"])
                goal["percentage"] = min(100, round(goal["saved_amount"] / goal["target_amount"] * 100)) if goal["target_amount"] else 0
        except Exception as exc:
            print("[goals]", exc)
            flash("Could not load goals. Confirm the savings_goals table exists.", "danger")
        finally:
            conn.close()
    return render_template("goals.html", goals=goals, errors=errors, values=request.form if request.method == "POST" else {})


@app.route("/goals/<int:goal_id>/update", methods=["POST"])
@login_required
def update_goal(goal_id):
    try:
        saved = Decimal(request.form.get("saved_amount", "").strip())
        if not saved.is_finite() or saved < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        flash("Enter a valid saved amount.", "danger")
        return redirect(url_for("savings_goals"))
    conn = db_connection_or_redirect()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE savings_goals SET saved_amount=%s
                   WHERE id=%s AND user_id=%s AND target_amount >= %s""",
                (saved, goal_id, session["user_id"], saved)
            )
            conn.commit()
            flash("Goal progress updated." if cur.rowcount else "Goal not found or saved amount exceeds its target.", "success" if cur.rowcount else "warning")
        except Exception as exc:
            conn.rollback()
            print("[goal update]", exc)
            flash("Could not update goal.", "danger")
        finally:
            conn.close()
    return redirect(url_for("savings_goals"))


@app.route("/goals/<int:goal_id>/delete", methods=["POST"])
@login_required
def delete_goal(goal_id):
    conn = db_connection_or_redirect()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM savings_goals WHERE id=%s AND user_id=%s", (goal_id, session["user_id"]))
            conn.commit()
            flash("Goal deleted." if cur.rowcount else "Goal not found.", "success" if cur.rowcount else "warning")
        except Exception as exc:
            conn.rollback()
            print("[goal delete]", exc)
            flash("Could not delete goal.", "danger")
        finally:
            conn.close()
    return redirect(url_for("savings_goals"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
