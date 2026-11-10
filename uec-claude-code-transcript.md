# UEC Assignment: building the import and review app

Selected prompts from a Claude Code session, November 9–10, 2026, after the Claude.ai UI was generated. Prompts are Mitchell's, copied as typed; responses are Claude's, shortened. Prompts already in `uec-chat-transcript.md` are left out.

---

## Prompt 1

is there a way to just put the name of the file in the .env and then have it load based on your current file path ?

## Response 1

Yes. Store just the file name in `.env`, then join it onto the folder the script lives in using `Path(__file__)`:

**`.env`**
```
FILE_NAME=file.xlsx
```

**`import.py`**
```python
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent   # the folder import.py is in
load_dotenv(BASE_DIR / ".env")

file = BASE_DIR / os.getenv("FILE_NAME")
df = pd.read_excel(file)
```

`__file__` is the path of the script itself, so `BASE_DIR` is always the project folder. It doesn't matter which directory you run the script from. Passing `BASE_DIR / ".env"` to `load_dotenv` means it also finds the `.env` file from anywhere.

If you'd rather look in whatever folder you're in when you run the script, use `Path.cwd()` instead. That breaks if you run the script from somewhere else, so the script's folder is usually the better choice.

---

## Prompt 2

alright I need you to guide me through setting this up I want to make a sqlite db with a notes table and a group table the groups will be not set right away until I run the script through all note rows which the notes will get a FK to a group PK and the groups will start null

## Response 2

I tested this setup on your spreadsheet in a scratch database. It loads all 100,000 notes, each with an empty group at first. The grouping pass then sorts them into 1,905 groups, and the whole run takes about 11 seconds.

### The two tables

```python
SCHEMA = """
CREATE TABLE IF NOT EXISTS note_groups (
    id          INTEGER PRIMARY KEY,
    name        TEXT,
    context     TEXT,
    start_date  TEXT,
    end_date    TEXT,
    note_count  INTEGER
);

CREATE TABLE IF NOT EXISTS notes (
    id                  INTEGER PRIMARY KEY,
    date                TEXT NOT NULL,
    name                TEXT NOT NULL,
    ...
    group_id            INTEGER REFERENCES note_groups(id)   -- starts NULL
);

CREATE INDEX IF NOT EXISTS idx_notes_group ON notes(group_id);
"""

con = sqlite3.connect(DB_FILE)
con.execute("PRAGMA foreign_keys = ON")
con.executescript(SCHEMA)
```

- **`group_id`** is the foreign key to the groups table. It has no `NOT NULL`, so every note starts with `NULL` until the grouping pass fills it in.
- **The groups table is called `note_groups`** because `group` is a reserved word in SQL.
- **`PRAGMA foreign_keys = ON`:** SQLite ignores foreign keys unless you turn them on, on every connection.

### Load the spreadsheet

Rename the spreadsheet columns to the database names, read Old/New Value as text (so `037` keeps its leading zero), and convert the ID columns to `Int64` so blanks don't turn `416` into `416.0`. Then `df.to_sql("notes", con, if_exists="append", index=False)`. Use `"append"`, not `"replace"`: `"replace"` would drop your table and make its own, without the foreign key.

### The grouping pass

```python
rows = con.execute(
    "SELECT id, date, name, context FROM notes ORDER BY name, context, date, id"
).fetchall()

prev = None
updates = []
for note_id, date, name, context in rows:
    t = datetime.fromisoformat(date)

    new_group = (
        prev is None              # first note
        or name != prev[0]        # different user
        or context != prev[1]     # different context
        or t - prev[2] > GAP      # too long since the last note
    )
    if new_group:
        cur = con.execute(
            "INSERT INTO note_groups (name, context, start_date) VALUES (?, ?, ?)",
            (name, context, date),
        )
        group_id = cur.lastrowid   # the new group's id

    updates.append((group_id, note_id))
    prev = (name, context, t)

con.executemany("UPDATE notes SET group_id = ? WHERE id = ?", updates)

# fill in each group's end time and how many notes it has
con.execute("""
    UPDATE note_groups SET
        end_date   = (SELECT MAX(date) FROM notes WHERE group_id = note_groups.id),
        note_count = (SELECT COUNT(*)  FROM notes WHERE group_id = note_groups.id)
""")
con.commit()
```

- **Sorting by user, then context, then date** puts notes that belong together next to each other, so you only ever compare a note with the one just before it.
- **`lastrowid`** gives you the id SQLite just assigned to the new group, which you then store on each of its notes.
- **`executemany`** saves all 100,000 group assignments in one call.

