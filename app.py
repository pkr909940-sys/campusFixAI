from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os
from datetime import datetime
from difflib import SequenceMatcher

app = Flask(__name__)
DB = os.getenv("DATABASE_PATH", "campusfix.db")

CATEGORY_RULES = {
    "IT / Network": ["wifi", "wi-fi", "internet", "computer", "pc", "laptop", "projector", "printer", "network", "software", "keyboard", "mouse"],
    "Electrical": ["fan", "light", "electricity", "switch", "socket", "ac", "air conditioner", "power", "bulb"],
    "Maintenance": ["water", "leak", "leakage", "washroom", "toilet", "door", "window", "chair", "desk", "cleaning", "floor", "tap"],
    "Library": ["book", "library", "issue", "return", "card"],
    "Safety": ["fire", "smoke", "unsafe", "emergency", "accident", "security", "fight", "harassment", "exit", "lock"],
    "Academic": ["teacher", "class", "lecture", "attendance", "exam", "timetable", "marks", "assignment"]
}

DEPARTMENT = {
    "IT / Network": "IT Department",
    "Electrical": "Electrical Department",
    "Maintenance": "Maintenance Team",
    "Library": "Library Department",
    "Safety": "Administration / Security",
    "Academic": "Academic Department",
    "Other": "Administration"
}

HIGH_WORDS = ["emergency", "fire", "smoke", "accident", "unsafe", "security", "harassment", "electric shock", "sparking", "locked exit"]
MEDIUM_WORDS = ["not working", "broken", "leak", "leakage", "wifi", "internet", "projector", "computer", "fan", "water"]

def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        location TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        department TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        created_at TEXT NOT NULL
    )""")
    con.commit()
    con.close()

def classify(description):
    text = description.lower()
    scores = {cat: sum(1 for word in words if word in text) for cat, words in CATEGORY_RULES.items()}
    category = max(scores, key=scores.get)
    if scores[category] == 0:
        category = "Other"

    if any(word in text for word in HIGH_WORDS):
        priority = "High"
    elif any(word in text for word in MEDIUM_WORDS):
        priority = "Medium"
    else:
        priority = "Low"

    return category, priority, DEPARTMENT.get(category, "Administration")

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_similar(description, location):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT * FROM complaints WHERE location = ? ORDER BY id DESC LIMIT 100",
        (location,)
    ).fetchall()
    con.close()
    matches = []
    for row in rows:
        score = similarity(description, row["description"])
        if score >= 0.48:
            matches.append((row, score))
    return matches

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("name", "Anonymous").strip() or "Anonymous"
    location = request.form.get("location", "").strip()
    description = request.form.get("description", "").strip()

    if not location or not description:
        return redirect(url_for("index", error="Please fill location and description."))

    category, priority, department = classify(description)
    matches = find_similar(description, location)

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""INSERT INTO complaints
        (name, location, description, category, priority, department, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)""",
        (name, location, description, category, priority, department,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    new_id = cur.lastrowid
    con.commit()
    con.close()

    return render_template(
        "result.html",
        complaint_id=new_id,
        name=name,
        location=location,
        description=description,
        category=category,
        priority=priority,
        department=department,
        similar_count=len(matches)
    )

@app.route("/admin")
def admin():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    complaints = con.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()
    con.close()
    return render_template("admin.html", complaints=complaints)

@app.route("/api/stats")
def stats():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    total = cur.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    high = cur.execute("SELECT COUNT(*) FROM complaints WHERE priority='High'").fetchone()[0]
    medium = cur.execute("SELECT COUNT(*) FROM complaints WHERE priority='Medium'").fetchone()[0]
    low = cur.execute("SELECT COUNT(*) FROM complaints WHERE priority='Low'").fetchone()[0]
    resolved = cur.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0]
    pending = total - resolved

    category_rows = cur.execute(
        "SELECT category, COUNT(*) c FROM complaints GROUP BY category ORDER BY c DESC"
    ).fetchall()
    location_rows = cur.execute(
        "SELECT location, COUNT(*) c FROM complaints GROUP BY location ORDER BY c DESC LIMIT 5"
    ).fetchall()
    con.close()

    return jsonify({
        "total": total, "high": high, "medium": medium, "low": low,
        "resolved": resolved, "pending": pending,
        "categories": [{"name": r[0], "count": r[1]} for r in category_rows],
        "locations": [{"name": r[0], "count": r[1]} for r in location_rows]
    })

@app.route("/update/<int:complaint_id>", methods=["POST"])
def update(complaint_id):
    status = request.form.get("status", "Pending")
    if status not in ["Pending", "In Progress", "Resolved"]:
        status = "Pending"
    con = sqlite3.connect(DB)
    con.execute("UPDATE complaints SET status=? WHERE id=?", (status, complaint_id))
    con.commit()
    con.close()
    return redirect(url_for("admin"))

@app.route("/seed")
def seed():
    samples = [
        ("Rahul", "Block B", "WiFi is not working in Block B for two days."),
        ("Aman", "Block B", "Block B wifi not working since yesterday."),
        ("Priya", "Block B", "Internet is down in Block B."),
        ("Neha", "Room 203", "Projector is not working in room 203."),
        ("Rohit", "Room 203", "Room 203 projector is broken."),
        ("Kajal", "Lab 1", "Five computers are not working in the computer lab."),
        ("Shivam", "Washroom 2", "There is water leakage near the washroom tap."),
        ("Anjali", "Main Gate", "Emergency exit is locked and this is a safety issue."),
    ]
    con = sqlite3.connect(DB)
    for name, loc, desc in samples:
        category, priority, dept = classify(desc)
        con.execute("""INSERT INTO complaints
        (name, location, description, category, priority, department, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)""",
        (name, loc, desc, category, priority, dept, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    con.commit()
    con.close()
    return redirect(url_for("admin"))

@app.route("/clear")
def clear():
    con = sqlite3.connect(DB)
    con.execute("DELETE FROM complaints")
    con.commit()
    con.close()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
