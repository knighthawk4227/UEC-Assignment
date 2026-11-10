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


APP_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY, 
   group_id     INTEGER NOT NULL REFERENCES note_groups(id),
  decision      TEXT NOT NULL,
  reviewer      TEXT NOT NULL,
  reviewed_at   TEXT NOT NULL,
  notes         TEXT,
  note_count    INTEGER
  );

CREATE INDEX IF NOT EXISTS idx_reviews_group ON reviews(group_id, id);
  """


GROUPS_SQL = """
SELECT g.*,
    r.reviewer, r.reviewed_at, r.notes AS review_notes
FROM note_groups g
LEFT JOIN reviews r on r.id = (SELECT MAX(id) FROM reviews WHERE group_id = g.id)
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

# connect to DB and run script for displaying reviews
def init_db():
    with sqlite3.connect(DB_FILE) as con:
        con.executescript(APP_SCHEMA)

@app.route("/")
def groups():
    rows = get_db().execute("""
        SELECT * FROM note_groups ORDER BY risk_score DESC, note_count DESC"""
    ).fetchall()
    return render_template("groups.html", groups=rows)


    