The "same user, same context, less than `GAP` minutes apart" rule is a starting point. The biggest group is one Map/Reduce run by User A, with 22,971 notes in 49 minutes, so you may want to split on `record_type` too.

---

## Prompt 3

*Pasted: the earlier Claude.ai conversation (grouping key advice, gap in code vs. a table, pandas import, Google Sheets export).*

Based on all this does it make sense so far for grouping and other

## Response 3

Yes, and your script already follows most of that advice. I checked each point against your `notes.db` and the spreadsheet.

**Already done:** Date and Type left out of the key, file order as the tie-breaker, dates stored as `YYYY-MM-DD HH:MM` text, gap set in code, IDs kept as whole numbers, table created first and then appended, one group per note with no join table.

Two of the advice's worries don't apply to your data. Reading the `.xlsx` takes about 5 seconds, not 20–40, so there's no need to switch to CSV. And the longest group lasts 49 minutes, with none over an hour.

**Worth changing now:**

1. **Add `record_type` to the grouping key.** Right now 137 of your groups mix different record types, like an invoice edit and a vendor bank change landing in the same group. Adding it takes you from 1,905 groups to 2,144.
2. **Add an index on `(record_type, record_id)`** for the drill-down and for "other groups that touched this record".

**Optional / later:**

- **Per-context gaps:** with record type in the key, 5 min gives 2,144 groups and 15 min gives 1,904. Start with 5.
- **Literal "None"/"NA" values:** none of the old/new values in this sample were turned into blanks by pandas, but `keep_default_na=False, na_values=[""]` protects you if the real data has them.
- **If you switch to a Google Sheets CSV:** add `*.csv` to `.gitignore`, and check the date format, because `datetime.fromisoformat` will crash on `11/9/2026 14:05:00`.

---

## Prompt 4

What does create index do for the main stuff ?

## Response 4

An index is a sorted lookup list that SQLite keeps alongside a table, like the index at the back of a book. Without one, finding the notes for group 500 means checking all 100,000 rows. With an index on `group_id`, SQLite jumps straight to the matching rows.

I timed it on a copy of your `notes.db`:

| Query | No index | With index |
|---|---|---|
| All notes in one group (`WHERE group_id = 500`) | 12 ms | 0.04 ms |
| One record's history (`WHERE record_type = ... AND record_id = ...`) | 11 ms | 0.02 ms |
| Your `UPDATE note_groups SET end_date..., note_count...` | **41.6 seconds** | **0.02 seconds** |

- **`idx_notes_group`** matters most right now. Your `end_date`/`note_count` update runs two lookups per group, about 3,800 lookups in total. Without the index, each one reads all 100k notes.
- **`idx_notes_record ON notes(record_type, record_id)`** helps when you search by `record_type`, or by both, but not by `record_id` alone. That fits your data, because record IDs only mean something within a record type.
- **The primary key gets one automatically,** which is why `UPDATE notes SET group_id = ? WHERE id = ?` is fast.
- **Indexes aren't free.** Each one uses disk space and slows writes slightly, so only index columns you actually search by.

To see whether a query uses one, put `EXPLAIN QUERY PLAN` in front of it. `SCAN notes` means it reads every row; `SEARCH notes USING INDEX ...` means it uses the index.

---

## Prompt 5

If it was a different set of data / I added new data wouldn't I want it to drop both then run again ?

## Response 5

Yes, and your script already clears both tables with `DELETE FROM`, so each run rebuilds everything from whatever file `.env` points to.

| | `DELETE FROM notes` (what you have) | `DROP TABLE notes` |
|---|---|---|
| Removes the rows | ✓ | ✓ |
| Removes the table and its indexes | ✗ | ✓ Recreated from `SCHEMA` |
| Picks up changes to `SCHEMA` | ✗ This is why you had to `rm notes.db` after the comma fix | ✓ Automatically |

Since everything in these tables comes from the spreadsheet, dropping them loses nothing:

```python
con.execute("DROP TABLE IF EXISTS notes")        # notes first
con.execute("DROP TABLE IF EXISTS note_groups")
con.executescript(SCHEMA)
```

**The order matters:** with foreign keys on, SQLite won't let you remove groups while notes still point to them.

**Adding new data:** rebuilding only works if the new file has all the rows, old and new. If you only get the new rows, add them to one combined spreadsheet and rebuild. That also handles a session that starts at the end of the old data and continues into the new data.

**Once you have reviews:** never drop the reviews table casually, because it's the only thing not rebuilt from the spreadsheet, and group ids can change on a rebuild.

---

## Prompt 6

