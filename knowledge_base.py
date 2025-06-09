# knowledge_base.py
import sqlite3
import json
from datetime import datetime, timedelta, timezone
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

            # Table for general user-specific data (key-value store)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_data_store (
                    user_name TEXT NOT NULL,
                    data_key TEXT NOT NULL,
                    data_value TEXT,
                    last_updated_timestamp TEXT,
                    PRIMARY KEY (user_name, data_key)
                )
            """)

            # Table for structured user profile items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile_items (
                    user_name TEXT NOT NULL,
                    item_category TEXT NOT NULL, -- e.g., 'interest', 'preference', 'fact'
                    item_key TEXT NOT NULL,      -- e.g., 'hobby', 'music_genre', 'favorite_color'
                    item_value TEXT,
                    last_updated_timestamp TEXT,
                    PRIMARY KEY (user_name, item_category, item_key)
                )
            """)

            # Table for system-wide identity/configuration items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_identity (
                    item_category TEXT NOT NULL,
                    item_key TEXT NOT NULL,
                    item_value TEXT,
                    last_updated_timestamp TEXT,
                    PRIMARY KEY (item_category, item_key)
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

def get_most_recently_used_skill() -> Optional[str]:
    """
    Retrieves the name of the skill that was most recently used based on skill_usage_metrics.
    Returns:
        Optional[str]: The name of the skill, or None if no skills have been used.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT skill_name FROM skill_usage_metrics ORDER BY last_used_timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return row['skill_name']
            return None
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error retrieving most recently used skill: {e}", exc_info=True)
        return None

def record_user_feedback(skill_name: str, was_correct_according_to_user: bool, comment: Optional[str] = None):
    """
    Records user feedback about a skill's performance, updating metrics and logging failures.
    """
    timestamp_now_utc = datetime.now(timezone.utc).isoformat()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if not was_correct_according_to_user:
                # User says action was incorrect
                cursor.execute("""
                    UPDATE skill_usage_metrics 
                    SET failure_count = failure_count + 1, success_count = CASE WHEN success_count > 0 THEN success_count - 1 ELSE 0 END
                    WHERE skill_name = ?
                """, (skill_name,))
                
                error_log_message = "User feedback: Action deemed incorrect."
                if comment:
                    error_log_message += f" Comment: \"{comment}\""
                
                cursor.execute("""
                    INSERT INTO skill_failures (skill_name, timestamp, error_message, args_used)
                    VALUES (?, ?, ?, ?)
                """, (skill_name, timestamp_now_utc, error_log_message, "N/A (user feedback on previous action)"))
            else:
                # User says action was correct (potentially correcting a previously logged failure)
                cursor.execute("""
                    UPDATE skill_usage_metrics
                    SET success_count = success_count + 1, failure_count = CASE WHEN failure_count > 0 THEN failure_count - 1 ELSE 0 END
                    WHERE skill_name = ?
                """, (skill_name,))
            conn.commit()
            logging.info(f"KnowledgeBase: User feedback recorded for skill '{skill_name}'. User deemed correct: {was_correct_according_to_user}.")
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error recording user feedback for '{skill_name}': {e}", exc_info=True)

def get_skill_usage_summary(period: str = "overall", top_n: int = 5) -> list[dict]:
    """
    Retrieves a summary of skill usage.
    Args:
        period (str): "overall", "today", "last_7_days".
        top_n (int): Number of top skills to return.
    Returns:
        list[dict]: A list of dictionaries, each containing skill_name, usage_count, 
                    success_count, failure_count, and success_rate.
    """
    results = []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT skill_name, usage_count, success_count, failure_count,
                       (CASE WHEN usage_count > 0 THEN (CAST(success_count AS REAL) / usage_count) * 100 ELSE 0 END) as success_rate
                FROM skill_usage_metrics
            """
            params = []

            if period == "today":
                today_start_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                query += " WHERE last_used_timestamp >= ?"
                params.append(today_start_utc)
            elif period == "last_7_days":
                seven_days_ago_utc = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)).isoformat()
                query += " WHERE last_used_timestamp >= ?"
                params.append(seven_days_ago_utc)
            
            query += " ORDER BY usage_count DESC LIMIT ?"
            params.append(top_n)

            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                results.append(dict(row))
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error getting skill usage summary (period: {period}): {e}", exc_info=True)
    return results

