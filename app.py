"""
SpendWise Student - Personal Finance & Budget Tracker for Students
Main Flask Application

Stack:
- Python 3 + Flask
- MySQL (via mysql-connector-python)
- Bootstrap 5 + Vanilla JavaScript + Chart.js

Designed to be clean, modular, and easy to explain in a Semester 3 Diploma viva.
"""

import os
import re
from datetime import date, datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, 
    url_for, flash, session, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection, init_db

# Initialize Flask application
app = Flask(__name__)
# Secret key for signing session cookies securely
app.secret_key = os.environ.get('SECRET_KEY', 'spendwise-student-super-secret-key-2026')

# ---------------------------------------------------------
# Custom Jinja Template Filters & Helpers
# ---------------------------------------------------------
def format_inr(amount):
    """
    Formats a numeric value into Indian Rupee currency format:
    e.g. 120000.00 -> ₹1,20,000.00
         500.00    -> ₹500.00
    """
    if amount is None:
        return "₹0.00"
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return "₹0.00"

    is_negative = val < 0
    val = abs(val)
    parts = f"{val:.2f}".split(".")
    int_part = parts[0]
    dec_part = parts[1]

    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last_three = int_part[-3:]
        remaining = int_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.append(remaining)
        groups.reverse()
        formatted_int = ",".join(groups) + "," + last_three

    result = f"₹{formatted_int}.{dec_part}"
    return f"-{result}" if is_negative else result

# Register the currency filter for Jinja templates
app.jinja_env.filters['inr'] = format_inr


