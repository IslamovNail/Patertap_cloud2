import os
import sqlite3
from pathlib import Path

import requests
from flask import Flask, g, jsonify, render_template, request

app = Flask(__name__)

DB = Path(os.environ.get("PATERTAP_DB", "instance/patertap.db"))
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
app.config["SECRET_KEY"] = os.environ.get(
    "PATERTAP_SECRET_KEY", "dev-only-change-before-deploy"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings(
    id INTEGER PRIMARY KEY,
    title TEXT,
    city TEXT,
    district TEXT,
    price INTEGER,
    rooms INTEGER,
    description TEXT
);
CREATE TABLE IF NOT EXISTS roommates(
    id INTEGER PRIMARY KEY,
    name TEXT,
    budget INTEGER,
    sleep TEXT,
    cleanliness TEXT,
    social TEXT,
    bio TEXT
);
CREATE TABLE IF NOT EXISTS inquiries(
    id INTEGER PRIMARY KEY,
    listing_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    contact TEXT NOT NULL,
    message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(listing_id) REFERENCES listings(id)
);
"""

SEED_LISTINGS = [
    ("Bright room near university", "Almaty", "Bostandyk", 75000, 1,
     "Furnished room; confirm availability with the owner."),
    ("Shared student apartment", "Almaty", "Auezov", 60000, 2,
     "Shared kitchen; utilities to be agreed."),
    ("Compact studio", "Almaty", "Almaly", 120000, 1,
     "Near transit; confirm all costs before paying."),
    ("Room in a 3-bedroom flat", "Almaty", "Medeu", 85000, 1,
     "Quiet area, two roommates already live there."),
    ("Budget bed in a hostel-style flat", "Almaty", "Turksib", 40000, 1,
     "Basic conditions, good for a short stay."),
    ("Two-room apartment for two", "Almaty", "Bostandyk", 150000, 2,
     "Renovated, close to IITU; split the rent with a roommate."),
    ("Cozy room with balcony", "Astana", "Esil", 90000, 1,
     "Furnished, internet included; confirm details with the owner."),
]

SEED_ROOMMATES = [
    ("Ayan", 80000, "early", "tidy", "quiet",
     "Student who prefers a calm home."),
    ("Dana", 70000, "late", "moderate", "social",
     "Friendly student, often studies outside."),
    ("Mira", 90000, "early", "tidy", "moderate",
     "Likes clear agreements about chores."),
    ("Timur", 60000, "late", "messy", "social",
     "Works evenings, loves hosting friends."),
    ("Aigerim", 100000, "early", "moderate", "quiet",
     "Prefers a quiet place for studying."),
]

SLEEP = ("early", "late")
CLEAN = ("tidy", "moderate", "messy")
SOCIAL = ("quiet", "moderate", "social")


def db():
    if "db" not in g:
        DB.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.executescript(SCHEMA)
        if g.db.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 0:
            g.db.executemany(
                """INSERT INTO listings
                (title, city, district, price, rooms, description)
                VALUES (?, ?, ?, ?, ?, ?)""",
                SEED_LISTINGS,
            )
        if g.db.execute("SELECT COUNT(*) FROM roommates").fetchone()[0] == 0:
            g.db.executemany(
                """INSERT INTO roommates
                (name, budget, sleep, cleanliness, social, bio)
                VALUES (?, ?, ?, ?, ?, ?)""",
                SEED_ROOMMATES,
            )
        g.db.commit()
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    con = g.pop("db", None)
    if con:
        con.close()


def clean(value, limit):
    return str(value or "").strip()[:limit]


def to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@app.get("/")
def home():
    db()
    return render_template("index.html")


@app.get("/healthz")
def health():
    return jsonify(status="ok", service="patertap-cloud")


@app.get("/api/listings")
def listings():
    con = db()
    sql = "SELECT * FROM listings WHERE 1=1"
    args = []
    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    rooms = request.args.get("rooms", type=int)
    if min_price is not None and min_price >= 0:
        sql += " AND price>=?"
        args.append(min_price)
    if max_price is not None and max_price >= 0:
        sql += " AND price<=?"
        args.append(max_price)
    if rooms is not None and rooms > 0:
        sql += " AND rooms=?"
        args.append(rooms)
    order = {
        "price_asc": "price ASC",
        "price_desc": "price DESC",
        "new": "id DESC",
    }.get(request.args.get("sort", "price_asc"), "price ASC")
    rows = [dict(r) for r in con.execute(sql + " ORDER BY " + order, args)]
    city = clean(request.args.get("city"), 60).lower()
    district = clean(request.args.get("district"), 60).lower()
    q = clean(request.args.get("q"), 80).lower()
    if city:
        rows = [r for r in rows if r["city"].lower() == city]
    if district:
        rows = [r for r in rows if district in r["district"].lower()]
    if q:
        rows = [
            r for r in rows
            if q in r["title"].lower() or q in r["description"].lower()
        ]
    return jsonify(rows)


@app.post("/api/listings")
def add_listing():
    con = db()
    data = request.get_json(silent=True) or {}
    title = clean(data.get("title"), 120)
    city = clean(data.get("city"), 60)
    district = clean(data.get("district"), 60)
    description = clean(data.get("description"), 500)
    price = to_int(data.get("price"))
    rooms = to_int(data.get("rooms"), 1)
    if (
        not title or not city or not district
        or price is None or price <= 0 or price > 10000000
        or rooms is None or rooms < 1 or rooms > 10
    ):
        return jsonify(error="Проверь поля: название, город, район, цена и комнаты обязательны."), 400
    cur = con.execute(
        """INSERT INTO listings
        (title, city, district, price, rooms, description)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (title, city, district, price, rooms, description),
    )
    con.commit()
    return jsonify(id=cur.lastrowid), 201


