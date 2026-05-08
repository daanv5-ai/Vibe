import sqlite3
import logging
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "memory.db"

logger = logging.getLogger(__name__)


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database and create tables if they don't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, key)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
        """)
        conn.commit()
    logger.info("Memory DB initialized at %s", DB_PATH)


def save_memory(user_id: int, category: str, key: str, value: str):
    """
    Upsert a memory entry.
    category: 'fact' | 'preference' | 'goal' | 'note'
    """
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO memories (user_id, category, key, value, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                updated_at = excluded.updated_at
        """, (user_id, category, key, value, now, now))
        conn.commit()
    logger.info("Saved memory [%s] %s = %s", category, key, value)


def get_memories(user_id: int) -> list[dict]:
    """Return all memories for a user as a list of dicts."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT category, key, value FROM memories WHERE user_id = ? ORDER BY category, key",
            (user_id,)
        ).fetchall()
    return [dict(row) for row in rows]


def get_memories_as_text(user_id: int) -> str:
    """
    Return a formatted string of all memories to inject into the system prompt.
    Returns empty string if no memories exist.
    """
    memories = get_memories(user_id)
    if not memories:
        return ""

    grouped: dict[str, list[str]] = {}
    for m in memories:
        grouped.setdefault(m["category"], []).append(f"  - {m['key']}: {m['value']}")

    lines = ["## What you remember about Daan:"]
    for category, items in grouped.items():
        lines.append(f"\n### {category.capitalize()}s")
        lines.extend(items)

    return "\n".join(lines)


def delete_memory(user_id: int, key: str) -> bool:
    """Delete a specific memory by key. Returns True if something was deleted."""
    with _get_conn() as conn:
        cursor = conn.execute(
            "DELETE FROM memories WHERE user_id = ? AND key = ?",
            (user_id, key)
        )
        conn.commit()
    return cursor.rowcount > 0


def clear_all_memories(user_id: int):
    """Wipe all memories for a user."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
        conn.commit()
    logger.info("Cleared all memories for user %s", user_id)


def save_conversation_turn(user_id: int, role: str, content: str):
    """
    Persist a conversation turn to the DB.
    role: 'user' | 'model'
    """
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, role, content, now)
        )
        conn.commit()


def get_recent_conversation(user_id: int, limit: int = 20) -> list[dict]:
    """
    Retrieve the most recent N conversation turns for context reconstruction.
    """
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT role, content, timestamp FROM conversations
               WHERE user_id = ?
               ORDER BY id DESC LIMIT ?""",
            (user_id, limit)
        ).fetchall()
    # Return in chronological order
    return [dict(row) for row in reversed(rows)]
