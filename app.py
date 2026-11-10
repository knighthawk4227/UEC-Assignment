"""UI for group system notes

    import.py needs to be run first so info is populated
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, g, redirect, render_template, request, url_for

DIR = Path(__file__).resolve().parent
load_dotenv(DIR / ".env")
DB_FILE = DIR / os.getenv("DB_FILE")


app = Flask(__name__)


REVIEWER = "default_reviewer"


# all groups with newest review, unreviewed by default
GROUPS_SQL = """
SELECT g.*,
    COALESCE(r.decision, 'unreviewed') AS status,
    r.reviewer, r.reviewed_at
FROM note_groups g
LEFT JOIN reviews r ON r.id = (SELECT MAX(id) FROM reviews WHERE group_id = g.id)
"""


# data base access

#  check if there is a connection if not connect to DB
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_FILE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


# just close Db at end of request
@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.route("/")
def groups():
    rows = get_db().execute(
        f"{GROUPS_SQL} ORDER BY g.risk_score DESC, g.note_count DESC"
    ).fetchall()
    return render_template("groups.html", groups=rows)

@app.route("/group/<int:group_id>")
def  group_detail(group_id):
    db = get_db()
    group = db.execute(f"{GROUPS_SQL} WHERE g.id = ?", (group_id,)).fetchone()
    if group is None:
        abort(404)

    notes = db.execute("""
        SELECT * FROM notes WHERE group_id = ? ORDER BY date, id limit 500""", (group_id,)).fetchall()
    return render_template("group.html", group=group, notes=notes)


@app.post("/review/<int:group_id>")
def review(group_id):
    decision = request.form.get("decision")
    if decision not in ("approved", "rejected"):
        abort(400)

    db = get_db()
    db.execute("""
        INSERT INTO reviews (group_id, decision, reviewer, reviewed_at) VALUES(?, ?, ?, ?)
        """,
        (group_id, decision, REVIEWER, datetime.now().isoformat()),
    )
    db.commit()
    return (redirect(url_for("groups", _anchor=f"g{group_id}"))) 
