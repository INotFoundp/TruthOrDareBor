"""
اصلاحات برای فایل game.py
"""

import json
import logging
from datetime import datetime
from db import Database

logger = logging.getLogger(__name__)


class GameManager:
    def __init__(self, db: Database):
        self.db = db

    def create_game(self, creator_id, difficulty, mode):
        """ایجاد یک بازی جدید"""
        try:
            players = json.dumps([creator_id])
            self.db.execute(
                "INSERT INTO games(creator_id,status,players,current_player,created_at,last_activity,difficulty,game_mode) VALUES(?, 'waiting', ?, ?, datetime('now'), datetime('now'), ?, ?)",
                (creator_id, players, creator_id, difficulty, mode)
            )
            self.db.commit()
            return self.db.last_id()
        except Exception as e:
            logger.error(f"Error creating game: {e}")
            raise

    def add_player(self, game_id, user_id):
        """اضافه کردن بازیکن به بازی"""
        try:
            row = self.db.execute("SELECT players, status FROM games WHERE game_id=?", (game_id,)).fetchone()
            if not row:
                logger.warning(f"Game {game_id} not found")
                return False

            players = json.loads(row['players'])
            if row['status'] == 'waiting' and user_id not in players:
                players.append(user_id)
                self.db.execute(
                    "UPDATE games SET players=?, last_activity=datetime('now') WHERE game_id=?",
                    (json.dumps(players), game_id)
                )
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding player to game {game_id}: {e}")
            return False

    def start_game(self, game_id):
        """شروع بازی"""
        try:
            # بررسی اینکه بازی موجود است و در وضعیت انتظار است
            row = self.db.execute("SELECT status FROM games WHERE game_id=?", (game_id,)).fetchone()
            if not row or row['status'] != 'waiting':
                logger.warning(f"Cannot start game {game_id}. Status: {row['status'] if row else 'not found'}")
                return False

            self.db.execute(
                "UPDATE games SET status='started', current_player=json_extract(players,'$[0]'), last_activity=datetime('now') WHERE game_id=?",
                (game_id,)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error starting game {game_id}: {e}")
            return False

    def next_turn(self, game_id):
        """نوبت بعدی بازی"""
        try:
            row = self.db.execute("SELECT players, current_player FROM games WHERE game_id=?", (game_id,)).fetchone()
            if not row:
                logger.warning(f"Game {game_id} not found")
                return None

            players = json.loads(row['players'])
            if not players:
                logger.warning(f"No players in game {game_id}")
                return None

            try:
                idx = players.index(row['current_player'])
                nxt = players[(idx + 1) % len(players)]
            except ValueError:
                # اگر current_player در لیست نباشد، نفر اول را برمی‌گرداند
                logger.warning(f"Current player not in players list for game {game_id}")
                nxt = players[0]

            self.db.execute(
                "UPDATE games SET current_player=?, last_activity=datetime('now') WHERE game_id=?",
                (nxt, game_id)
            )
            self.db.commit()
            return nxt
        except Exception as e:
            logger.error(f"Error in next_turn for game {game_id}: {e}")
            return None

    def get_random_question(self, question_type, difficulty, game_mode=None):
        """
        دریافت سوال تصادفی بر اساس نوع، سختی و حالت بازی

        Args:
            question_type: 'truth' یا 'dare'
            difficulty: 'easy', 'medium', 'hard', 'mixed'
            game_mode: 'classic', 'challenge', 'performance' یا None
        """
        try:
            table = 'truth_questions' if question_type == 'truth' else 'dare_questions'

            # تعیین category بر اساس game_mode
            category_map = {
                'classic': 'عمومی',
                'challenge': 'چالشی',
                'performance': 'عملکردی'
            }

            # اگر game_mode مشخص شده، category را تعیین کن
            if game_mode and game_mode in category_map:
                target_category = category_map[game_mode]

                # اول سعی کن سوال از category مخصوص پیدا کنی
                if difficulty == 'mixed':
                    # برای mixed از همه سطوح انتخاب کن
                    question = self.db.execute(
                        f"SELECT question_text FROM {table} WHERE category = ? ORDER BY RANDOM() LIMIT 1",
                        (target_category,)
                    ).fetchone()
                else:
                    # برای سطح مشخص
                    question = self.db.execute(
                        f"SELECT question_text FROM {table} WHERE difficulty = ? AND category = ? ORDER BY RANDOM() LIMIT 1",
                        (difficulty, target_category)
                    ).fetchone()

                # اگر سوال پیدا شد، برگردان
                if question:
                    return question['question_text']

                # اگر سوال از category مخصوص پیدا نشد، log کن
                logger.warning(f"No questions found for category '{target_category}', falling back to general")

            # fallback: اگر category مخصوص نداریم یا سوال پیدا نشد
            if difficulty == 'mixed':
                # برای mixed از همه سطوح و categories انتخاب کن
                question = self.db.execute(
                    f"SELECT question_text FROM {table} ORDER BY RANDOM() LIMIT 1"
                ).fetchone()
            else:
                # اول سعی کن از سطح مشخص پیدا کنی
                question = self.db.execute(
                    f"SELECT question_text FROM {table} WHERE difficulty = ? ORDER BY RANDOM() LIMIT 1",
                    (difficulty,)
                ).fetchone()

                # اگر پیدا نشد، از همه سطوح انتخاب کن
                if not question:
                    question = self.db.execute(
                        f"SELECT question_text FROM {table} ORDER BY RANDOM() LIMIT 1"
                    ).fetchone()

            return question['question_text'] if question else f"سوال {question_type} پیش‌فرض"

        except Exception as e:
            logger.error(f"Error getting random question: {e}")
            return f"سوال {question_type} پیش‌فرض"

    def record_action(self, game_id, player_id, action_type, question_text):
        """ثبت اکشن بازیکن (حقیقت یا شجاعت) و بازگرداندن history_id جدید."""
        try:
            # 1. افزایش استفاده از سوال
            table = 'truth_questions' if action_type == 'truth' else 'dare_questions'
            self.db.execute(
                f"UPDATE {table} SET times_used = times_used + 1 WHERE question_text = ?",
                (question_text,)
            )

            # 2. ثبت در تاریخچه بازی و گرفتن cursor
            cursor = self.db.execute(
                """
                INSERT INTO game_history
                    (game_id, player_id, action_type, question_text, completed, timestamp)
                VALUES
                    (?, ?, ?, ?, NULL, datetime('now'))
                """,
                (game_id, player_id, action_type, question_text)
            )
            self.db.commit()

            # 3. بروزرسانی آخرین فعالیت بازی
            self.db.execute(
                "UPDATE games SET last_activity = datetime('now') WHERE game_id = ?",
                (game_id,)
            )
            self.db.commit()

            # 4. بازگرداندن شناسه‌ی سطر جدید
            return cursor.lastrowid

        except Exception as e:
            logger.error(f"Error recording action for game {game_id}: {e}")
            # در صورت خطا، هیچ تراکنشی را نیمه‌کاره نگذاریم
            try:
                self.db.commit()
            except:
                pass
            return None

    def complete_action(self, history_id, completed):
        """تکمیل اکشن (انجام شد یا نشد)"""
        try:
            self.db.execute(
                "UPDATE game_history SET completed=? WHERE history_id=?",
                (1 if completed else 0, history_id)
            )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error completing action {history_id}: {e}")
            return False

    def get_game_info(self, game_id):
        """دریافت اطلاعات بازی"""
        try:
            row = self.db.execute(
                "SELECT game_id, creator_id, status, players, current_player, created_at, difficulty, game_mode FROM games WHERE game_id=?",
                (game_id,)
            ).fetchone()

            if not row:
                return None

            # تبدیل به دیکشنری
            game_info = dict(row)
            # تبدیل players از JSON به لیست
            game_info['players'] = json.loads(game_info['players'])

            return game_info
        except Exception as e:
            logger.error(f"Error getting game info for {game_id}: {e}")
            return None

    def end_game(self, game_id):
        """پایان دادن به بازی"""
        try:
            # ۱) تغییر وضعیت بازی به 'ended'
            self.db.execute(
                "UPDATE games SET status='ended', last_activity=datetime('now') WHERE game_id=? AND status IN ('waiting', 'started')",
                (game_id,)
            )
            self.db.commit()

            # ۲) بروزرسانی آمار games_played برای همه بازیکنان
            game = self.get_game_info(game_id)  # <-- اینجا
            if game and game['players']:
                # players یک لیستِ telegram_id است
                players_str = ','.join('?' for _ in game['players'])
                self.db.execute(
                    f"UPDATE users SET games_played = games_played + 1 WHERE telegram_id IN ({players_str})",
                    game['players']
                )
                self.db.commit()

            return True
        except Exception as e:
            logger.error(f"Error ending game {game_id}: {e}")
            return False