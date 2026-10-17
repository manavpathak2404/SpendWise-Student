# -------------------- CHART DATA --------------------

@app.route("/api/chart-data")
@login_required
def chart_data():
    uid = session["user_id"]

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

    labels = [d.strftime("%b %Y") for _, _, d in months]

    month_keys = [
        f"{y:04d}-{m:02d}"
        for y, m, _ in months
    ]

    income = [0.0] * 6
    expense = [0.0] * 6
    categories = {"labels": [], "data": []}

    conn = get_db_connection()

    if conn:
        try:
            cur = conn.cursor(dictionary=True)

            # Expense category chart
            cur.execute(
                """
                SELECT category, SUM(amount) AS total
                FROM transactions
                WHERE user_id = %s AND type = 'expense'
                GROUP BY category
                ORDER BY total DESC
                """,
                (uid,)
            )

            for row in cur.fetchall():
                categories["labels"].append(row["category"])
                categories["data"].append(float(row["total"] or 0))

            # Monthly income and expense chart
            start = months[0][2]

            last_year, last_month, _ = months[-1]
            last_day = calendar.monthrange(
                last_year, last_month
            )[1]

            end = date(last_year, last_month, last_day)

            cur.execute(
                """
                SELECT
                    YEAR(date) AS transaction_year,
                    MONTH(date) AS transaction_month,
                    type,
                    SUM(amount) AS total
                FROM transactions
                WHERE user_id = %s
                  AND date >= %s
                  AND date <= %s
                GROUP BY YEAR(date), MONTH(date), type
                """,
                (uid, start, end)
            )

            index = {
                key: i for i, key in enumerate(month_keys)
            }

            for row in cur.fetchall():
                key = (
                    f"{int(row['transaction_year']):04d}-"
                    f"{int(row['transaction_month']):02d}"
                )

                if key in index:
                    i = index[key]
                    amount = float(row["total"] or 0)

                    if row["type"] == "income":
                        income[i] = amount
                    elif row["type"] == "expense":
                        expense[i] = amount

        except Exception as exc:
            app.logger.exception("Chart data error")

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