# ---------------------------------------------------------
# Authentication Decorator
# ---------------------------------------------------------
def login_required(f):
    """
    Ensures that a user is authenticated in the session before accessing the route.
    Redirects to the login page if the user is unauthenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------
# Authentication Routes (Phase 1)
# ---------------------------------------------------------

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    User registration route.
    Validates form data inline, hashes password, and saves user to MySQL database.
    """
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    errors = {}
    values = {}

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        values = {'name': name, 'email': email}

        # 1. Server-side validation
        if not name:
            errors['name'] = "Full name is required."
        elif len(name) > 100:
            errors['name'] = "Name must not exceed 100 characters."

        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not email:
            errors['email'] = "Email address is required."
        elif not re.match(email_regex, email):
            errors['email'] = "Please provide a valid email address."
        elif len(email) > 150:
            errors['email'] = "Email must not exceed 150 characters."

        if not password:
            errors['password'] = "Password is required."
        elif len(password) < 6:
            errors['password'] = "Password must be at least 6 characters long."

        if not confirm_password:
            errors['confirm_password'] = "Please confirm your password."
        elif password != confirm_password:
            errors['confirm_password'] = "Passwords do not match."

        # 2. Check for duplicate email if no previous validation errors
        if not errors:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    # Parameterized query prevents SQL injection
                    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                    existing_user = cursor.fetchone()

                    if existing_user:
                        errors['email'] = "An account with this email address already exists."
                    else:
                        # 3. Hash password and insert into users table
                        password_hash = generate_password_hash(password)
                        cursor.execute(
                            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                            (name, email, password_hash)
                        )
                        cursor.close()
                        conn.close()

                        flash("Account created successfully! Please sign in with your credentials.", "success")
                        return redirect(url_for('login'))
                except Exception as e:
                    print(f"[Error in signup] {e}")
                    flash("An unexpected error occurred while creating your account. Please try again.", "danger")
                finally:
                    if conn.is_connected():
                        conn.close()
            else:
                flash("Database connection error. Please verify the MySQL service is running.", "danger")

    return render_template('auth/signup.html', errors=errors, values=values)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route.
    Validates credentials against hashed passwords stored in MySQL.
    """
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    errors = {}
    values = {}

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        values = {'email': email}

        if not email:
            errors['email'] = "Email address is required."
        if not password:
            errors['password'] = "Password is required."

        if not errors:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    # Safe parameterized query
                    cursor.execute(
                        "SELECT id, name, email, password_hash FROM users WHERE email = %s", 
                        (email,)
                    )
                    user = cursor.fetchone()
                    cursor.close()
                    conn.close()

                    if user and check_password_hash(user['password_hash'], password):
                        # Credentials verified: store session
                        session['user_id'] = user['id']
                        session['user_name'] = user['name']
                        session['user_email'] = user['email']
                        session.permanent = True

                        flash(f"Welcome back, {user['name']}!", "success")
                        return redirect(url_for('dashboard'))
                    else:
                        errors['email'] = "Invalid email or password. Please try again."
                except Exception as e:
                    print(f"[Error in login] {e}")
                    flash("An unexpected error occurred while logging in.", "danger")
                finally:
                    if conn and conn.is_connected():
                        conn.close()
            else:
                flash("Database connection error. Please verify the MySQL service is running.", "danger")

    return render_template('auth/login.html', errors=errors, values=values)


@app.route('/logout')
def logout():
    """
    Clears the session and logs the user out.
    """
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('login'))


# ---------------------------------------------------------
# Core Application Placeholders (Ready for upcoming phases)
# ---------------------------------------------------------

# Valid category definitions for validation and dynamic dropdowns
INCOME_CATEGORIES = ['Salary', 'Freelance', 'Allowance', 'Scholarship', 'Other']
EXPENSE_CATEGORIES = ['Food', 'Transport', 'Education', 'Shopping', 'Bills', 'Entertainment', 'Other']


# ---------------------------------------------------------
# Core Application Routes (Phase 2)
# ---------------------------------------------------------

@app.route('/')
@login_required
def dashboard():
    """
    Main student dashboard route.
    Computes summary metrics (Total Balance, Total Income, Total Expenses) 
    and fetches recent transactions (latest 10) for the authenticated user.
    """
    user_id = session['user_id']
    total_income = 0.0
    total_expense = 0.0
    recent_transactions = []

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # 1. Calculate Total Income for current user
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE user_id = %s AND type = 'income'",
                (user_id,)
            )
            income_row = cursor.fetchone()
            if income_row:
                total_income = float(income_row['total'])

            # 2. Calculate Total Expenses for current user
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE user_id = %s AND type = 'expense'",
                (user_id,)
            )
            expense_row = cursor.fetchone()
            if expense_row:
                total_expense = float(expense_row['total'])

            # 3. Retrieve 10 most recent transactions
            cursor.execute(
                """
                SELECT id, user_id, title, amount, type, category, date, created_at 
                FROM transactions 
                WHERE user_id = %s 
                ORDER BY date DESC, id DESC 
                LIMIT 10
                """,
                (user_id,)
            )
            recent_transactions = cursor.fetchall()

            cursor.close()
        except Exception as e:
            print(f"[Error in dashboard] {e}")
            flash("Failed to retrieve dashboard metrics.", "danger")
        finally:
            if conn.is_connected():
                conn.close()

    # Total Balance = Total Income - Total Expenses
    total_balance = total_income - total_expense

    return render_template(
        'dashboard.html',
        total_balance=total_balance,
        total_income=total_income,
        total_expense=total_expense,
        recent_transactions=recent_transactions,
        now=datetime.now()
    )


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    """
    Add Transaction route.
    Validates title, positive amount, type, dynamically matched category, and date.
    Inserts validated record into transactions table.
    """
    user_id = session['user_id']
    today_str = date.today().strftime('%Y-%m-%d')
    errors = {}
    values = {}

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        amount_str = request.form.get('amount', '').strip()
        tx_type = request.form.get('type', '').strip().lower()
        category = request.form.get('category', '').strip()
        date_str = request.form.get('date', '').strip()

        values = {
            'title': title,
            'amount': amount_str,
            'type': tx_type,
            'category': category,
            'date': date_str
        }

        # 1. Validate Title
        if not title:
            errors['title'] = "Title is required."
        elif len(title) > 100:
            errors['title'] = "Title cannot exceed 100 characters."

        # 2. Validate Amount (must be numeric and > 0)
        try:
            amount_val = float(amount_str)
            if amount_val <= 0:
                errors['amount'] = "Amount must be strictly greater than ₹0."
        except (ValueError, TypeError):
            errors['amount'] = "Please provide a valid numeric amount."

        # 3. Validate Transaction Type
        if tx_type not in ('income', 'expense'):
            errors['type'] = "Invalid transaction type selected."

        # 4. Validate Category matches Type
        if tx_type == 'income':
            if category not in INCOME_CATEGORIES:
                errors['category'] = f"Please select a valid income category ({', '.join(INCOME_CATEGORIES)})."
        elif tx_type == 'expense':
            if category not in EXPENSE_CATEGORIES:
                errors['category'] = f"Please select a valid expense category ({', '.join(EXPENSE_CATEGORIES)})."

        # 5. Validate Date format
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            errors['date'] = "Please provide a valid date in YYYY-MM-DD format."

        # If no errors, persist to MySQL database
        if not errors:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    insert_query = """
                        INSERT INTO transactions (user_id, title, amount, type, category, date)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(
                        insert_query,
                        (user_id, title, amount_val, tx_type, category, parsed_date)
                    )
                    cursor.close()
                    conn.close()

                    flash(f"Transaction '{title}' added successfully!", "success")
                    return redirect(url_for('dashboard'))
                except Exception as e:
                    print(f"[Error saving transaction] {e}")
                    flash("An error occurred while saving the transaction.", "danger")
                finally:
                    if conn and conn.is_connected():
                        conn.close()
            else:
                flash("Database connection error. Could not save transaction.", "danger")

    return render_template(
        'transaction_form.html',
        is_edit=False,
        today=today_str,
        values=values,
        errors=errors
    )


