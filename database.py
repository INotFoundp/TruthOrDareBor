# database.py
import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """ایجاد جداول مورد نیاز"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # جدول کاربران
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        first_name TEXT,
                        games_played INTEGER DEFAULT 0,
                        truths_completed INTEGER DEFAULT 0,
                        dares_completed INTEGER DEFAULT 0,
                        total_score INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # جدول سوالات
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question_text TEXT NOT NULL,
                        question_type TEXT NOT NULL CHECK (question_type IN ('truth', 'dare')),
                        mode TEXT NOT NULL DEFAULT 'classic',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # جدول بازی‌ها
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS games (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game_code TEXT UNIQUE NOT NULL,
                        creator_id INTEGER NOT NULL,
                        mode TEXT NOT NULL,
                        status TEXT DEFAULT 'waiting' CHECK (status IN ('waiting', 'active', 'finished')),
                        chat_id INTEGER,
                        current_player_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        finished_at TIMESTAMP,
                        FOREIGN KEY (creator_id) REFERENCES users(telegram_id)
                    )
                ''')

                # جدول بازیکنان بازی
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS game_players (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game_code TEXT NOT NULL,
                        player_id INTEGER NOT NULL,
                        join_order INTEGER NOT NULL,
                        FOREIGN KEY (game_code) REFERENCES games(game_code),
                        FOREIGN KEY (player_id) REFERENCES users(telegram_id)
                    )
                ''')

                # جدول اقدامات بازی
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS game_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game_code TEXT NOT NULL,
                        player_id INTEGER NOT NULL,
                        question_id INTEGER NOT NULL,
                        action_type TEXT NOT NULL CHECK (action_type IN ('truth', 'dare')),
                        completed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (game_code) REFERENCES games(game_code),
                        FOREIGN KEY (player_id) REFERENCES users(telegram_id),
                        FOREIGN KEY (question_id) REFERENCES questions(id)
                    )
                ''')

                conn.commit()
                logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization error: {e}")

    def execute_query(self, query, params=None, fetch=False):
        """اجرای کوئری در پایگاه داده"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch:
                    return cursor.fetchall()

                conn.commit()
                return cursor.lastrowid

        except Exception as e:
            logger.error(f"Database query error: {e}")
            return None

    def execute_many(self, query, params_list):
        """اجرای چندین کوئری به صورت همزمان"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Database executemany error: {e}")
            return False