# admin.py
from database import Database
from user import UserManager
import logging

logger = logging.getLogger(__name__)


class AdminManager:
    def __init__(self, database: Database, user_manager: UserManager):
        self.db = database
        self.user_manager = user_manager

    def add_question(self, question_text, question_type, mode="classic"):
        """اضافه کردن سؤال جدید"""
        try:
            self.db.execute_query(
                "INSERT INTO questions (question_text, question_type, mode) VALUES (?, ?, ?)",
                (question_text, question_type, mode)
            )
            return True
        except Exception as e:
            logger.error(f"Error adding question: {e}")
            return False

    def get_questions_list(self, question_type=None, mode=None, limit=50):
        """دریافت لیست سؤالات"""
        try:
            query = "SELECT id, question_text, question_type, mode FROM questions"
            params = []

            conditions = []
            if question_type:
                conditions.append("question_type = ?")
                params.append(question_type)

            if mode:
                conditions.append("mode = ?")
                params.append(mode)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += f" ORDER BY id DESC LIMIT {limit}"

            questions = self.db.execute_query(query, params, fetch=True)

            return [{
                'id': q[0],
                'text': q[1],
                'type': q[2],
                'mode': q[3]
            } for q in questions] if questions else []
        except Exception as e:
            logger.error(f"Error getting questions list: {e}")
            return []

    def delete_question(self, question_id):
        """حذف سؤال"""
        try:
            self.db.execute_query(
                "DELETE FROM questions WHERE id = ?",
                (question_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting question {question_id}: {e}")
            return False

    def get_general_stats(self):
        """دریافت آمار کلی"""
        try:
            # تعداد کل کاربران
            total_users = self.db.execute_query(
                "SELECT COUNT(*) FROM users", fetch=True
            )[0][0]

            # تعداد کاربران فعال (بازی کرده‌اند)
            active_users = self.db.execute_query(
                "SELECT COUNT(*) FROM users WHERE games_played > 0", fetch=True
            )[0][0]

            # تعداد کل بازی‌ها
            total_games = self.db.execute_query(
                "SELECT COUNT(*) FROM games", fetch=True
            )[0][0]

            # تعداد بازی‌های فعال
            active_games = self.db.execute_query(
                "SELECT COUNT(*) FROM games WHERE status = 'active'", fetch=True
            )[0][0]

            # تعداد سؤالات
            total_questions = self.db.execute_query(
                "SELECT COUNT(*) FROM questions", fetch=True
            )[0][0]

            # سؤالات حقیقت و شجاعت
            truth_questions = self.db.execute_query(
                "SELECT COUNT(*) FROM questions WHERE question_type = 'truth'", fetch=True
            )[0][0]

            dare_questions = self.db.execute_query(
                "SELECT COUNT(*) FROM questions WHERE question_type = 'dare'", fetch=True
            )[0][0]

            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_games': total_games,
                'active_games': active_games,
                'total_questions': total_questions,
                'truth_questions': truth_questions,
                'dare_questions': dare_questions
            }
        except Exception as e:
            logger.error(f"Error getting general stats: {e}")
            return {}

    def get_top_users(self, limit=10):
        """دریافت کاربران برتر"""
        try:
            users = self.db.execute_query(
                """SELECT telegram_id, first_name, username, games_played, total_score
                   FROM users WHERE games_played > 0 
                   ORDER BY total_score DESC, games_played DESC 
                   LIMIT ?""",
                (limit,), fetch=True
            )

            return [{
                'telegram_id': u[0],
                'first_name': u[1],
                'username': u[2],
                'games_played': u[3],
                'total_score': u[4]
            } for u in users] if users else []
        except Exception as e:
            logger.error(f"Error getting top users: {e}")
            return []