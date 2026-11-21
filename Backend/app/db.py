import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def get_db_path(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "", 1)
    return database_url


class Database:
    def __init__(self, database_url: str) -> None:
        self.db_path = get_db_path(database_url)
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    system_prompt TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def ping(self) -> bool:
        with self._connect() as conn:
            conn.execute("SELECT 1")
        return True

    def upsert_session_prompt(
        self, session_id: str, system_prompt: Optional[str]
    ) -> Optional[str]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT system_prompt FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO sessions (session_id, system_prompt, created_at) VALUES (?, ?, ?)",
                    (session_id, system_prompt, now),
                )
                conn.commit()
                return system_prompt
            if system_prompt is not None:
                conn.execute(
                    "UPDATE sessions SET system_prompt = ? WHERE session_id = ?",
                    (system_prompt, session_id),
                )
                conn.commit()
                return system_prompt
            return row["system_prompt"]

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content, metadata FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        result = []
        for row in rows:
            item: Dict[str, Any] = {"role": row["role"], "content": row["content"]}
            if row["role"] == "assistant" and row["metadata"]:
                item["metadata"] = json.loads(row["metadata"])
            result.append(item)
        return result

    def save_turn(
        self,
        session_id: str,
        user_content: str,
        assistant_content: str,
        metadata: Dict[str, Any],
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, metadata, created_at) VALUES (?, 'user', ?, NULL, ?)",
                (session_id, user_content, now),
            )
            conn.execute(
                "INSERT INTO messages (session_id, role, content, metadata, created_at) VALUES (?, 'assistant', ?, ?, ?)",
                (session_id, assistant_content, json.dumps(metadata), now),
            )
            conn.commit()