@app.route('/transactions')
@login_required
def all_transactions():
    """
    Phase 3: All Transactions view.
    Provides complete paginated listing of transactions with filtering by
    type, category, date range, and sorting.
    """
    import math

    user_id = session['user_id']
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Retrieve filter parameters
    filter_type = request.args.get('type', 'all').strip().lower()
    filter_category = request.args.get('category', 'all').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    sort_by = request.args.get('sort', 'date_desc').strip()

    # Build parameterized SQL conditions safely
    where_clauses = ["user_id = %s"]
    params = [user_id]

    if filter_type in ('income', 'expense'):
        where_clauses.append("type = %s")
        params.append(filter_type)

    all_valid_categories = INCOME_CATEGORIES + EXPENSE_CATEGORIES
    if filter_category in all_valid_categories:
        where_clauses.append("category = %s")
        params.append(filter_category)

    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            where_clauses.append("date >= %s")
            params.append(parsed_start)
        except (ValueError, TypeError):
            start_date = ''

    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            where_clauses.append("date <= %s")
            params.append(parsed_end)
        except (ValueError, TypeError):
            end_date = ''

    where_sql = " WHERE " + " AND ".join(where_clauses)

    # Allowed sorting map to prevent SQL injection
    sort_mapping = {
        'date_desc': 'date DESC, id DESC',
        'date_asc': 'date ASC, id ASC',
        'amount_desc': 'amount DESC, id DESC',
        'amount_asc': 'amount ASC, id ASC'
    }
    order_by_sql = sort_mapping.get(sort_by, 'date DESC, id DESC')

    total_count = 0
    transactions = []

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # 1. Count total matching rows
            count_query = f"SELECT COUNT(*) AS cnt FROM transactions {where_sql}"
            cursor.execute(count_query, tuple(params))
            count_row = cursor.fetchone()
            if count_row:
                total_count = count_row['cnt']

            # 2. Calculate pagination
            total_pages = max(1, math.ceil(total_count / per_page))
            if page < 1:
                page = 1
            elif page > total_pages and total_count > 0:
                page = total_pages
            offset = (page - 1) * per_page

            # 3. Retrieve paginated records
            data_query = f"""
                SELECT id, user_id, title, amount, type, category, date, created_at 
                FROM transactions 
                {where_sql} 
                ORDER BY {order_by_sql} 
                LIMIT %s OFFSET %s
            """
            cursor.execute(data_query, tuple(params + [per_page, offset]))
            transactions = cursor.fetchall()

            cursor.close()
        except Exception as e:
            print(f"[Error in all_transactions] {e}")
            flash("Failed to retrieve transactions.", "danger")
        finally:
            if conn.is_connected():
                conn.close()
    else:
        total_pages = 1

    current_filters = {
        'type': filter_type,
        'category': filter_category,
        'start_date': start_date,
        'end_date': end_date,
        'sort': sort_by
    }

    return render_template(
        'transactions.html',
        transactions=transactions,
        total_count=total_count,
        total_pages=total_pages,
        current_page=page,
        current_filters=current_filters,
        income_categories=INCOME_CATEGORIES,
        expense_categories=EXPENSE_CATEGORIES
    )


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    """
    Phase 3: Edit Transaction route.
    Verifies user ownership, pre-populates existing data, validates modifications,
    and updates the transaction record in MySQL.
    """
    user_id = session['user_id']
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.", "danger")
        return redirect(url_for('all_transactions'))

    transaction = None
    try:
        cursor = conn.cursor(dictionary=True)
        # Security check: ensures users can only edit their own transactions
        cursor.execute(
            "SELECT id, user_id, title, amount, type, category, date FROM transactions WHERE id = %s AND user_id = %s",
            (id, user_id)
        )
        transaction = cursor.fetchone()
        cursor.close()
    except Exception as e:
        print(f"[Error loading transaction for edit] {e}")

    if not transaction:
        if conn.is_connected():
            conn.close()
        flash("Transaction not found or you are not authorized to edit it.", "danger")
        return redirect(url_for('all_transactions'))

    errors = {}
    values = {}

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        amount_str = request.form.get('amount', '').strip()
        tx_type = request.form.get('type', '').strip().lower()
        category = request.form.get('category', '').strip()
        date_str = request.form.get('date', '').strip()

        values = {
            'title': title,
            'amount': amount_str,
            'type': tx_type,
            'category': category,
            'date': date_str
        }

        # 1. Validation
        if not title:
            errors['title'] = "Title is required."
        elif len(title) > 100:
            errors['title'] = "Title cannot exceed 100 characters."

        try:
            amount_val = float(amount_str)
            if amount_val <= 0:
                errors['amount'] = "Amount must be strictly greater than ₹0."
        except (ValueError, TypeError):
            errors['amount'] = "Please provide a valid numeric amount."

        if tx_type not in ('income', 'expense'):
            errors['type'] = "Invalid transaction type selected."

        if tx_type == 'income' and category not in INCOME_CATEGORIES:
            errors['category'] = f"Please select a valid income category ({', '.join(INCOME_CATEGORIES)})."
        elif tx_type == 'expense' and category not in EXPENSE_CATEGORIES:
            errors['category'] = f"Please select a valid expense category ({', '.join(EXPENSE_CATEGORIES)})."

        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            errors['date'] = "Please provide a valid date in YYYY-MM-DD format."

        # If valid, execute UPDATE query
        if not errors:
            try:
                update_cursor = conn.cursor()
                update_sql = """
                    UPDATE transactions 
                    SET title = %s, amount = %s, type = %s, category = %s, date = %s 
                    WHERE id = %s AND user_id = %s
                """
                update_cursor.execute(
                    update_sql,
                    (title, amount_val, tx_type, category, parsed_date, id, user_id)
                )
                update_cursor.close()
                conn.close()

                flash(f"Transaction '{title}' updated successfully!", "success")
                return redirect(url_for('all_transactions'))
            except Exception as e:
                print(f"[Error updating transaction] {e}")
                flash("An error occurred while updating the transaction.", "danger")

    if conn and conn.is_connected():
        conn.close()

    return render_template(
        'transaction_form.html',
        is_edit=True,
        transaction=transaction,
        values=values,
        errors=errors
    )


