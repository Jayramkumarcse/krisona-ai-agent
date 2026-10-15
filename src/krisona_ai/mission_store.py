"""Local SQLite persistence for missions, progress, and user feedback."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_RECORD_BYTES = 1_000_000
MAX_FEEDBACK_BYTES = 10_000
MAX_COMMENT_LENGTH = 2_000
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")

TASK_STATUSES = {
    "pending", "in_progress", "completed", "blocked", "skipped"
}

ALLOWED_TRANSITIONS = {
    "pending": {"pending", "in_progress", "completed", "blocked", "skipped"},
    "in_progress": {
        "in_progress", "pending", "completed", "blocked", "skipped"
    },
    "blocked": {"blocked", "pending", "in_progress", "skipped"},
    "skipped": {"skipped", "pending"},
    "completed": {"completed"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _checked_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field} has an invalid identifier.")
    return value


def _text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")

    value = value.strip()
    if not value or len(value) > limit:
        raise ValueError(f"{field} must contain 1 to {limit} characters.")

    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError(f"{field} contains prohibited control characters.")

    return value


def _json_text(value: dict[str, Any], limit: int = MAX_RECORD_BYTES) -> str:
    if not isinstance(value, dict):
        raise ValueError("Stored data must be a JSON object.")

    try:
        result = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("Data is not valid JSON-compatible content.") from exc

    if len(result.encode("utf-8")) > limit:
        raise ValueError(f"Stored data exceeds the {limit}-byte limit.")

    return result


class MissionStore:
    """File-backed SQLite store. No network access or cloud sync is used."""

    def __init__(self, db_path: str | Path):
        if not isinstance(db_path, (str, Path)) or not str(db_path).strip():
            raise ValueError("db_path must be a non-empty path.")

        requested = Path(db_path).expanduser()
        if requested.exists() and requested.is_dir():
            raise ValueError("db_path must identify a database file.")

        parent_was_missing = not requested.parent.exists()
        requested.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        if os.name == "posix" and parent_was_missing:
            os.chmod(requested.parent, 0o700)

        self.path = requested.resolve()

        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    data_json TEXT NOT NULL
                        CHECK(length(data_json) <= 1000000)
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL
                        REFERENCES missions(mission_id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    data_json TEXT NOT NULL
                        CHECK(length(data_json) <= 10000)
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT NOT NULL
                        REFERENCES missions(mission_id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    data_json TEXT NOT NULL
                        CHECK(length(data_json) <= 10000)
                );
                """
            )
            connection.commit()
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("PRAGMA synchronous=FULL")

            if os.name == "posix" and self.path.exists():
                os.chmod(self.path, 0o600)

            return connection
        except Exception:
            connection.close()
            raise

    @staticmethod
    def _mission_id(record: dict[str, Any]) -> str:
        mission = record.get("mission", record)
        if not isinstance(mission, dict):
            raise ValueError("record.mission must be an object.")
        return _checked_id(mission.get("mission_id"), "mission_id")

    def save_mission(self, record: dict[str, Any]) -> str:
        """Create a mission record. Existing IDs are never silently replaced."""
        mission_id = self._mission_id(record)
        payload = _json_text(record)
        timestamp = _now()

        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO missions
                        (mission_id, created_at, updated_at, data_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (mission_id, timestamp, timestamp, payload),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Mission ID already exists or violates a database constraint."
            ) from exc
        finally:
            connection.close()

        return mission_id

    def get_mission(self, mission_id: str) -> dict[str, Any] | None:
        mission_id = _checked_id(mission_id, "mission_id")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT data_json FROM missions WHERE mission_id = ?",
                (mission_id,),
            ).fetchone()
            return json.loads(row["data_json"]) if row else None
        finally:
            connection.close()

    def list_missions(self, limit: int = 50) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit must be an integer from 1 to 100.")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be an integer from 1 to 100.")

        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT data_json FROM missions
                ORDER BY updated_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [json.loads(row["data_json"]) for row in rows]
        finally:
            connection.close()

    def record_feedback(
        self, mission_id: str, feedback: dict[str, Any]
    ) -> str:
        mission_id = _checked_id(mission_id, "mission_id")

        if not isinstance(feedback, dict) or not feedback:
            raise ValueError("feedback must be a non-empty object.")

        allowed = {"rating", "helpful", "comments"}
        if set(feedback) - allowed:
            raise ValueError("Feedback contains unsupported fields.")

        clean: dict[str, Any] = {}

        if "rating" in feedback:
            rating = feedback["rating"]
            if isinstance(rating, bool) or not isinstance(rating, int):
                raise ValueError("rating must be an integer from 1 to 5.")
            if not 1 <= rating <= 5:
                raise ValueError("rating must be an integer from 1 to 5.")
            clean["rating"] = rating

        if "helpful" in feedback:
            if not isinstance(feedback["helpful"], bool):
                raise ValueError("helpful must be true or false.")
            clean["helpful"] = feedback["helpful"]

        if "comments" in feedback:
            clean["comments"] = _text(
                feedback["comments"], "comments", MAX_COMMENT_LENGTH
            )

        if not clean:
            raise ValueError("Provide at least one valid feedback field.")

        payload = _json_text(clean, MAX_FEEDBACK_BYTES)
        feedback_id = str(uuid.uuid4())
        timestamp = _now()

        event_payload = _json_text({
            "feedback_id": feedback_id,
            "rating": clean.get("rating"),
            "helpful": clean.get("helpful"),
        }, MAX_FEEDBACK_BYTES)

        connection = self._connect()
        try:
            with connection:
                exists = connection.execute(
                    "SELECT 1 FROM missions WHERE mission_id = ?",
                    (mission_id,),
                ).fetchone()
                if not exists:
                    raise KeyError(f"Unknown mission: {mission_id}")

                connection.execute(
                    """
                    INSERT INTO feedback
                        (feedback_id, mission_id, created_at, data_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (feedback_id, mission_id, timestamp, payload),
                )
                connection.execute(
                    """
                    INSERT INTO events
                        (mission_id, created_at, event_type, data_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (mission_id, timestamp, "feedback_recorded", event_payload),
                )
                connection.execute(
                    "UPDATE missions SET updated_at = ? WHERE mission_id = ?",
                    (timestamp, mission_id),
                )
        finally:
            connection.close()

        return feedback_id

    def list_feedback(self, mission_id: str) -> list[dict[str, Any]]:
        mission_id = _checked_id(mission_id, "mission_id")
        connection = self._connect()
        try:
            exists = connection.execute(
                "SELECT 1 FROM missions WHERE mission_id = ?",
                (mission_id,),
            ).fetchone()
            if not exists:
                raise KeyError(f"Unknown mission: {mission_id}")

            rows = connection.execute(
                """
                SELECT feedback_id, created_at, data_json FROM feedback
                WHERE mission_id = ? ORDER BY created_at, feedback_id
                """,
                (mission_id,),
            ).fetchall()

            return [
                {
                    "feedback_id": row["feedback_id"],
                    "created_at": row["created_at"],
                    "feedback": json.loads(row["data_json"]),
                }
                for row in rows
            ]
        finally:
            connection.close()

    def update_task_status(
        self,
        mission_id: str,
        task_id: str,
        status: str,
        note: str | None = None,
    ) -> dict[str, str]:
        mission_id = _checked_id(mission_id, "mission_id")
        task_id = _checked_id(task_id, "task_id")

        if status not in TASK_STATUSES:
            raise ValueError("Unsupported task status.")

        if note is not None:
            note = _text(note, "note", MAX_COMMENT_LENGTH)

        if status == "completed" and note is None:
            raise ValueError(
                "Completion requires an outcome note as evidence."
            )

        connection = self._connect()
        try:
            with connection:
                row = connection.execute(
                    "SELECT data_json FROM missions WHERE mission_id = ?",
                    (mission_id,),
                ).fetchone()
                if not row:
                    raise KeyError(f"Unknown mission: {mission_id}")

                record = json.loads(row["data_json"])
                plan = record.get("plan")

                if not isinstance(plan, dict) or not isinstance(
                    plan.get("days"), list
                ):
                    raise ValueError("Mission has no stored daily plan.")

                target = None
                for day in plan["days"]:
                    if not isinstance(day, dict):
                        continue
                    for task in day.get("tasks", []):
                        if isinstance(task, dict) and task.get("id") == task_id:
                            target = task
                            break
                    if target is not None:
                        break

                if target is None:
                    raise KeyError(f"Unknown task: {task_id}")

                old_status = target.get("status", "pending")
                if old_status not in ALLOWED_TRANSITIONS:
                    raise ValueError("Stored task has an invalid status.")

                if status not in ALLOWED_TRANSITIONS[old_status]:
                    raise ValueError(
                        f"Cannot change task from {old_status} to {status}."
                    )

                target["status"] = status
                if note is not None:
                    target["result"] = note

                timestamp = _now()
                mission = record.get("mission")
                if isinstance(mission, dict):
                    mission["updated_at"] = timestamp

                payload = _json_text(record)
                event = _json_text({
                    "task_id": task_id,
                    "from_status": old_status,
                    "to_status": status,
                    "note": note,
                }, MAX_FEEDBACK_BYTES)

                connection.execute(
                    """
                    UPDATE missions
                    SET data_json = ?, updated_at = ?
                    WHERE mission_id = ?
                    """,
                    (payload, timestamp, mission_id),
                )
                connection.execute(
                    """
                    INSERT INTO events
                        (mission_id, created_at, event_type, data_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (mission_id, timestamp, "task_status_changed", event),
                )
        finally:
            connection.close()

        return {
            "mission_id": mission_id,
            "task_id": task_id,
            "status": status,
            "updated_at": timestamp,
        }

    def list_events(self, mission_id: str) -> list[dict[str, Any]]:
        mission_id = _checked_id(mission_id, "mission_id")
        connection = self._connect()
        try:
            exists = connection.execute(
                "SELECT 1 FROM missions WHERE mission_id = ?",
                (mission_id,),
            ).fetchone()
            if not exists:
                raise KeyError(f"Unknown mission: {mission_id}")

            rows = connection.execute(
                """
                SELECT event_id, created_at, event_type, data_json
                FROM events WHERE mission_id = ? ORDER BY event_id
                """,
                (mission_id,),
            ).fetchall()

            return [
                {
                    "event_id": row["event_id"],
                    "created_at": row["created_at"],
                    "event_type": row["event_type"],
                    "data": json.loads(row["data_json"]),
                }
                for row in rows
            ]
        finally:
            connection.close()

    def delete_mission(self, mission_id: str) -> bool:
        """Delete a mission and its feedback/events. This cannot be undone."""
        mission_id = _checked_id(mission_id, "mission_id")
        connection = self._connect()
        try:
            with connection:
                cursor = connection.execute(
                    "DELETE FROM missions WHERE mission_id = ?",
                    (mission_id,),
                )
                return cursor.rowcount == 1
        finally:
            connection.close()