Prev is non sets it to true then it goes to make a new group ? but then wouldn't it never go into any of the others

## Response 6

`prev is None` is only true once, for the very first note. The last line of the loop sets `prev = (name, context, t)`, so from the second note on it's never `None` again.

Python checks `or` conditions from left to right and stops at the first one that's true:

- **1st note:** `prev is None` is true, so Python stops there and makes a new group. The other checks are skipped, which is good, because `prev[0]` would crash on `None`.
- **Every later note:** `prev is None` is false, so Python moves on to check name, then context, then the gap.

That's also why `prev is None` has to come first. If it came later, the first note would crash with `TypeError: 'NoneType' object is not subscriptable`.

| Note | name, context, time | `prev` before this note | First check that's true | Result |
|---|---|---|---|---|
| 1 | A, CSV, 09:00 | `None` | `prev is None` | **new group 1** |
| 2 | A, CSV, 09:03 | (A, CSV, 09:00) | none (3 min ≤ 5) | joins group 1 |
| 3 | A, CSV, 09:20 | (A, CSV, 09:03) | gap: 17 min > 5 | **new group 2** |
| 4 | A, UI, 09:21 | (A, CSV, 09:20) | `context != prev[1]` | **new group 3** |
| 5 | B, UI, 09:22 | (A, UI, 09:21) | `name != prev[0]` | **new group 4** |

---

## Prompt 7

So what I want to do to conserve time is not make a login logout just have it set so that it always thinks approve comes from default reviewer. So What I want is you to walk me through adding the render and use of the home page and then also adding the default user to the code maybe hard coded for this case

## Response 7

I built this on copies of your `import.py` and `app.py` and tested every step. The home page lists all 1,905 groups as "unreviewed", Approve saves `approved by default_reviewer` and brings you back to the same row, and re-importing still works when reviews exist.

### Step 1: `import.py` creates the `reviews` table too

```sql
CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY,
    group_id    INTEGER NOT NULL REFERENCES note_groups(id),
    decision    TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    reviewer    TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    notes       TEXT
);
```

Drop it first, above the other two `DROP` lines. Once reviews exist, `DROP TABLE note_groups` would otherwise fail with a foreign key error. The trade-off is that re-importing clears all reviews, which is honest, since they'd point at regrouped notes anyway.

### Step 2: `app.py`

```python
# no logins, so every decision is saved under this name
REVIEWER = "default_reviewer"

# every group plus its newest review; no review yet means "unreviewed"
GROUPS_SQL = """
SELECT g.*,
       COALESCE(r.decision, 'unreviewed') AS status,
       r.reviewer, r.reviewed_at
FROM note_groups g
LEFT JOIN reviews r ON r.id = (SELECT MAX(id) FROM reviews WHERE group_id = g.id)
"""


@app.route("/")
def groups():
    rows = get_db().execute(
        f"{GROUPS_SQL} ORDER BY g.risk_score DESC, g.note_count DESC"
    ).fetchall()
    return render_template("groups.html", groups=rows)


@app.post("/review/<int:group_id>")
def review(group_id):
    decision = request.form.get("decision")
    if decision not in ("approved", "rejected"):
        abort(400)

    db = get_db()
    db.execute(
        "INSERT INTO reviews (group_id, decision, reviewer, reviewed_at) VALUES (?, ?, ?, ?)",
        (group_id, decision, REVIEWER, datetime.now().isoformat(sep=" ", timespec="seconds")),
    )
    db.commit()
    return redirect(url_for("groups", _anchor=f"g{group_id}"))
```

- **`LEFT JOIN`** keeps every group, even ones with no review, and `COALESCE` turns "no review" into `'unreviewed'`.
- **`SELECT MAX(id) ...`** picks each group's newest review.
- **`redirect(...)`** sends the browser back to the home page, so refreshing won't post the review again. `_anchor` jumps back to that row instead of the top of 1,905 groups.

### Step 3: `templates/groups.html`

One table row per group, with the status and one form holding both buttons:

```html
<tr id="g{{ group.id }}">
  ...
  <td>{{ group.status }} {% if group.reviewer %}by {{ group.reviewer }}{% endif %}</td>
  <td>
    <form method="post" action="{{ url_for('review', group_id=group.id) }}">
      <button name="decision" value="approved">Approve</button>
      <button name="decision" value="rejected">Reject</button>
    </form>
  </td>
</tr>
```

The browser only sends the `value` of the button that was clicked, so the route gets `approved` or `rejected`.

### Step 4: Run it

```sh
.venv/bin/python import.py
.venv/bin/python -m flask --app app run --debug
```
