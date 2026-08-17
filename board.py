"""The shared SQLite todo and deliverables board for the multi-agent engineering team.

A top-level goal is assigned to the Orchestrator, which creates step todos for specialist 
workers (Designer, Backend, Frontend, QA). Workers claim their task, mark it in_progress, 
and output deliverables into the 'result' column once complete.

WAL mode + busy_timeout ensure concurrent read/write operations across async execution loop.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

BOARD_PATH = Path(
    os.environ.get("BOARD_PATH", Path(__file__).resolve().parent / "board.sqlite")
)


def _connect(path: Path = BOARD_PATH) -> sqlite3.Connection:
    """Creates a connection with WAL mode and busy timeout enabled for concurrency handling."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def reset_board(path: Path = BOARD_PATH) -> None:
    """Create a fresh, empty board, dropping any existing table."""
    with _connect(path) as conn:
        conn.execute("DROP TABLE IF EXISTS todos")
        conn.execute(
            """CREATE TABLE todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                role TEXT,
                task TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result TEXT NOT NULL DEFAULT ''
            )"""
        )



def add_goal(task: str, path: Path = BOARD_PATH) -> int:
    """Add a top-level goal to the board and return its generated ID."""
    with _connect(path) as conn:
        cur = conn.execute("INSERT INTO todos (task) VALUES (?)", (task,))
        return cur.lastrowid

def add_step(goal_id: int, task: str, role: Optional[str] = None, path: Path = BOARD_PATH) -> int:
    """Add a child step/task under a goal with an optional role, returning its ID."""
    with _connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO todos (parent_id, role, task) VALUES (?, ?, ?)",
            (goal_id, role, task)
        )
        return cur.lastrowid


def get_latest_result_by_role(role: str, path: Path = BOARD_PATH) -> Optional[str]:
    """Retrieves the result string for the most recent completed todo matching a specific role."""
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT result FROM todos WHERE role = ? AND status = 'done' ORDER BY id DESC LIMIT 1",
            (role,),
        ).fetchone()
        return row["result"] if row else None


def list_todos(path: Path = BOARD_PATH) -> List[Dict[str, Any]]:
    """Return every todo on the board, sorted chronologically."""
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT id, parent_id, task, status, result FROM todos ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]


def claim_todo(task_id: int, path: Path = BOARD_PATH) -> None:
    """Mark a todo as in_progress when an agent picks it up."""
    with _connect(path) as conn:
        conn.execute("UPDATE todos SET status = 'in_progress' WHERE id = ?", (task_id,))


def complete_todo(task_id: int, result: str, path: Path = BOARD_PATH) -> None:
    """Mark a todo as done and record its output/deliverable string."""
    with _connect(path) as conn:
        conn.execute(
            "UPDATE todos SET status = 'done', result = ? WHERE id = ?",
            (result, task_id),
        )


def get_latest_result_by_task(task_substr: str, path: Path = BOARD_PATH) -> Optional[str]:
    """Retrieves the result string for the most recent completed todo matching a search string."""
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT result FROM todos WHERE task LIKE ? AND status = 'done' ORDER BY id DESC LIMIT 1",
            (f"%{task_substr}%",),
        ).fetchone()
        return row["result"] if row else None


def show_board(path: Path = BOARD_PATH) -> None:
    """Renders a styled terminal tree of all goals and steps using Rich formatting."""
    todos = list_todos(path)
    lines = []
    for goal in [t for t in todos if t["parent_id"] is None]:
        lines.append(_format(goal, "Goal", ""))
        for step in [t for t in todos if t["parent_id"] == goal["id"]]:
            lines.append(_format(step, "Step", "  "))
    if lines:
        Console().print("\n".join(lines), soft_wrap=True)


def _format(todo: Dict[str, Any], kind: str, indent: str) -> str:
    label = f"{indent}{kind} #{todo['id']}: {todo['task']}"
    if todo["status"] == "done":
        line = f"[green][strike]{label}[/strike][/green]"
        if todo["result"]:
            res_preview = todo['result'][:80].replace("\n", " ")
            line += f"  [dim]=> {res_preview}...[/dim]"
        return line
    if todo["status"] == "in_progress":
        return f"[yellow]{label}[/yellow]"
    return label