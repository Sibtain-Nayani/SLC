import sqlite3
import json
import datetime
from typing import List, Dict, Any

CREATE_TABLES_SQL = [
"""
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT UNIQUE,
    raw_text TEXT,
    summary TEXT,
    last_updated TEXT
);
""",
"""
CREATE TABLE IF NOT EXISTS quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    questions_json TEXT,
    created_at TEXT
);
""",
"""
CREATE TABLE IF NOT EXISTS quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    results_json TEXT,
    score REAL,
    taken_at TEXT
);
""",
"""
CREATE TABLE IF NOT EXISTS repetition_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT UNIQUE,
    interval_days INTEGER,
    easiness REAL,
    repetition_count INTEGER,
    next_review_date TEXT
);
"""
]

class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        c = self._conn.cursor()
        for sql in CREATE_TABLES_SQL:
            c.execute(sql)
        self._conn.commit()

    # Notes
    def insert_or_update_note(self, topic: str, raw_text: str, summary: str):
        now = datetime.datetime.utcnow().isoformat()
        c = self._conn.cursor()
        c.execute("SELECT id FROM notes WHERE topic = ?", (topic,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE notes SET raw_text = ?, summary = ?, last_updated = ? WHERE topic = ?", (raw_text, summary, now, topic))
        else:
            c.execute("INSERT INTO notes (topic, raw_text, summary, last_updated) VALUES (?, ?, ?, ?)", (topic, raw_text, summary, now))
        self._conn.commit()

    def get_note_by_topic(self, topic: str):
        c = self._conn.cursor()
        c.execute("SELECT * FROM notes WHERE topic = ?", (topic,))
        row = c.fetchone()
        if not row:
            return None
        return {"topic": row["topic"], "raw_text": row["raw_text"], "summary": row["summary"], "last_updated": row["last_updated"]}

    def get_all_topics(self) -> List[str]:
        c = self._conn.cursor()
        c.execute("SELECT topic FROM notes ORDER BY last_updated DESC")
        return [r["topic"] for r in c.fetchall()]

    # Quizzes
    def save_quiz(self, topic: str, questions: List[Dict[str, Any]]):
        now = datetime.datetime.utcnow().isoformat()
        qj = json.dumps(questions, ensure_ascii=False)
        c = self._conn.cursor()
        c.execute("INSERT INTO quizzes (topic, questions_json, created_at) VALUES (?, ?, ?)", (topic, qj, now))
        self._conn.commit()

    def get_quiz_for_topic(self, topic: str) -> List[Dict[str, Any]]:
        c = self._conn.cursor()
        c.execute("SELECT questions_json FROM quizzes WHERE topic = ? ORDER BY id DESC LIMIT 1", (topic,))
        row = c.fetchone()
        if not row:
            return []
        return json.loads(row["questions_json"])

    # Quiz results
    def save_quiz_result(self, topic: str, results: List[Dict[str, Any]], score: float):
        now = datetime.datetime.utcnow().isoformat()
        rj = json.dumps(results, ensure_ascii=False)
        c = self._conn.cursor()
        c.execute("INSERT INTO quiz_results (topic, results_json, score, taken_at) VALUES (?, ?, ?, ?)", (topic, rj, score, now))
        self._conn.commit()

    def get_quiz_results_for_topic(self, topic: str):
        c = self._conn.cursor()
        c.execute("SELECT * FROM quiz_results WHERE topic = ? ORDER BY taken_at DESC", (topic,))
        return [dict(row) for row in c.fetchall()]

    # Repetition schedule
    def get_schedule(self, topic: str):
        c = self._conn.cursor()
        c.execute("SELECT * FROM repetition_schedule WHERE topic = ?", (topic,))
        row = c.fetchone()
        return dict(row) if row else None

    def upsert_schedule(self, topic: str, interval_days: int, easiness: float, repetition_count: int, next_review_date: str):
        c = self._conn.cursor()
        row = self.get_schedule(topic)
        if row:
            c.execute("UPDATE repetition_schedule SET interval_days=?, easiness=?, repetition_count=?, next_review_date=? WHERE topic = ?", (interval_days, easiness, repetition_count, next_review_date, topic))
        else:
            c.execute("INSERT INTO repetition_schedule (topic, interval_days, easiness, repetition_count, next_review_date) VALUES (?, ?, ?, ?, ?)", (topic, interval_days, easiness, repetition_count, next_review_date))
        self._conn.commit()

    def get_all_schedules(self):
        c = self._conn.cursor()
        c.execute("SELECT * FROM repetition_schedule")
        return [dict(r) for r in c.fetchall()]

    def run_integrity_check(self):
        try:
            c = self._conn.cursor()
            c.execute("PRAGMA integrity_check")
            res = c.fetchone()
            return (res[0] == 'ok', res[0])
        except Exception as e:
            return (False, str(e))
