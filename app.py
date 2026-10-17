# -------------------- CHART DATA --------------------

@app.route("/api/chart-data")
@login_required
def chart_data():
    uid = session["user_id"]

    # Prepare the latest 6 months.
    months = []
    year = date.today().year
    month = date.today().month

    for _ in range(6):
        months.append((year, month, date(year, month, 1)))

        month -= 1
        if month == 0:
            month = 12
            year -= 1

    months.reverse()

    labels = [
        first_day.strftime("%b %Y")
        for _, _, first_day in months
    ]

    month_keys = [
        (y, m)
        for y, m, _ in months
    ]

    income = [0.0] * len(months)
    expense = [0.0] * len(months)

    categories = {
        "labels": [],
        "data": []
    }

    conn = get_db_connection()

    if not conn:
        return jsonify({
            "categories": categories,
            "monthly": {
                "labels": labels,
                "income": income,
                "expense": expense
            },
            "error": "Database connection failed"
        }), 500

    try:
        cur = conn.cursor(dictionary=True)

        # Expense totals by category.
        cur.execute(
            """
            SELECT category, COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE user_id = %s
              AND LOWER(TRIM(type)) = 'expense'
            GROUP BY category
            ORDER BY total DESC
            """,
            (uid,)
        )

        for row in cur.fetchall():
            categories["labels"].append(row["category"])
            categories["data"].append(float(row["total"] or 0))

        # Monthly income and expenses.
        # Group using YEAR() and MONTH() instead of DATE_FORMAT().
        cur.execute(
            """
            SELECT
                YEAR(`date`) AS transaction_year,
                MONTH(`date`) AS transaction_month,
                LOWER(TRIM(type)) AS type,
                COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE user_id = %s
            GROUP BY
                YEAR(`date`),
                MONTH(`date`),
                LOWER(TRIM(type))
            """,
            (uid,)
        )

        month_index = {
            key: index
            for index, key in enumerate(month_keys)
        }

        for row in cur.fetchall():
            key = (
                int(row["transaction_year"]),
                int(row["transaction_month"])
            )

            if key not in month_index:
                continue

            index = month_index[key]
            tx_type = (row["type"] or "").strip().lower()
            total = float(row["total"] or 0)

            if tx_type == "income":
                income[index] = total
            elif tx_type == "expense":
                expense[index] = total

    except Exception as exc:
        print("[chart data error]", exc)

        return jsonify({
            "error": "Could not load chart data."
        }), 500

    finally:
        conn.close()

    return jsonify({
        "categories": categories,
        "monthly": {
            "labels": labels,
            "income": income,
            "expense": expense
        }
    })
