import sqlite3
from datetime import datetime

DB_FILE = "tasks.db"


def _connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            deadline TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )"""
    )
    return conn


def add_task(title: str, deadline: str) -> dict:
    """Create a task. Deadline must be in YYYY-MM-DD format."""
    title = (title or "").strip()
    if not title:
        return {"success": False, "error": "Title cannot be empty."}

    try:
        date = datetime.strptime(deadline, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return {"success": False, "error": "Deadline must be in YYYY-MM-DD format."}

    conn = _connect()
    cur = conn.execute(
        "INSERT INTO tasks (title, deadline) VALUES (?, ?)",
        (title, date.isoformat()),
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return {"success": True, "task_id": task_id, "title": title, "deadline": date.isoformat()}


def list_tasks(status: str = "pending") -> dict:
    """List tasks sorted by deadline. status: 'pending', 'done' or 'all'."""
    if status not in ("pending", "done", "all"):
        return {"success": False, "error": "status must be 'pending', 'done' or 'all'."}

    conn = _connect()
    if status == "all":
        rows = conn.execute("SELECT * FROM tasks ORDER BY deadline").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY deadline", (status,)
        ).fetchall()
    conn.close()
    return {"success": True, "tasks": [dict(r) for r in rows]}


def complete_task(task_id: int) -> dict:
    """Mark a task as done."""
    try:
        task_id = int(task_id)
    except (ValueError, TypeError):
        return {"success": False, "error": "task_id must be a number."}

    conn = _connect()
    cur = conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
    conn.commit()
    changed = cur.rowcount
    conn.close()

    if changed == 0:
        return {"success": False, "error": f"No task found with id {task_id}."}
    return {"success": True, "task_id": task_id, "status": "done"}


if __name__ == "__main__":
    # Quick self-test
    print(add_task("Physics assignment", "2026-10-30"))
    print(add_task("", "2026-10-30"))            # should fail: empty title
    print(add_task("Lab report", "30-10-2026"))  # should fail: wrong date format
    print(list_tasks())
    print(complete_task(1))
    print(complete_task(999))                    # should fail: no such task
    print(list_tasks("all"))