# SpendWise Student — Personal Finance & Budget Tracker

**SpendWise Student** is a complete, responsive personal finance and budgeting web application designed specifically for college students. It enables students to track allowances, scholarships, freelance earnings, canteen expenses, books, lifestyle costs, and view visual analytics with budget summaries.

---

## 🛠️ Technology Stack (Exact Stack)

This project strictly follows standard, framework-free foundational web technologies:
- **Frontend**: HTML5, CSS3, Bootstrap 5 (CDN), Vanilla JavaScript (ES6+), Chart.js (v4.4 CDN)
- **Backend**: Python 3 + Flask
- **Database**: MySQL (MariaDB compatible, via `mysql-connector-python`)
- **Authentication**: Flask Sessions + `werkzeug.security` password hashing (PBKDF2/SHA256)

---

## 📁 Project Directory Structure

```text
spendwise_student/
├── app.py                     # Main Flask web application (routes, auth guards, APIs)
├── db.py                      # MySQL connection pool & automatic table initializer
├── schema.sql                 # SQL schema script defining tables and constraints
├── requirements.txt           # Python library dependencies
├── README.md                  # Setup documentation & Diploma Viva Voce preparation guide
│
├── static/
│   ├── css/
│   │   └── style.css          # Custom styling, student color theme, responsive rules (down to 375px)
│   └── js/
│       ├── main.js            # Dynamic category filtering, inline validation, delete modals
│       └── charts.js          # Chart.js initialization for Doughnut and 6-Month Bar charts
│
└── templates/
    ├── base.html              # Base layout with navbar, flash alerts, delete modal, footer
    ├── dashboard.html         # Main dashboard with 3 summary cards, charts, recent transactions
    ├── transactions.html      # Paginated full transactions table with filters and sorting
    ├── transaction_form.html  # Unified form for /add and /edit/<id> with ₹ prefix
    └── auth/
        ├── login.html         # Login page with inline validation (no alert popups)
        └── signup.html        # Registration page with inline validation
```

---

## 🗄️ Database Architecture & Schema

The database is named `spendwise_db` and uses the **InnoDB** storage engine for ACID compliance and foreign key support.

### 1. `users` Table
Stores student account details and hashed credentials.

| Field | Data Type | Key / Constraint | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT` | `PRIMARY KEY AUTO_INCREMENT` | Unique identifier for each student |
| `name` | `VARCHAR(100)` | `NOT NULL` | Student full name |
| `email` | `VARCHAR(150)` | `NOT NULL UNIQUE` | Login email address |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Salted SHA-256 / PBKDF2 hashed password |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Account registration timestamp |

### 2. `transactions` Table
Stores all individual financial records associated with each user.

| Field | Data Type | Key / Constraint | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INT` | `PRIMARY KEY AUTO_INCREMENT` | Unique transaction ID |
| `user_id` | `INT` | `FOREIGN KEY (users.id) ON DELETE CASCADE` | Links record to owner |
| `title` | `VARCHAR(100)` | `NOT NULL` | Description of expense / income |
| `amount` | `DECIMAL(10,2)` | `NOT NULL` | Monetary value (> 0.00) |
| `type` | `ENUM('income','expense')` | `NOT NULL` | Transaction category direction |
| `category` | `VARCHAR(50)` | `NOT NULL` | Dynamically filtered category |
| `date` | `DATE` | `NOT NULL` | Date of transaction |
| `created_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | System creation timestamp |

> **Index**: `INDEX idx_user_date (user_id, date)` speeds up historical queries and monthly aggregation.

---

## 🚀 Local Setup & Installation Instructions

### 1. Prerequisites
- **Python 3.10+** (Python 3.10, 3.11, 3.12, 3.13, or 3.14)
- **MySQL Server** (via **XAMPP**, **WampServer**, or standalone MySQL Community Server)

### 2. Start MySQL
- Open **XAMPP Control Panel** and click **Start** next to **MySQL** (port 3306).

### 3. Clone or Navigate to Project Directory
```powershell
cd spendwise_student
```

### 4. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 5. Initialize the Database
Run the automated initialization script to create the database and tables:
```powershell
python db.py
```
*(You will see `[Database] Initialization completed successfully.`)*

### 6. Run the Application
```powershell
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🎓 Diploma Semester 3 Viva Voce Preparation Guide

