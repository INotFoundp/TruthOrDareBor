import sqlite3
import threading
import logging
from datetime import datetime, timedelta
from config import DB_PATH, GAME_TIMEOUT

logger = logging.getLogger(__name__)


class Database:
    # ایجاد یک قفل برای همزمانی بهتر
    _lock = threading.RLock()

    def __init__(self):
        # استفاده از check_same_thread=False برای اجازه دسترسی از thread‌های مختلف
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        # حذف کردن cursor به عنوان متغیر عضو کلاس برای جلوگیری از تداخل
        self._create_tables()
        # شروع thread تمیزکاری با استفاده از daemon=True
        threading.Thread(target=self._cleanup_loop, daemon=True).start()

    def _create_tables(self):
        # استفاده از with برای مدیریت بهتر قفل
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                date_joined TEXT,
                games_played INTEGER DEFAULT 0,
                truths_chosen INTEGER DEFAULT 0,
                dares_chosen INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0
            )""")
            # ادامه اجرای کوئری‌های ایجاد جدول
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                status TEXT,
                players TEXT,
                current_player INTEGER,
                created_at TEXT,
                last_activity TEXT,
                difficulty TEXT DEFAULT 'mixed',
                game_mode TEXT DEFAULT 'classic'
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER,
                player_id INTEGER,
                action_type TEXT,
                question_text TEXT,
                completed INTEGER,
                timestamp TEXT
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS truth_questions (
                question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                difficulty TEXT,
                category TEXT,
                times_used INTEGER DEFAULT 0
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_sets (
                set_id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_name TEXT NOT NULL,
                is_public INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dare_questions (
                question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                difficulty TEXT,
                category TEXT,
                times_used INTEGER DEFAULT 0
            )""")
            self.conn.commit()

    def execute(self, query, params=()):
        # استفاده از with برای مدیریت قفل و بستن cursor
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                return cursor
            except sqlite3.Error as e:
                logger.error(f"DB error: {e}, Query: {query}, Params: {params}")
                self.conn.rollback()  # برگرداندن تغییرات در صورت خطا
                raise

    def commit(self):
        with self._lock:
            try:
                self.conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Commit error: {e}")
                self.conn.rollback()
                raise

    def last_id(self):
        with self._lock:
            cursor = self.conn.cursor()
            return cursor.lastrowid

    def close(self):
        """بستن اتصال به دیتابیس"""
        try:
            self.conn.close()
        except sqlite3.Error as e:
            logger.error(f"Error closing database: {e}")

    def last_id(self):
        row = self.conn.execute("SELECT last_insert_rowid()").fetchone()
        return row[0] if row else None


    def _cleanup_loop(self):
        """حذف بازی‌های قدیمی و غیرفعال"""
        while True:
            threshold = (datetime.now() - timedelta(seconds=GAME_TIMEOUT)).isoformat()
            try:
                with self._lock:
                    self.execute(
                        "UPDATE games SET status='timeout' WHERE status IN ('waiting','started') AND last_activity < ?",
                        (threshold,)
                    )
                    self.commit()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            finally:
                # استفاده از threading.Event برای تاخیر
                threading.Event().wait(300)  # هر 5 دقیقه