@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    """
    Phase 3: Delete Transaction route.
    Safely deletes a transaction after verifying user ownership.
    Triggered exclusively via POST request to prevent CSRF / accidental link deletion.
    """
    user_id = session['user_id']
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Enforce user_id in WHERE clause for data ownership security
            cursor.execute(
                "DELETE FROM transactions WHERE id = %s AND user_id = %s",
                (id, user_id)
            )
            rows_deleted = cursor.rowcount
            cursor.close()
            conn.close()

            if rows_deleted > 0:
                flash("Transaction deleted successfully.", "success")
            else:
                flash("Transaction not found or you are not authorized to delete it.", "danger")
        except Exception as e:
            print(f"[Error deleting transaction] {e}")
            flash("An error occurred while deleting the transaction.", "danger")
        finally:
            if conn and conn.is_connected():
                conn.close()
    else:
        flash("Database connection error.", "danger")

    # Redirect back to referring page if available, else default to all_transactions
    referrer = request.referrer
    if referrer and ('transactions' in referrer or 'dashboard' in referrer or referrer.endswith('/')):
        return redirect(referrer)
    return redirect(url_for('all_transactions'))



def get_last_six_months():
    """
    Computes date ranges and labels for the last 6 calendar months.
    Returns: list of dicts with 'label', 'ym', 'start', 'end'
    """
    import calendar
    today = date.today()
    months = []
    year = today.year
    month = today.month

    for _ in range(6):
        _, last_day = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)
        months.append({
            'label': start_date.strftime('%b %Y'),
            'ym': start_date.strftime('%Y-%m'),
            'start': start_date,
            'end': end_date
        })
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    months.reverse()
    return months


