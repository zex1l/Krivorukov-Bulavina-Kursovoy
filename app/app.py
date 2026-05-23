from datetime import datetime
import calendar
import sqlite3
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "expenses.db"

app = Flask(__name__)
app.config["DATABASE"] = str(DATABASE_PATH)
app.config["SECRET_KEY"] = "SECRET_KEY"

DEFAULT_CATEGORIES = [
    ("Еда", 0),
    ("Транспорт", 0),
    ("Кофе", 3000),
    ("Развлечения", 7000),
    ("Здоровье", 0),
    ("Другое", 0),
]

ALERTS = [
    {
        "category": "Кофе",
        "amount": 3000,
        "message": "Тратишь слишком много на кофе… как всегда.",
    },
    {
        "category": "Развлечения",
        "amount": 7000,
        "message": "Выделяешь много на развлечения в этом месяце — подумай о бюджете.",
    },
]


def get_db():
    db = getattr(g, "db", None)
    if db is None:
        db = g.db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
    return db


def close_db(e=None):
    db = getattr(g, "db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    with app.open_resource("schema.sql", mode="r", encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()
    db.close()


def ensure_default_categories():
    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    cursor = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='categories'"
    )
    if cursor.fetchone() is None:
        db.execute(
            "CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, monthly_limit REAL NOT NULL DEFAULT 0)"
        )
        db.commit()

    count = db.execute("SELECT COUNT(1) FROM categories").fetchone()[0]
    if count == 0:
        db.executemany(
            "INSERT INTO categories (name, monthly_limit) VALUES (?, ?)",
            DEFAULT_CATEGORIES,
        )
        db.commit()
    db.close()


def ensure_db():
    if not DATABASE_PATH.exists():
        init_db()
    ensure_default_categories()


def get_month_bounds(year: int, month: int):
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start.isoformat(), end.isoformat()


def get_day_bounds(year: int, month: int, day: int):
    last_day = calendar.monthrange(year, month)[1]
    safe_day = min(max(1, day), last_day)
    start = datetime(year, month, safe_day, 0, 0)
    end = datetime(year, month, safe_day, 23, 59, 59, 999999)
    return start.isoformat(), end.isoformat()


def format_date(value):
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return value


def format_datetime_local(value):
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%dT%H:%M")
    except Exception:
        return value


app.add_template_filter(format_date, "format_date")
app.add_template_filter(format_datetime_local, "datetime_local")


def fetch_expenses(year=None, month=None):
    db = get_db()
    query = """SELECT e.id, e.date, e.amount, e.category_id, e.note, c.name as category
               FROM expenses e
               JOIN categories c ON e.category_id = c.id"""
    params = []
    if year and month:
        start, end = get_month_bounds(year, month)
        query += " WHERE e.date >= ? AND e.date < ?"
        params.extend([start, end])
    query += " ORDER BY e.date DESC"
    return db.execute(query, params).fetchall()


def fetch_categories():
    db = get_db()
    return db.execute("SELECT * FROM categories ORDER BY name").fetchall()


def fetch_expense(expense_id):
    db = get_db()
    return db.execute(
        """SELECT e.id, e.date, e.amount, e.category_id, e.note, c.name as category
           FROM expenses e
           JOIN categories c ON e.category_id = c.id
           WHERE e.id = ?""", 
        (expense_id,)
    ).fetchone()


def category_exists(category_id):
    db = get_db()
    return db.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone() is not None


def monthly_report(year, month):
    db = get_db()
    start, end = get_month_bounds(year, month)
    rows = db.execute(
        """SELECT c.name, SUM(e.amount) AS total 
           FROM expenses e
           JOIN categories c ON e.category_id = c.id
           WHERE e.date >= ? AND e.date < ?
           GROUP BY e.category_id, c.name""",
        (start, end),
    ).fetchall()
    return {row["name"]: row["total"] for row in rows}


def daily_report(year, month, day):
    db = get_db()
    start, end = get_day_bounds(year, month, day)
    rows = db.execute(
        """SELECT c.name, SUM(e.amount) AS total 
           FROM expenses e
           JOIN categories c ON e.category_id = c.id
           WHERE e.date >= ? AND e.date <= ?
           GROUP BY e.category_id, c.name""",
        (start, end),
    ).fetchall()
    return {row["name"]: row["total"] for row in rows}


def compute_alerts(report, categories):
    messages = []
    for alert in ALERTS:
        total = report.get(alert["category"], 0)
        if total >= alert["amount"]:
            messages.append(alert["message"])

    for category in categories:
        limit = category["monthly_limit"]
        if limit and report.get(category["name"], 0) > limit:
            overrun = report[category["name"]] - limit
            messages.append(
                f"Лимит по категории {category['name']} превышен на {overrun:.2f} ₽."
            )
    return messages


@app.teardown_appcontext
def teardown_db(exception):
    close_db(exception)


@app.route("/", methods=["GET"])
def index():
    today = datetime.now()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)

    categories = fetch_categories()
    expenses = fetch_expenses(year, month)
    report = monthly_report(year, month)
    total = sum(report.values())
    alerts = compute_alerts(report, categories)

    return render_template(
        "index.html",
        categories=categories,
        expenses=expenses,
        year=year,
        month=month,
        report=report,
        total=total,
        alerts=alerts,
        active_page="home",
    )