def get_skill_failure_rates(top_n: int = 5, min_usage: int = 1) -> list[dict]:
    """
    Retrieves skills ordered by their failure rate.
    Args:
        top_n (int): Number of top skills to return by failure rate.
        min_usage (int): Minimum number of times a skill must have been used to be included.
    Returns:
        list[dict]: A list of dictionaries, each containing skill_name, failure_rate,
                    failure_count, and usage_count.
    """
    results = []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Calculate failure rate as (failure_count / usage_count) * 100
            # Ensure usage_count > 0 to avoid division by zero.
            query = """
                SELECT skill_name, failure_count, usage_count,
                       (CASE WHEN usage_count > 0 THEN (CAST(failure_count AS REAL) / usage_count) * 100 ELSE 0 END) as failure_rate
                FROM skill_usage_metrics
                WHERE usage_count >= ? 
                ORDER BY failure_rate DESC, failure_count DESC
                LIMIT ?
            """
            cursor.execute(query, (min_usage, top_n))
            for row in cursor.fetchall():
                results.append(dict(row))
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error getting skill failure rates: {e}", exc_info=True)
    return results

def get_recent_skill_failures(skill_name: Optional[str] = None, limit: int = 5) -> list[dict]:
    """
    Retrieves recent failure logs for a specific skill or all skills.
    Args:
        skill_name (Optional[str]): The name of the skill. If None, gets failures for all skills.
        limit (int): Maximum number of failure records to return.
    Returns:
        list[dict]: A list of failure records.
    """
    results = []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT skill_name, timestamp, error_message, args_used FROM skill_failures"
            params = []
            if skill_name:
                query += " WHERE skill_name = ?"
                params.append(skill_name)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                results.append(dict(row))
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error getting recent skill failures (skill: {skill_name}): {e}", exc_info=True)
    return results

def store_user_data(user_name: str, data_key: str, data_value: str) -> bool:
    """
    Stores or updates a key-value pair in the user_data_store.
    Returns True on success, False on failure.
    """
    if not user_name:
        logging.error("KnowledgeBase: User name cannot be empty for store_user_data.")
        return False
    timestamp_now_utc = datetime.now(timezone.utc).isoformat()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_data_store (user_name, data_key, data_value, last_updated_timestamp)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_name, data_key) DO UPDATE SET
                    data_value = excluded.data_value,
                    last_updated_timestamp = excluded.last_updated_timestamp
            """, (user_name, data_key, data_value, timestamp_now_utc))
            conn.commit()
            logging.info(f"KnowledgeBase: Stored/Updated user data for user '{user_name}', key '{data_key}'.")
            return True
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error storing user data for user '{user_name}', key '{data_key}': {e}", exc_info=True)
        return False

def get_user_data(user_name: str, data_key: str) -> Optional[str]:
    """
    Retrieves a value from the user_data_store by its key.
    Returns the value as a string, or None if the key is not found or an error occurs.
    """
    if not user_name:
        logging.error("KnowledgeBase: User name cannot be empty for get_user_data.")
        return None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data_value FROM user_data_store WHERE user_name = ? AND data_key = ?", (user_name, data_key))
            row = cursor.fetchone()
            if row:
                return row['data_value']
            return None
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error retrieving user data for user '{user_name}', key '{data_key}': {e}", exc_info=True)
        return None

def delete_user_data(user_name: str, data_key: str) -> bool:
    """
    Deletes a key-value pair from the user_data_store.
    Returns True on success or if key didn't exist, False on failure.
    """
    if not user_name:
        logging.error("KnowledgeBase: User name cannot be empty for delete_user_data.")
        return False
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_data_store WHERE user_name = ? AND data_key = ?", (user_name, data_key))
            conn.commit()
            logging.info(f"KnowledgeBase: Attempted to delete user data for user '{user_name}', key '{data_key}'. Rows affected: {cursor.rowcount}")
            return True
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error deleting user data for user '{user_name}', key '{data_key}': {e}", exc_info=True)
        return False

def store_user_profile_item(user_name: str, item_category: str, item_key: str, item_value: str) -> bool:
    """
    Stores or updates an item in the user_profile_items table.
    Returns True on success, False on failure.
    """
    if not all([user_name, item_category, item_key]):
        logging.error("KnowledgeBase: user_name, item_category, and item_key cannot be empty for store_user_profile_item.")
        return False
    timestamp_now_utc = datetime.now(timezone.utc).isoformat()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_profile_items (user_name, item_category, item_key, item_value, last_updated_timestamp)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_name, item_category, item_key) DO UPDATE SET
                    item_value = excluded.item_value,
                    last_updated_timestamp = excluded.last_updated_timestamp
            """, (user_name, item_category, item_key, item_value, timestamp_now_utc))
            conn.commit()
            logging.info(f"KnowledgeBase: Stored/Updated profile item for user '{user_name}', category '{item_category}', key '{item_key}'.")
            return True
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error storing profile item for user '{user_name}', category '{item_category}', key '{item_key}': {e}", exc_info=True)
        return False