@app.route('/api/chart-data')
@login_required
def chart_data():
    """
    Phase 4: Chart data API.
    Returns JSON payload for:
    1. Expense breakdown by category (for doughnut chart)
    2. Income vs Expenses comparison for the last 6 months (for bar chart)
    """
    user_id = session['user_id']
    categories_data = {'labels': [], 'data': []}
    monthly_data = {'labels': [], 'income': [], 'expense': []}

    months_info = get_last_six_months()
    month_labels = [m['label'] for m in months_info]
    ym_to_index = {m['ym']: i for i, m in enumerate(months_info)}
    income_by_month = [0.0] * 6
    expense_by_month = [0.0] * 6

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)

            # 1. Expense Breakdown by Category (Doughnut Chart)
            cursor.execute(
                """
                SELECT category, SUM(amount) AS total 
                FROM transactions 
                WHERE user_id = %s AND type = 'expense' 
                GROUP BY category 
                ORDER BY total DESC
                """,
                (user_id,)
            )
            cat_rows = cursor.fetchall()
            for r in cat_rows:
                categories_data['labels'].append(r['category'])
                categories_data['data'].append(float(r['total']))

            # 2. Income vs Expenses for the last 6 months (Bar Chart)
            first_month_start = months_info[0]['start']
            last_month_end = months_info[-1]['end']

            cursor.execute(
                """
                SELECT 
                    DATE_FORMAT(date, '%Y-%m') AS ym,
                    type,
                    SUM(amount) AS total
                FROM transactions
                WHERE user_id = %s AND date >= %s AND date <= %s
                GROUP BY ym, type
                """,
                (user_id, first_month_start, last_month_end)
            )
            monthly_rows = cursor.fetchall()

            for r in monthly_rows:
                ym = r['ym']
                tx_type = r['type']
                total = float(r['total'])
                if ym in ym_to_index:
                    idx = ym_to_index[ym]
                    if tx_type == 'income':
                        income_by_month[idx] = total
                    elif tx_type == 'expense':
                        expense_by_month[idx] = total

            cursor.close()
        except Exception as e:
            print(f"[Error fetching chart data] {e}")
        finally:
            if conn.is_connected():
                conn.close()

    monthly_data['labels'] = month_labels
    monthly_data['income'] = income_by_month
    monthly_data['expense'] = expense_by_month

    return jsonify({
        'categories': categories_data,
        'monthly': monthly_data
    })




# ---------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------
if __name__ == '__main__':
    # Initialize database and tables on startup
    init_db()
    # Run the Flask development server on port 5000 with auto-reload enabled
    app.run(host='0.0.0.0', port=5000, debug=True)