@app.post("/api/inquiries")
def add_inquiry():
    con = db()
    data = request.get_json(silent=True) or {}
    listing_id = to_int(data.get("listing_id"))
    name = clean(data.get("name"), 80)
    contact = clean(data.get("contact"), 120)
    message = clean(data.get("message"), 500)
    if listing_id is None or not name or not contact:
        return jsonify(error="Укажи имя и контакт."), 400
    exists = con.execute(
        "SELECT 1 FROM listings WHERE id=?", (listing_id,)
    ).fetchone()
    if not exists:
        return jsonify(error="Объявление не найдено."), 404
    cur = con.execute(
        """INSERT INTO inquiries (listing_id, name, contact, message)
        VALUES (?, ?, ?, ?)""",
        (listing_id, name, contact, message),
    )
    con.commit()
    return jsonify(id=cur.lastrowid), 201


@app.get("/api/inquiries")
def inquiries():
    con = db()
    rows = con.execute(
        """SELECT i.id, i.name, i.message, i.created_at, l.title AS listing
        FROM inquiries i JOIN listings l ON l.id = i.listing_id
        ORDER BY i.id DESC LIMIT 20"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/api/roommates")
def roommates():
    con = db()
    rows = con.execute("SELECT * FROM roommates ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/roommates")
def add_roommate():
    con = db()
    data = request.get_json(silent=True) or {}
    name = clean(data.get("name"), 60)
    bio = clean(data.get("bio"), 300)
    budget = to_int(data.get("budget"))
    sleep = clean(data.get("sleep"), 20)
    cleanliness = clean(data.get("cleanliness"), 20)
    social = clean(data.get("social"), 20)
    if (
        not name or budget is None or budget <= 0 or budget > 10000000
        or sleep not in SLEEP or cleanliness not in CLEAN
        or social not in SOCIAL
    ):
        return jsonify(error="Проверь поля профиля."), 400
    cur = con.execute(
        """INSERT INTO roommates
        (name, budget, sleep, cleanliness, social, bio)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (name, budget, sleep, cleanliness, social, bio),
    )
    con.commit()
    return jsonify(id=cur.lastrowid), 201


@app.get("/api/matches")
def matches():
    con = db()
    budget = max(1, request.args.get("budget", 80000, type=int))
    sleep = request.args.get("sleep", "early")
    clean_pref = request.args.get("cleanliness", "tidy")
    social = request.args.get("social", "quiet")
    result = []
    for row in con.execute("SELECT * FROM roommates").fetchall():
        person = dict(row)
        score = 100 - min(35, abs(person["budget"] - budget) / budget * 35)
        if person["sleep"] != sleep:
            score -= 20
        if person["cleanliness"] != clean_pref:
            score -= 20
        if person["social"] != social:
            score -= 15
        person["compatibility"] = max(0, round(score))
        result.append(person)
    result.sort(key=lambda x: x["compatibility"], reverse=True)
    return jsonify(result)


@app.get("/api/stats")
def stats():
    con = db()
    total = con.execute(
        """SELECT COUNT(*) AS c, CAST(AVG(price) AS INTEGER) AS avg_price,
        MIN(price) AS min_price, MAX(price) AS max_price FROM listings"""
    ).fetchone()
    districts = con.execute(
        """SELECT district, COUNT(*) AS count,
        CAST(AVG(price) AS INTEGER) AS avg_price
        FROM listings GROUP BY district ORDER BY avg_price"""
    ).fetchall()
    return jsonify(
        listings=total["c"],
        avg_price=total["avg_price"] or 0,
        min_price=total["min_price"] or 0,
        max_price=total["max_price"] or 0,
        roommates=con.execute("SELECT COUNT(*) FROM roommates").fetchone()[0],
        inquiries=con.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0],
        districts=[dict(r) for r in districts],
    )


@app.post("/api/ai")
def ai():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return jsonify(
            error="AI не настроен: добавь GEMINI_API_KEY в переменные окружения сервера."
        ), 503
    prompt = clean((request.get_json(silent=True) or {}).get("prompt"), 1500)
    if not prompt:
        return jsonify(error="Введи вопрос до 1500 символов."), 400
    con = db()
    rows = con.execute(
        "SELECT id, title, city, district, price, rooms FROM listings ORDER BY price LIMIT 15"
    ).fetchall()
    catalog = "\n".join(
        f"#{r['id']} {r['title']}, {r['city']}, {r['district']}, "
        f"{r['price']} KZT/month, rooms: {r['rooms']}"
        for r in rows
    )
    text = (
        "You are PaterTap, a practical student housing assistant in Kazakhstan. "
        "Answer in the language of the user. Be concise and concrete. "
        "Recommend listings only from the catalog below and mention their numbers. "
        "Never claim listings are verified; remind the user to verify ownership "
        "and costs before paying.\n\nCatalog:\n" + catalog +
        "\n\nUser request: " + prompt
    )
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + GEMINI_MODEL + ":generateContent",
            params={"key": key},
            json={"contents": [{"parts": [{"text": text}]}]},
            timeout=25,
        )
        response.raise_for_status()
        answer = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify(answer=answer)
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else 502
        if code == 429:
            return jsonify(error="Лимит запросов Gemini исчерпан, попробуй через минуту."), 429
        return jsonify(error=f"Ошибка Gemini ({code}). Проверь ключ и название модели."), 502
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return jsonify(error="AI временно недоступен. Проверь ключ, модель и квоту."), 502


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
