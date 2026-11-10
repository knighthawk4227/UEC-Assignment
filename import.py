import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv


DIR = Path(__file__).resolve().parent
load_dotenv(DIR / ".env")
DB_FILE = DIR / os.getenv("DB_FILE")
FILE = DIR / os.getenv("FILE")
# current folder

# join folder dir with file name
GAP = timedelta(minutes=int(os.getenv("GAP")))

SCHEMA = """
CREATE TABLE IF NOT EXISTS note_groups (
    id              INTEGER PRIMARY KEY,
    name            TEXT,
    context         TEXT,
    start_date      TEXT,
    end_date        TEXT,
    note_count      INTEGER,
    risk_score      INTEGER
);

CREATE TABLE IF NOT EXISTS notes (
    id                      INTEGER PRIMARY KEY,
    date                    TEXT NOT NULL,
    name                    TEXT NOT NULL,
    role                    TEXT,
    context                 TEXT,
    record_type             TEXT,
    record_id               INTEGER,
    record                  TEXT,
    type                    TEXT NOT NULL,
    field                   TEXT NOT NULL,
    old_value               TEXT,
    new_value               TEXT,
    line_id                 INTEGER,
    line_transaction_id     INTEGER,
    group_id                INTEGER REFERENCES note_groups(id)
);

CREATE INDEX IF NOT EXISTS idx_notes_group ON notes(group_id);
CREATE INDEX IF NOT EXISTS idx_notes_record ON notes(record_type, record_id);

CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY,
    group_id        INTEGER NOT NULL REFERENCES note_groups(id)
    decision        TEXT NOT NULL CHECK(decision IN ('approved', 'rejected')),
    reviewer        TEXT NOT NULL,
    reviewed_at     TEXT NOT NULL,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_reviews_groups ON reviews(group_id, id);

"""

con = sqlite3.connect(DB_FILE)
con.execute("PRAGMA foreign_keys = ON")
# drop tables if they exist
con.execute("DROP TABLE IF EXISTS reviews")
con.execute("DROP TABLE IF EXISTS notes")
con.execute("DROP TABLE IF EXISTS note_groups")
con.executescript(SCHEMA)

COLUMNS = {
    "Date": "date", "Name": "name", "Role": "role", "Context": "context",
    "Record Type": "record_type", "Record ID": "record_id", "Record": "record",
     "Type": "type", "Field": "field", "Old Value": "old_value",
     "New Value": "new_value","Line Id": "line_id", "Line Transaction Id": "line_transaction_id",
}


df = pd.read_excel(FILE, dtype={"Old Value" : str, "New Value": str})
df = df.rename(columns=COLUMNS)

# ensure to handle nums,
for col in ["record_id", "line_id", "line_transaction_id"]:
    df[col] = df[col].astype("Int64")

# don't accidentally get rid of schema table
df.to_sql("notes", con, if_exists="append", index=False)
con.commit()

rows = con.execute(
    "SELECT id, date, name, context FROM notes ORDER BY name, context, date, id"
).fetchall()

# first iter
prev = None
updates = []
for note_id, date, name, context in rows:
    t = datetime.fromisoformat(date)

    # check all cases, different user did something, different context, too long since last note
    new_group = (
        prev is None
        or name != prev[0]
        or context != prev[1]
        or t - prev[2] > GAP
    )
    if new_group:
        cur = con.execute(
            "INSERT INTO note_groups(name, context, start_date) VALUES (?, ?, ?)",
            (name, context, date),
        )
        group_id = cur.lastrowid

    updates.append((group_id, note_id))
    prev = (name, context, t)

# all 100k notes to their respective group
con.executemany("UPDATE notes SET group_id = ? WHERE id = ?", updates)

# fill group end time and total note, also go through and set risk based off type
con.execute("""
    UPDATE note_groups SET
        end_date = (SELECT MAX(date) FROM notes WHERE group_id = note_groups.id),
        note_count = (SELECT COUNT(*) FROM notes WHERE group_id = note_groups.id),
        risk_score = (
            SELECT MAX(CASE
                WHEN field LIKE '%password%'           THEN 5
                WHEN field LIKE '%bank%'
                  OR field LIKE '%routing%'
                  OR field LIKE '%iban%'
                  OR field LIKE '%swift%'
                  OR field LIKE '%eft%'
                  OR field LIKE '%account number%'
                  OR field LIKE '%payment method%'     THEN 5
                WHEN record_type LIKE '%script%'
                  OR record_type LIKE '%workflow%'
                  OR record_type LIKE '%plugin%'       THEN 4
                WHEN role IS NULL                      THEN 3
                WHEN context IS NULL                   THEN 2
                ELSE 0
            END)
            FROM notes WHERE group_id = note_groups.id
        )""")
con.commit()

# print # of rows in notes
print(con.execute("SELECT COUNT(*), COUNT(group_id) FROM notes").fetchone())
# print # of groups made
print(con.execute("SELECT COUNT(*) FROM note_groups").fetchone())
con.close()