@app.route("/add", methods=["POST"])
def add_expense():
    try:
        amount = float(request.form["amount"])
    except (ValueError, KeyError):
        return redirect(url_for("index"))

    try:
        category_id = int(request.form.get("category_id", ""))
    except (ValueError, KeyError):
        # Если категория не указана, возьмём первую категорию
        db = get_db()
        first_cat = db.execute("SELECT id FROM categories LIMIT 1").fetchone()
        category_id = first_cat["id"] if first_cat else None
        if category_id is None:
            return redirect(url_for("index"))

    if not category_exists(category_id):
        return redirect(url_for("index"))

    note = request.form.get("note", "").strip()
    date_str = request.form.get("date") or datetime.now().strftime("%Y-%m-%dT%H:%M")

    db = get_db()
    db.execute(
        "INSERT INTO expenses (date, amount, category_id, note) VALUES (?, ?, ?, ?)",
        (date_str, amount, category_id, note),
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/categories", methods=["GET"])
def categories_page():
    categories = fetch_categories()

    return render_template(
        "categories.html",
        categories=categories,
        active_page="categories",
    )


@app.route("/categories/add", methods=["POST"])
def add_category():
    name = request.form.get("name", "").strip()
    limit = request.form.get("limit", "0")
    try:
        limit_value = float(limit or 0)
    except ValueError:
        limit_value = 0

    if name:
        db = get_db()
        existing = db.execute(
            "SELECT id FROM categories WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE categories SET monthly_limit = ? WHERE id = ?",
                (limit_value, existing["id"]),
            )
        else:
            db.execute(
                "INSERT INTO categories (name, monthly_limit) VALUES (?, ?)",
                (name, limit_value),
            )
        db.commit()

    return redirect(url_for("categories_page"))


@app.route("/categories/delete", methods=["POST"])
def delete_category():
    category_id = request.form.get("category_id", type=int)
    if category_id:
        db = get_db()
        db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        db.commit()
    return redirect(url_for("categories_page"))


@app.route("/expense/<int:expense_id>/delete", methods=["POST"])
def delete_expense(expense_id):
    db = get_db()
    db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    db.commit()
    return redirect(url_for("index"))


@app.route("/expense/<int:expense_id>/edit", methods=["GET"])
def edit_expense(expense_id):
    expense = fetch_expense(expense_id)
    if expense is None:
        return redirect(url_for("index"))

    categories = fetch_categories()
    return render_template(
        "edit_expense.html",
        expense=expense,
        categories=categories,
        active_page="home",
    )


@app.route("/expense/<int:expense_id>/update", methods=["POST"])
def update_expense(expense_id):
    try:
        amount = float(request.form["amount"])
    except (ValueError, KeyError):
        return redirect(url_for("edit_expense", expense_id=expense_id))

    try:
        category_id = int(request.form.get("category_id", ""))
    except (ValueError, KeyError):
        return redirect(url_for("edit_expense", expense_id=expense_id))

    if not category_exists(category_id):
        return redirect(url_for("edit_expense", expense_id=expense_id))

    note = request.form.get("note", "").strip()
    date_str = request.form.get("date") or datetime.now().strftime("%Y-%m-%dT%H:%M")

    db = get_db()
    db.execute(
        "UPDATE expenses SET date = ?, amount = ?, category_id = ?, note = ? WHERE id = ?",
        (date_str, amount, category_id, note, expense_id),
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/categories/update", methods=["POST"])
def update_category():
    category_id = request.form.get("category_id", type=int)
    limit = request.form.get("limit", "0")
    try:
        limit_value = float(limit or 0)
    except ValueError:
        limit_value = 0

    if category_id:
        db = get_db()
        db.execute(
            "UPDATE categories SET monthly_limit = ? WHERE id = ?",
            (limit_value, category_id),
        )
        db.commit()

    return redirect(url_for("categories_page"))


@app.route("/report", methods=["GET"])
def report_page():
    categories = fetch_categories()
    today = datetime.now()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    report = monthly_report(year, month)
    total = sum(report.values())
    alerts = compute_alerts(report, categories)

    return render_template(
        "report.html",
        categories=categories,
        report=report,
        total=total,
        alerts=alerts,
        year=year,
        month=month,
        active_page="report",
    )


@app.route("/daily", methods=["GET"])
def daily_page():
    today = datetime.now()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    day = request.args.get("day", today.day, type=int)
    categories = fetch_categories()
    expenses = fetch_expenses(year, month)
    report = daily_report(year, month, day)
    total = sum(report.values())

    return render_template(
        "daily.html",
        categories=categories,
        expenses=[expense for expense in expenses if expense["date"] >= get_day_bounds(year, month, day)[0] and expense["date"] <= get_day_bounds(year, month, day)[1]],
        report=report,
        total=total,
        year=year,
        month=month,
        day=day,
        active_page="daily",
    )


if __name__ == "__main__":
    ensure_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
