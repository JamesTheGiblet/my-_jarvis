# knowledge_base.py
import sqlite3
import json
from datetime import datetime, timezone
import logging
import os
from typing import Optional

# Database will be created in the same directory as this script (project root)
DB_NAME = "praxis_knowledge_base.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Access columns by name
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Table for overall skill usage metrics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_usage_metrics (
                    skill_name TEXT PRIMARY KEY,
                    usage_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_used_timestamp TEXT
                )
            """)

            # Table for detailed failure logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    error_message TEXT,
                    args_used TEXT 
                )
            """)
            conn.commit()
            logging.info(f"KnowledgeBase: Database '{DB_NAME}' initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error initializing database: {e}", exc_info=True)

def record_skill_invocation(skill_name: str, success: bool, args_used: Optional[dict] = None, error_message: Optional[str] = None):
    """
    Records the invocation of a skill, its success/failure, arguments, and any errors.
    """
    timestamp_now_utc = datetime.now(timezone.utc).isoformat()
    
    args_json = None
    if args_used:
        try:
            # Attempt to serialize args, converting non-serializable items to string
            args_json = json.dumps(args_used, default=str)
        except TypeError as te:
            logging.warning(f"KnowledgeBase: Could not serialize all arguments for skill '{skill_name}': {te}")
            args_json = json.dumps({"error": "Arguments not fully serializable", "details": str(te)}, default=str)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Update or insert into skill_usage_metrics
            cursor.execute("""
                INSERT INTO skill_usage_metrics (skill_name, usage_count, success_count, failure_count, last_used_timestamp)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(skill_name) DO UPDATE SET
                    usage_count = usage_count + 1,
                    success_count = success_count + excluded.success_count,
                    failure_count = failure_count + excluded.failure_count,
                    last_used_timestamp = excluded.last_used_timestamp
            """, (skill_name, 1 if success else 0, 1 if not success else 0, timestamp_now_utc))

            if not success:
                cursor.execute("""
                    INSERT INTO skill_failures (skill_name, timestamp, error_message, args_used)
                    VALUES (?, ?, ?, ?)
                """, (skill_name, timestamp_now_utc, error_message, args_json))
            
            conn.commit()
            logging.info(f"KnowledgeBase: Recorded invocation for skill '{skill_name}' (Success: {success}).")

    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error recording skill invocation for '{skill_name}': {e}", exc_info=True)

# Initialize the DB when this module is loaded (e.g., at app startup if imported early)
# Alternatively, call init_db() explicitly from main.py
# init_db() # Let's call it from main.py for more explicit control