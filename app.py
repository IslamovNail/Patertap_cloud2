
import os
import sqlite3
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request, g

app = Flask(__name__)

DB = Path(os.environ.get("PATERTAP_DB", "instance/patertap.db"))
app.config["SECRET_KEY"] = os.environ.get(
    "PATERTAP_SECRET_KEY", "dev-only-change-before-deploy"
)


def db():
    if "db" not in g:
        DB.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row

        g.db.executescript("""
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
        """)

        if g.db.execute("SELECT COUNT(*) FROM listings").fetchone()[0] == 0:
            g.db.executemany(
                """INSERT INTO listings
                (title, city, district, price, rooms, description)
                VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    ("Bright room near university", "Almaty", "Bostandyk", 75000, 1,
                     "Furnished room; confirm availability with the owner."),
                    ("Shared student apartment", "Almaty", "Auezov", 60000, 2,
                     "Shared kitchen; utilities to be agreed."),
                    ("Compact studio", "Almaty", "Almaly", 120000, 1,
                     "Near transit; confirm all costs before paying.")
                ]
            )

        if g.db.execute("SELECT COUNT(*) FROM roommates").fetchone()[0] == 0:
            g.db.executemany(
                """INSERT INTO roommates
                (name, budget, sleep, cleanliness, social, bio)
                VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    ("Ayan", 80000, "early", "tidy", "quiet",
                     "Student who prefers a calm home."),
                    ("Dana", 70000, "late", "moderate", "social",
                     "Friendly student, often studies outside."),
                    ("Mira", 90000, "early", "tidy", "moderate",
                     "Likes clear agreements about chores.")
                ]
            )

        g.db.commit()

    return g.db


@app.teardown_appcontext
def close_db(_exc):
    con = g.pop("db", None)
    if con:
        con.close()


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
    city = request.args.get("city", "").strip()
    price = request.args.get("max_price", type=int)

    sql = "SELECT * FROM listings WHERE 1=1"
    args = []

    if city:
        sql += " AND lower(city)=lower(?)"
        args.append(city)

    if price is not None and price >= 0:
        sql += " AND price<=?"
        args.append(price)

    rows = con.execute(sql + " ORDER BY price", args).fetchall()
    return jsonify([dict(row) for row in rows])


@app.get("/api/matches")
def matches():
    con = db()
    budget = max(1, request.args.get("budget", 80000, type=int))
    sleep = request.args.get("sleep", "early")
    clean = request.args.get("cleanliness", "tidy")
    social = request.args.get("social", "quiet")

    result = []

    for row in con.execute("SELECT * FROM roommates").fetchall():
        person = dict(row)

        score = 100 - min(
            35, abs(person["budget"] - budget) / budget * 35
        )

        if person["sleep"] != sleep:
            score -= 20
        if person["cleanliness"] != clean:
            score -= 20
        if person["social"] != social:
            score -= 15

        person["compatibility"] = max(0, round(score))
        result.append(person)

    result.sort(key=lambda x: x["compatibility"], reverse=True)
    return jsonify(result)


@app.post("/api/ai")
def ai():
    key = os.environ.get("GEMINI_API_KEY")

    if not key:
        return jsonify(
            error="AI is not configured yet. Add GEMINI_API_KEY on the server."
        ), 503

    prompt = str(
        (request.get_json(silent=True) or {}).get("prompt", "")
    ).strip()

    if not prompt or len(prompt) > 1500:
        return jsonify(
            error="Enter a question up to 1500 characters."
        ), 400

    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            params={"key": key},
            json={
                "contents": [{
                    "parts": [{
                        "text": (
                            "You are PaterTap, a practical housing search "
                            "assistant. Do not claim listings are verified. "
                            "Remind users to verify ownership and costs "
                            "before paying. User request: " + prompt
                        )
                    }]
                }]
            },
            timeout=20
        )

        response.raise_for_status()
        data = response.json()
        answer = data["candidates"][0]["content"]["parts"][0]["text"]

        return jsonify(answer=answer)

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError
    ):
        return jsonify(
            error="AI provider error. Check the key, model availability and quota."
        ), 502


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False
  )
  