This section is prepared specifically to help students confidently answer examiner questions during practical exams and project viva.

### Q1: What architecture pattern does this application follow?
**Answer:** The project follows the **MVC (Model-View-Controller)** architectural pattern:
- **Model**: Database layer in `db.py` and MySQL tables (`users`, `transactions`).
- **View**: HTML5 templates in `templates/` styled with Bootstrap 5 and rendered by the Jinja2 template engine.
- **Controller**: Python Flask routes in `app.py` that handle incoming HTTP requests, perform validation, execute database queries, and return responses.

---

### Q2: What is SQL Injection, and how did you prevent it?
**Answer:** 
- **SQL Injection (SQLi)** occurs when malicious user input is concatenated directly into a SQL query string (e.g. `' OR 1=1 --`), altering the query's logic.
- **Prevention**: In our application, we **never** use raw string concatenation or f-strings for query values. We strictly use **parameterized queries** with `%s` placeholders:
  ```python
  cursor.execute(
      "SELECT * FROM transactions WHERE user_id = %s AND type = %s",
      (user_id, tx_type)
  )
  ```
  The database driver transmits data and code separately, ensuring user inputs are treated solely as literal values, completely neutralizing injection attempts.

---

### Q3: Why don't you store plain-text passwords in the database?
**Answer:** Storing plain text passwords is a severe security vulnerability. If a database is breached, attacker immediately gains access to all user accounts.
- We use `werkzeug.security.generate_password_hash()` which generates a cryptographically secure, salted hash (PBKDF2/SHA256).
- When a user logs in, `werkzeug.security.check_password_hash(hash, password)` verifies the password without ever storing or decrypting the original password.

---

### Q4: How does session-based authentication work in Flask?
**Answer:**
1. When a student logs in successfully, Flask creates a cryptographically signed cookie stored on the client browser (`session['user_id'] = user['id']`).
2. Subsequent requests send this session cookie back to the server.
3. The custom `@login_required` decorator checks `if 'user_id' not in session` before allowing access to protected routes like `/`, `/transactions`, `/add`, and `/edit`.
4. Logging out calls `session.clear()`, invalidating the session.

---

### Q5: How is user data isolation guaranteed?
**Answer:** Every database query that fetches, modifies, or deletes transaction records enforces the `WHERE user_id = %s` filter. Even if a user attempts to manually navigate to `/edit/5` or send a `POST` to `/delete/5`, the query will only find and modify records where `id = 5 AND user_id = %s`. If the record belongs to another user, 0 rows are affected and access is denied.

---

### Q6: How does the category dropdown dynamically update when changing Transaction Type?
**Answer:** In `static/js/main.js`, we maintain JavaScript arrays for income and expense categories. We attach a `'change'` event listener to the Transaction Type `<select id="type">` dropdown. When the student toggles between "Income" and "Expense", JavaScript clears the `<select id="category">` options and dynamically injects the appropriate `<option>` elements using the DOM API without requiring a page reload.

---

### Q7: How are the charts rendered?
**Answer:**
1. When the dashboard loads, `static/js/charts.js` issues an asynchronous HTTP `GET` request using the JavaScript `fetch('/api/chart-data')` API.
2. The Flask route queries MySQL:
   - Groups expenses by category for the Doughnut Chart.
   - Calculates monthly sums for Income and Expenses across the last 6 calendar months for the Bar Chart.
3. Flask returns a JSON response.
4. The client initializes **Chart.js**, rendering interactive canvas charts with custom tooltips formatted in Indian Rupees.

---

### Q8: How is the Indian Currency formatted (₹1,20,000.00)?
**Answer:** Unlike western numbering (where commas separate every 3 digits, like `120,000`), the Indian numbering system groups the last 3 digits, and subsequent digits in groups of 2 (e.g. `1,20,000.00`).
- In Python, we created a custom Jinja filter `inr` in `app.py` using modulo arithmetic and string grouping.
- In JavaScript, `formatINR()` in `static/js/main.js` formats chart tooltips identically.
