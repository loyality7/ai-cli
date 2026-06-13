import json
import sqlite3
from datetime import datetime
from typing import Any, Optional
from contextlib import contextmanager
from ai_cli.core.config import CONFIG_DIR

DB_PATH = CONFIG_DIR / "ai_cli.db"

@contextmanager
def db_session():
    """Context manager for SQLite connections. Automatically commits and closes."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db() -> None:
    """Initialize the database tables if they do not exist."""
    with db_session() as conn:
        cursor = conn.cursor()
        
        # 1. Session logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT
            )
        """)
        
        # 2. Doctor reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctor_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                check_name TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)
        
        # 3. Executed commands
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executed_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                command TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                status TEXT NOT NULL,
                output TEXT
            )
        """)

def log_session_action(session_id: str, action: str, details: Any = None) -> None:
    """Log a general session action."""
    timestamp = datetime.now().isoformat()
    details_str = json.dumps(details) if details is not None else None
    with db_session() as conn:
        conn.execute(
            "INSERT INTO session_logs (session_id, timestamp, action, details) VALUES (?, ?, ?, ?)",
            (session_id, timestamp, action, details_str)
        )

def log_doctor_report(
    session_id: str,
    check_name: str,
    status: str,
    message: str
) -> int:
    """Log a system diagnostic check result. Returns the inserted row ID."""
    timestamp = datetime.now().isoformat()
    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO doctor_reports 
            (session_id, timestamp, check_name, status, message) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, timestamp, check_name, status, message)
        )
        return cursor.lastrowid

def log_executed_command(
    session_id: str,
    command: str,
    risk_level: str,
    status: str,
    output: Optional[str] = None
) -> None:
    """Log shell command execution details."""
    timestamp = datetime.now().isoformat()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO executed_commands 
            (session_id, timestamp, command, risk_level, status, output) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, timestamp, command, risk_level, status, output)
        )

def get_latest_doctor_reports() -> list[dict]:
    """Retrieve all logged doctor diagnostic checks from the latest run."""
    with db_session() as conn:
        last_session = conn.execute(
            "SELECT session_id FROM doctor_reports ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        
        if not last_session:
            return []
            
        rows = conn.execute(
            "SELECT * FROM doctor_reports WHERE session_id = ? ORDER BY check_name ASC",
            (last_session["session_id"],)
        ).fetchall()
        return [dict(r) for r in rows]

def get_recent_commands(limit: int = 10) -> list[dict]:
    """Retrieve recent executed commands logs."""
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM executed_commands ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

def get_recent_actions(limit: int = 10) -> list[dict]:
    """Retrieve recent session actions."""
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM session_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

def get_db_stats() -> dict[str, int]:
    """Gather count statistics from the database tables."""
    with db_session() as conn:
        total_actions = conn.execute("SELECT COUNT(*) FROM session_logs").fetchone()[0]
        total_commands = conn.execute("SELECT COUNT(*) FROM executed_commands").fetchone()[0]
        
        last_session = conn.execute(
            "SELECT session_id FROM doctor_reports ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        
        passed_checks = 0
        failed_checks = 0
        
        if last_session:
            passed_checks = conn.execute(
                "SELECT COUNT(*) FROM doctor_reports WHERE session_id = ? AND status = 'passed'",
                (last_session["session_id"],)
            ).fetchone()[0]
            failed_checks = conn.execute(
                "SELECT COUNT(*) FROM doctor_reports WHERE session_id = ? AND status = 'failed'",
                (last_session["session_id"],)
            ).fetchone()[0]
            
        return {
            "total_actions": total_actions,
            "total_commands": total_commands,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
        }

# Automatically initialize tables on import
init_db()