def get_user_profile_item(user_name: str, item_category: str, item_key: str) -> Optional[str]:
    """
    Retrieves a specific item_value from the user_profile_items table.
    Returns the value as a string, or None if not found or an error occurs.
    """
    if not all([user_name, item_category, item_key]):
        logging.error("KnowledgeBase: user_name, item_category, and item_key cannot be empty for get_user_profile_item.")
        return None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_value FROM user_profile_items WHERE user_name = ? AND item_category = ? AND item_key = ?", 
                           (user_name, item_category, item_key))
            row = cursor.fetchone()
            return row['item_value'] if row else None
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error retrieving profile item for user '{user_name}', category '{item_category}', key '{item_key}': {e}", exc_info=True)
        return None

def get_user_profile_items_by_category(user_name: str, item_category: str) -> list[dict]:
    """
    Retrieves all items for a given user and category from user_profile_items.
    Returns a list of dictionaries, each containing item_key and item_value.
    """
    if not all([user_name, item_category]):
        logging.error("KnowledgeBase: user_name and item_category cannot be empty for get_user_profile_items_by_category.")
        return []
    results = []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_key, item_value FROM user_profile_items WHERE user_name = ? AND item_category = ? ORDER BY item_key", 
                           (user_name, item_category))
            for row in cursor.fetchall():
                results.append(dict(row))
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error retrieving profile items for user '{user_name}', category '{item_category}': {e}", exc_info=True)
    return results

def delete_user_profile_item(user_name: str, item_category: str, item_key: str) -> bool:
    """
    Deletes a specific item from the user_profile_items table.
    Returns True on success or if the item didn't exist, False on failure.
    """
    if not all([user_name, item_category, item_key]):
        logging.error("KnowledgeBase: user_name, item_category, and item_key cannot be empty for delete_user_profile_item.")
        return False
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM user_profile_items 
                WHERE user_name = ? AND item_category = ? AND item_key = ?
            """, (user_name, item_category, item_key))
            conn.commit()
            logging.info(f"KnowledgeBase: Attempted to delete profile item for user '{user_name}', category '{item_category}', key '{item_key}'. Rows affected: {cursor.rowcount}")
            return True
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error deleting profile item for user '{user_name}', category '{item_category}', key '{item_key}': {e}", exc_info=True)
        return False

# --- System Identity Functions ---

def store_system_identity_item(item_category: str, item_key: str, item_value: str) -> bool:
    """
    Stores or updates an item in the system_identity table.
    Returns True on success, False on failure.
    """
    if not all([item_category, item_key]):
        logging.error("KnowledgeBase: item_category and item_key cannot be empty for store_system_identity_item.")
        return False
    timestamp_now_utc = datetime.now(timezone.utc).isoformat()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_identity (item_category, item_key, item_value, last_updated_timestamp)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(item_category, item_key) DO UPDATE SET
                    item_value = excluded.item_value,
                    last_updated_timestamp = excluded.last_updated_timestamp
            """, (item_category, item_key, item_value, timestamp_now_utc))
            conn.commit()
            logging.info(f"KnowledgeBase: Stored/Updated system identity item for category '{item_category}', key '{item_key}'.")
            return True
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error storing system identity item for category '{item_category}', key '{item_key}': {e}", exc_info=True)
        return False

def get_system_identity_item(item_category: str, item_key: str) -> Optional[str]:
    """
    Retrieves a specific item_value from the system_identity table.
    Returns the value as a string, or None if not found or an error occurs.
    """
    if not all([item_category, item_key]):
        logging.error("KnowledgeBase: item_category and item_key cannot be empty for get_system_identity_item.")
        return None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_value FROM system_identity WHERE item_category = ? AND item_key = ?",
                           (item_category, item_key))
            row = cursor.fetchone()
            return row['item_value'] if row else None
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error retrieving system identity item for category '{item_category}', key '{item_key}': {e}", exc_info=True)
        return None

def delete_system_identity_item(item_category: str, item_key: str) -> bool:
    """
    Deletes a specific item from the system_identity table.
    Returns True on success or if the item didn't exist, False on failure.
    """
    if not all([item_category, item_key]):
        logging.error("KnowledgeBase: item_category and item_key cannot be empty for delete_system_identity_item.")
        return False
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM system_identity
                WHERE item_category = ? AND item_key = ?
            """, (item_category, item_key))
            conn.commit()
            logging.info(f"KnowledgeBase: Attempted to delete system identity item for category '{item_category}', key '{item_key}'. Rows affected: {cursor.rowcount}")
            return True
    except sqlite3.Error as e:
        logging.error(f"KnowledgeBase: Error deleting system identity item for category '{item_category}', key '{item_key}': {e}", exc_info=True)
        return False


# Initialize the DB when this module is loaded (e.g., at app startup if imported early)
# Alternatively, call init_db() explicitly from main.py
# init_db() # Let's call it from main.py for more explicit control