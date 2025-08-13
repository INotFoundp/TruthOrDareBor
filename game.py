# game.py
from database import Database
from user import UserManager
import random
import string
import logging

logger = logging.getLogger(__name__)


class GameManager:
    def __init__(self, database: Database, user_manager: UserManager):
        self.db = database
        self.user_manager = user_manager

    def generate_game_code(self):
        """تولید کد منحصر به فرد بازی"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    def create_game(self, creator_id, mode="classic", chat_id=None):
        """ایجاد بازی جدید"""
        try:
            game_code = self.generate_game_code()

            # بررسی تکراری نبودن کد
            while self.db.execute_query(
                    "SELECT id FROM games WHERE game_code = ?",
                    (game_code,), fetch=True
            ):
                game_code = self.generate_game_code()

            # ایجاد بازی
            self.db.execute_query(
                """INSERT INTO games (game_code, creator_id, mode, chat_id) 
                   VALUES (?, ?, ?, ?)""",
                (game_code, creator_id, mode, chat_id)
            )

            # اضافه کردن سازنده به لیست بازیکنان
            self.add_player_to_game(game_code, creator_id)

            return game_code
        except Exception as e:
            logger.error(f"Error creating game: {e}")
            return None

    def add_player_to_game(self, game_code, player_id):
        """اضافه کردن بازیکن به بازی"""
        try:
            # بررسی وجود بازی و وضعیت انتظار
            game = self.db.execute_query(
                "SELECT status FROM games WHERE game_code = ?",
                (game_code,), fetch=True
            )

            if not game or game[0][0] != 'waiting':
                return False

            # بررسی عدم عضویت قبلی
            existing_player = self.db.execute_query(
                "SELECT id FROM game_players WHERE game_code = ? AND player_id = ?",
                (game_code, player_id), fetch=True
            )

            if existing_player:
                return False  # قبلاً عضو است

            # تعیین ترتیب پیوستن
            join_order = self.db.execute_query(
                "SELECT COUNT(*) FROM game_players WHERE game_code = ?",
                (game_code,), fetch=True
            )[0][0] + 1

            # اضافه کردن بازیکن
            self.db.execute_query(
                "INSERT INTO game_players (game_code, player_id, join_order) VALUES (?, ?, ?)",
                (game_code, player_id, join_order)
            )

            return True
        except Exception as e:
            logger.error(f"Error adding player to game {game_code}: {e}")
            return False

    def get_game_players(self, game_code):
        """دریافت لیست بازیکنان"""
        try:
            players = self.db.execute_query(
                """SELECT gp.player_id, u.first_name, u.username, gp.join_order
                   FROM game_players gp 
                   JOIN users u ON gp.player_id = u.telegram_id 
                   WHERE gp.game_code = ? 
                   ORDER BY gp.join_order""",
                (game_code,), fetch=True
            )

            return [{
                'player_id': p[0],
                'first_name': p[1],
                'username': p[2],
                'join_order': p[3]
            } for p in players] if players else []
        except Exception as e:
            logger.error(f"Error getting game players {game_code}: {e}")
            return []

    def start_game(self, game_code, starter_id):
        """شروع بازی"""
        try:
            # بررسی اینکه فقط سازنده بتواند بازی را شروع کند
            game = self.db.execute_query(
                "SELECT creator_id, status FROM games WHERE game_code = ?",
                (game_code,), fetch=True
            )

            if not game or game[0][0] != starter_id or game[0][1] != 'waiting':
                return False

            # بررسی حداقل دو بازیکن
            players = self.get_game_players(game_code)
            if len(players) < 2:
                return False

            # انتخاب بازیکن اول به صورت تصادفی
            first_player = random.choice(players)

            # شروع بازی
            self.db.execute_query(
                "UPDATE games SET status = 'active', current_player_id = ? WHERE game_code = ?",
                (first_player['player_id'], game_code)
            )

            return first_player
        except Exception as e:
            logger.error(f"Error starting game {game_code}: {e}")
            return False

    def get_random_question(self, question_type, mode="classic"):
        """دریافت سؤال تصادفی"""
        try:
            questions = self.db.execute_query(
                "SELECT id, question_text FROM questions WHERE question_type = ? AND mode = ?",
                (question_type, mode), fetch=True
            )

            if questions:
                question = random.choice(questions)
                return {
                    'id': question[0],
                    'text': question[1]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting random question: {e}")
            return None

    def record_action(self, game_code, player_id, question_id, action_type, completed=False):
        """ثبت اقدام بازیکن"""
        try:
            # دریافت اطلاعات بازی
            game_info = self.get_game_info(game_code)
            if not game_info or game_info['status'] != 'active':
                return False
            self.db.execute_query(
                """INSERT INTO game_actions (game_code, player_id, question_id, action_type, completed) 
                   VALUES (?, ?, ?, ?, ?)""",
                (game_code, player_id, question_id, action_type, completed)
            )

            # به‌روزرسانی آمار کاربر
            if completed:
                if action_type == 'truth':
                    self.user_manager.update_user_stats(player_id, truths_completed=1, score_add=10)
                else:  # dare
                    self.user_manager.update_user_stats(player_id, dares_completed=1, score_add=15)

            return True
        except Exception as e:
            logger.error(f"Error recording action: {e}")
            return False

    def next_turn(self, game_code):
        """انتقال نوبت به بازیکن بعدی"""
        try:
            # دریافت اطلاعات بازی
            game_info = self.get_game_info(game_code)
            if not game_info or game_info['status'] != 'active':
                return None
            # دریافت بازیکن فعلی
            current_player = self.db.execute_query(
                "SELECT current_player_id FROM games WHERE game_code = ?",
                (game_code,), fetch=True
            )[0][0]

            # دریافت لیست بازیکنان
            players = self.get_game_players(game_code)

            # پیدا کردن ایندکس بازیکن فعلی
            current_index = next(
                (i for i, p in enumerate(players) if p['player_id'] == current_player),
                0
            )

            # انتخاب بازیکن بعدی (چرخشی)
            next_index = (current_index + 1) % len(players)
            next_player = players[next_index]

            # به‌روزرسانی بازیکن فعلی
            self.db.execute_query(
                "UPDATE games SET current_player_id = ? WHERE game_code = ?",
                (next_player['player_id'], game_code)
            )

            return next_player
        except Exception as e:
            logger.error(f"Error switching turn: {e}")
            return None

    def get_game_info(self, game_code):
        """دریافت اطلاعات بازی"""
        try:
            game = self.db.execute_query(
                """SELECT game_code, creator_id, mode, status, current_player_id, chat_id 
                   FROM games WHERE game_code = ?""",
                (game_code,), fetch=True
            )

            if game:
                return {
                    'game_code': game[0][0],
                    'creator_id': game[0][1],
                    'mode': game[0][2],
                    'status': game[0][3],
                    'current_player_id': game[0][4],
                    'chat_id': game[0][5]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting game info {game_code}: {e}")
            return None

    def finish_game(self, game_code):
        """پایان دادن به بازی"""
        try:
            # ابتدا اطلاعات بازیکنان را دریافت کنید
            players = self.get_game_players(game_code)

            # به‌روزرسانی آمار تمام بازیکنان
            for player in players:
                self.user_manager.update_user_stats(player['player_id'], games_played=1)

            # سپس اطلاعات بازی را پاک کنید
            # حذف اقدامات بازی
            self.db.execute_query(
                "DELETE FROM game_actions WHERE game_code = ?",
                (game_code,)
            )

            # حذف بازیکنان
            self.db.execute_query(
                "DELETE FROM game_players WHERE game_code = ?",
                (game_code,)
            )

            # حذف خود بازی
            self.db.execute_query(
                "DELETE FROM games WHERE game_code = ?",
                (game_code,)
            )

            return True
        except Exception as e:
            logger.error(f"Error finishing game {game_code}: {e}")
            return False