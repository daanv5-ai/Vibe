import sqlite3
import os
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

DB_PATH = "tasks.db"
AMSTERDAM_TZ = pytz.timezone("Europe/Amsterdam")

def init_db():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    project_name TEXT,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            ''')
            conn.commit()
            logger.info("Tasks DB initialized.")
    except Exception as e:
        logger.error(f"Error initializing tasks db: {e}")

def add_task(user_id: int, title: str, project_name: str = None) -> str:
    try:
        now = datetime.now(AMSTERDAM_TZ).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (user_id, project_name, title, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
                (user_id, project_name, title, now)
            )
            task_id = cursor.lastrowid
            conn.commit()
            return f"Task added with ID {task_id}: {title} (Project: {project_name})"
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        return f"Error adding task: {e}"

def list_tasks(user_id: int, status: str = 'pending', project_name: str = None) -> str:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            query = "SELECT id, title, project_name, status, created_at FROM tasks WHERE user_id = ?"
            params = [user_id]
            if status and status.lower() != 'all':
                query += " AND status = ?"
                params.append(status.lower())
            if project_name:
                query += " AND project_name = ?"
                params.append(project_name)
                
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            if not rows:
                return "No tasks found matching criteria."
            
            res = ["Current tasks:"]
            for row in rows:
                p_name = row[2] if row[2] else "Uncategorized"
                res.append(f"[{row[0]}] {row[1]} (Project: {p_name}) - {row[3]}")
            return "\n".join(res)
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return f"Error listing tasks: {e}"

def update_task_status(user_id: int, task_id: int, status: str) -> str:
    try:
        now = datetime.now(AMSTERDAM_TZ).isoformat()
        completed_at = now if status.lower() == 'completed' else None
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Verify ownership
            cursor.execute("SELECT id FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
            if not cursor.fetchone():
                return f"Task {task_id} not found or you don't have permission to modify it."
                
            cursor.execute(
                "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ? AND user_id = ?",
                (status.lower(), completed_at, task_id, user_id)
            )
            conn.commit()
            return f"Task {task_id} marked as '{status.lower()}'."
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        return f"Error updating task: {e}"
