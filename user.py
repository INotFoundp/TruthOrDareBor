# user.py
from database import Database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class UserManager:
    def __init__(self, database: Database):
        self.db = database

    def register_user(self, telegram_id, username=None, first_name=None):
        """ثبت نام یا به‌روزرسانی کاربر"""
        try:
            # بررسی وجود کاربر
            existing_user = self.db.execute_query(
                "SELECT id FROM users WHERE telegram_id = ?",
                (telegram_id,), fetch=True
            )

            if existing_user:
                # به‌روزرسانی اطلاعات
                self.db.execute_query(
                    """UPDATE users SET username = ?, first_name = ?, 
                       last_activity = CURRENT_TIMESTAMP WHERE telegram_id = ?""",
                    (username, first_name, telegram_id)
                )
            else:
                # ثبت کاربر جدید
                self.db.execute_query(
                    """INSERT INTO users (telegram_id, username, first_name) 
                       VALUES (?, ?, ?)""",
                    (telegram_id, username, first_name)
                )
            return True
        except Exception as e:
            logger.error(f"Error registering user {telegram_id}: {e}")
            return False

    def get_user_stats(self, telegram_id):
        """دریافت آمار کاربر"""
        try:
            user_data = self.db.execute_query(
                """SELECT telegram_id, username, first_name, games_played, 
                   truths_completed, dares_completed, total_score FROM users 
                   WHERE telegram_id = ?""",
                (telegram_id,), fetch=True
            )

            if user_data:
                return {
                    'telegram_id': user_data[0][0],
                    'username': user_data[0][1],
                    'first_name': user_data[0][2],
                    'games_played': user_data[0][3],
                    'truths_completed': user_data[0][4],
                    'dares_completed': user_data[0][5],
                    'total_score': user_data[0][6]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user stats {telegram_id}: {e}")
            return None

    def update_user_stats(self, telegram_id, games_played=0, truths_completed=0,
                          dares_completed=0, score_add=0):
        """به‌روزرسانی آمار کاربر"""
        try:
            self.db.execute_query(
                """UPDATE users SET 
                   games_played = games_played + ?, 
                   truths_completed = truths_completed + ?,
                   dares_completed = dares_completed + ?,
                   total_score = total_score + ?,
                   last_activity = CURRENT_TIMESTAMP
                   WHERE telegram_id = ?""",
                (games_played, truths_completed, dares_completed, score_add, telegram_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error updating user stats {telegram_id}: {e}")
            return False

    def is_admin(self, telegram_id):
        """بررسی ادمین بودن کاربر"""
        from config import ADMIN_IDS
        return telegram_id in ADMIN_IDS

    def search_user(self, search_term):
        """جستجوی کاربر بر اساس ID یا username"""
        try:
            # جستجو بر اساس telegram_id
            if search_term.isdigit():
                user_data = self.db.execute_query(
                    """SELECT telegram_id, username, first_name, games_played, 
                       truths_completed, dares_completed, total_score FROM users 
                       WHERE telegram_id = ?""",
                    (int(search_term),), fetch=True
                )
            else:
                # جستجو بر اساس username
                user_data = self.db.execute_query(
                    """SELECT telegram_id, username, first_name, games_played, 
                       truths_completed, dares_completed, total_score FROM users 
                       WHERE username LIKE ?""",
                    (f"%{search_term}%",), fetch=True
                )

            return user_data if user_data else []
        except Exception as e:
            logger.error(f"Error searching user {search_term}: {e}")
            return []