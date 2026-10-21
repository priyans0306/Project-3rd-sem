"""
Database Layer for Mail AI
Intelligent Business Email Classification
Handles SQLite database connection, table initialization, seeding, and queries.
"""

import os
import sqlite3
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DEFAULT_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emails.db")
DB_FILE = os.path.abspath(os.environ.get("MAIL_AI_DATABASE", DEFAULT_DB_FILE))


def set_database_path(path: str):
    """Set the SQLite file used by subsequent database operations."""
    global DB_FILE
    DB_FILE = os.path.abspath(path)


def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys and dict-like rows enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def database_available() -> bool:
    """Return whether the configured database can execute a basic query."""
    conn = None
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        return True
    except sqlite3.Error:
        return False
    finally:
        if conn is not None:
            conn.close()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _normalize_timestamp(value: Any = None) -> str:
    if value is None or value == "":
        return _utc_timestamp()
    try:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return _utc_timestamp()
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = ? AND name = ?",
        ("table", table_name)
    ).fetchone()
    return row is not None


def _create_tables(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        body TEXT NOT NULL,
        sender TEXT NOT NULL DEFAULT '',
        received_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        recipient TEXT NOT NULL DEFAULT 'support@mailai.enterprise.com',
        status TEXT NOT NULL DEFAULT 'Unread',
        suggested_action TEXT NOT NULL DEFAULT 'PROCESS',
        routed_department TEXT NOT NULL DEFAULT 'General',
        sla TEXT NOT NULL DEFAULT 'Normal',
        key_phrases TEXT NOT NULL DEFAULT '[]'
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS classifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
        model_version TEXT NOT NULL DEFAULT 'unspecified',
        classified_at TEXT NOT NULL,
        priority_confidence REAL,
        risk_confidence REAL,
        UNIQUE (email_id, model_version),
        FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
    )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_received_at ON emails(received_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_created_at ON emails(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_classifications_email_id ON classifications(email_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_classifications_category ON classifications(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_classifications_priority ON classifications(priority)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_classifications_risk ON classifications(risk_level)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_classifications_classified_at ON classifications(classified_at)")


def _migrate_legacy_emails(conn: sqlite3.Connection):
    """Move the former denormalized email/classification rows into both tables."""
    legacy_table = "emails_legacy_migration"
    if not _table_exists(conn, legacy_table):
        return

    rows = conn.execute(f'SELECT * FROM "{legacy_table}"').fetchall()
    for row in rows:
        old = dict(row)
        created_at = _normalize_timestamp(old.get("created_at"))
        received_at = _normalize_timestamp(old.get("received_at") or created_at)
        key_phrases = old.get("key_phrases") or "[]"
        if not isinstance(key_phrases, str):
            key_phrases = json.dumps(key_phrases)

        conn.execute("""
            INSERT INTO emails (
                id, subject, body, sender, received_at, created_at, recipient,
                status, suggested_action, routed_department, sla, key_phrases
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            old["id"], old.get("subject", ""), old.get("body", ""), old.get("sender", ""),
            received_at, created_at, old.get("recipient") or "support@mailai.enterprise.com",
            old.get("status") or "Unread", old.get("suggested_action") or "PROCESS",
            old.get("routed_department") or "General", old.get("sla") or "Normal", key_phrases
        ))

        if all(old.get(key) is not None for key in ("category", "priority", "risk_level")):
            confidence = old.get("category_confidence")
            if confidence is None:
                confidence = 0.0
            priority = old.get("priority") or old.get("urgency") or "Medium"
            conn.execute("""
                INSERT INTO classifications (
                    email_id, category, priority, risk_level, confidence,
                    model_version, classified_at, priority_confidence, risk_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(email_id, model_version) DO NOTHING
            """, (
                old["id"], old["category"], priority, old["risk_level"],
                float(confidence), "legacy-migration", created_at,
                old.get("priority_confidence") or old.get("urgency_confidence"),
                old.get("risk_confidence")
            ))

    conn.execute(f'DROP TABLE "{legacy_table}"')


def init_db():
    """Create the normalized schema and migrate legacy records without demo predictions."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = get_db_connection()
    try:
        with conn:
            if _table_exists(conn, "emails"):
                columns = {
                    row["name"] for row in conn.execute('PRAGMA table_info("emails")')
                }
                if "category" in columns and "received_at" not in columns:
                    conn.execute('ALTER TABLE emails RENAME TO emails_legacy_migration')

            _create_tables(conn)
            _migrate_legacy_emails(conn)
    finally:
        conn.close()


def _insert_email_row(conn: sqlite3.Connection, email_data: Dict[str, Any]) -> int:
    now = _utc_timestamp()
    created_at = _normalize_timestamp(email_data.get("created_at") or now)
    received_at = _normalize_timestamp(email_data.get("received_at") or created_at)
    key_phrases = email_data.get("key_phrases", [])
    if not isinstance(key_phrases, str):
        key_phrases = json.dumps(key_phrases)

    cursor = conn.execute("""
        INSERT INTO emails (
            subject, body, sender, received_at, created_at, recipient, status,
            suggested_action, routed_department, sla, key_phrases
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        email_data.get("subject", ""), email_data.get("body", ""),
        email_data.get("sender", "unknown@sender.com"), received_at, created_at,
        email_data.get("recipient", "support@mailai.enterprise.com"),
        email_data.get("status", "Unread"), email_data.get("suggested_action", "PROCESS"),
        email_data.get("routed_department", "General"), email_data.get("sla", "Normal"), key_phrases
    ))
    return int(cursor.lastrowid)


def _insert_classification_row(
    conn: sqlite3.Connection,
    email_id: int,
    classification: Dict[str, Any]
) -> int:
    priority = classification.get("priority") or classification.get("urgency")
    confidence = classification.get("confidence")
    if confidence is None:
        confidence = classification.get("category_confidence")
    classified_at = _normalize_timestamp(classification.get("classified_at"))
    model_version = str(classification.get("model_version") or "unspecified")
    cursor = conn.execute("""
        INSERT INTO classifications (
            email_id, category, priority, risk_level, confidence, model_version,
            classified_at, priority_confidence, risk_confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(email_id, model_version) DO UPDATE SET
            category = excluded.category,
            priority = excluded.priority,
            risk_level = excluded.risk_level,
            confidence = excluded.confidence,
            classified_at = excluded.classified_at,
            priority_confidence = excluded.priority_confidence,
            risk_confidence = excluded.risk_confidence
    """, (
        email_id, classification["category"], priority, classification["risk_level"],
        float(confidence), model_version, classified_at,
        classification.get("priority_confidence"), classification.get("risk_confidence")
    ))
    row = conn.execute(
        "SELECT id FROM classifications WHERE email_id = ? AND model_version = ?",
        (email_id, model_version)
    ).fetchone()
    return int(row["id"])


def replace_demo_data(email_records: List[Dict[str, Any]]):
    """Atomically replace all inbox rows using already-classified records."""
    if not email_records:
        raise ValueError("At least one classified demo email is required.")

    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM emails")
            for email_data in email_records:
                email_id = _insert_email_row(conn, email_data)
                _insert_classification_row(conn, email_id, email_data)
    finally:
        conn.close()


def insert_email(email_data: Dict[str, Any]) -> int:
    """Atomically insert an email and, when present, its classification."""
    conn = get_db_connection()
    try:
        with conn:
            email_id = _insert_email_row(conn, email_data)
            if all(key in email_data for key in ("category", "priority", "risk_level")):
                _insert_classification_row(conn, email_id, email_data)
        return email_id
    finally:
        conn.close()


def add_classification(email_id: int, classification: Dict[str, Any]) -> int:
    """Add or replace a model-version result for an existing email."""
    conn = get_db_connection()
    try:
        with conn:
            exists = conn.execute("SELECT 1 FROM emails WHERE id = ?", (email_id,)).fetchone()
            if exists is None:
                raise ValueError(f"Email with ID {email_id} does not exist.")
            return _insert_classification_row(conn, email_id, classification)
    finally:
        conn.close()


def get_classification_history(email_id: int) -> List[Dict[str, Any]]:
    """Return all distinct model-version classifications for an email."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM classifications WHERE email_id = ? "
            "ORDER BY classified_at ASC, id ASC",
            (email_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_legacy_or_unclassified_emails(model_version: str) -> List[Dict[str, Any]]:
    """Find rows needing current-model results after legacy migration or startup."""
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT e.* FROM emails AS e
            WHERE (
                NOT EXISTS (
                    SELECT 1 FROM classifications AS current
                    WHERE current.email_id = e.id AND current.model_version = ?
                )
                AND (
                    NOT EXISTS (
                        SELECT 1 FROM classifications AS any_result
                        WHERE any_result.email_id = e.id
                    )
                    OR EXISTS (
                        SELECT 1 FROM classifications AS legacy
                        WHERE legacy.email_id = e.id
                          AND legacy.model_version IN ('legacy-migration', 'demo-seed')
                    )
                )
            )
            ORDER BY e.id
        """, (model_version,)).fetchall()
        return [_decode_email(row) for row in rows]
    finally:
        conn.close()


_EMAIL_SELECT = """
    SELECT
        e.*,
        c.category,
        c.priority,
        c.priority AS urgency,
        c.risk_level,
        c.confidence,
        c.confidence AS category_confidence,
        COALESCE(c.priority_confidence, c.confidence) AS priority_confidence,
        COALESCE(c.priority_confidence, c.confidence) AS urgency_confidence,
        COALESCE(c.risk_confidence, c.confidence) AS risk_confidence,
        c.model_version,
        c.classified_at
    FROM emails AS e
    LEFT JOIN classifications AS c ON c.id = (
        SELECT latest.id
        FROM classifications AS latest
        WHERE latest.email_id = e.id
        ORDER BY latest.classified_at DESC, latest.id DESC
        LIMIT 1
    )
"""


def _email_filters(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    urgency: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> tuple[str, list]:
    conditions = []
    params = []
    if category:
        conditions.append("c.category = ?")
        params.append(category)
    priority_filter = priority or urgency
    if priority_filter:
        conditions.append("c.priority = ?")
        params.append(priority_filter)
    if risk_level:
        conditions.append("c.risk_level = ?")
        params.append(risk_level)
    if status:
        conditions.append("e.status = ?")
        params.append(status)
    if search:
        conditions.append("(e.subject LIKE ? OR e.body LIKE ? OR e.sender LIKE ?)")
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term])
    return (" WHERE " + " AND ".join(conditions) if conditions else "", params)


def _decode_email(row: sqlite3.Row) -> Dict[str, Any]:
    item = dict(row)
    try:
        item["key_phrases"] = json.loads(item["key_phrases"]) if item.get("key_phrases") else []
    except (TypeError, json.JSONDecodeError):
        item["key_phrases"] = []
    return item


def get_emails(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    urgency: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve emails and their latest classification using optional filters."""
    conn = get_db_connection()
    where, params = _email_filters(category, priority, urgency, risk_level, status, search)
    try:
        rows = conn.execute(
            _EMAIL_SELECT + where + " ORDER BY e.id DESC LIMIT ? OFFSET ?",
            [*params, limit, offset]
        ).fetchall()
        return [_decode_email(row) for row in rows]
    finally:
        conn.close()


def count_emails(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    urgency: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> int:
    """Count emails matching the same filters used by get_emails."""
    conn = get_db_connection()
    where, params = _email_filters(category, priority, urgency, risk_level, status, search)
    query = (
        "SELECT COUNT(*) FROM emails AS e "
        "LEFT JOIN classifications AS c ON c.id = ("
        "SELECT latest.id FROM classifications AS latest "
        "WHERE latest.email_id = e.id "
        "ORDER BY latest.classified_at DESC, latest.id DESC LIMIT 1)" + where
    )
    try:
        row = conn.execute(query, params).fetchone()
        return int(row[0])
    finally:
        conn.close()


def get_email_by_id(email_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve one email with its latest classification, if it has one."""
    conn = get_db_connection()
    try:
        row = conn.execute(_EMAIL_SELECT + " WHERE e.id = ?", (email_id,)).fetchone()
        return _decode_email(row) if row else None
    finally:
        conn.close()


def update_email_status(email_id: int, status: str) -> bool:
    """Updates status of an email."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute("UPDATE emails SET status = ? WHERE id = ?", (status, email_id))
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_email(email_id: int) -> bool:
    """Delete an email and cascade-delete its classification history."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute("DELETE FROM emails WHERE id = ?", (email_id,))
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_dashboard_metrics() -> Dict[str, Any]:
    """Compute dashboard aggregates from each email's latest classification."""
    conn = get_db_connection()
    try:
        latest = """
            FROM emails AS e
            LEFT JOIN classifications AS c ON c.id = (
                SELECT latest.id FROM classifications AS latest
                WHERE latest.email_id = e.id
                ORDER BY latest.classified_at DESC, latest.id DESC
                LIMIT 1
            )
        """
        total_emails = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
        classified_emails = conn.execute(
            "SELECT COUNT(DISTINCT email_id) FROM classifications"
        ).fetchone()[0]
        critical_emails = conn.execute(
            "SELECT COUNT(*) " + latest + " WHERE c.priority IN ('High', 'Urgent') OR c.risk_level = 'High'"
        ).fetchone()[0]
        high_risk_emails = conn.execute(
            "SELECT COUNT(*) " + latest + " WHERE c.risk_level = 'High'"
        ).fetchone()[0]

        def grouped_counts(column: str) -> Dict[str, int]:
            rows = conn.execute(
                f"SELECT c.{column}, COUNT(*) {latest} "
                f"WHERE c.{column} IS NOT NULL GROUP BY c.{column}"
            ).fetchall()
            return {str(row[0]): int(row[1]) for row in rows}

        category_counts = grouped_counts("category")
        priority_counts = grouped_counts("priority")
        risk_counts = grouped_counts("risk_level")
        urgent_emails = priority_counts.get("Urgent", 0)
        status_rows = conn.execute(
            "SELECT status, COUNT(*) FROM emails GROUP BY status"
        ).fetchall()
        recent_rows = conn.execute(
            "SELECT e.id, e.sender, e.subject, c.category, c.priority, "
            "c.priority AS urgency, c.risk_level, e.status, e.created_at " + latest +
            " ORDER BY e.id DESC LIMIT 5"
        ).fetchall()

        return {
            "total_emails": int(total_emails),
            "classified_emails": int(classified_emails),
            "urgent_emails": int(urgent_emails),
            "critical_emails": int(critical_emails),
            "high_risk_emails": int(high_risk_emails),
            "category_counts": category_counts,
            "priority_counts": priority_counts,
            "urgency_counts": priority_counts,
            "risk_counts": risk_counts,
            "status_counts": {str(row[0]): int(row[1]) for row in status_rows},
            "recent_emails": [dict(row) for row in recent_rows]
        }
    finally:
        conn.close()
