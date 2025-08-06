import json
import logging
from telebot import types
from db import Database
from user import UserManager

logger = logging.getLogger(__name__)


class AdminManager:
    def __init__(self, db: Database, user_mgr: UserManager):
        self.db = db
        self.user_mgr = user_mgr
        # pending_requests stores action, step, and temp data
        self.pending_requests = {}  # {user_id: {'action': str, 'step': int, 'text': str}}


    def show_main_menu(self, chat_id, message_id, bot):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("📝 مدیریت سؤالات", callback_data="admin_questions"),
            types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
            types.InlineKeyboardButton("🎮 آمار بازی‌ها", callback_data="admin_games"),
        )
        bot.edit_message_text(
            "🔐 پنل مدیریت ربات حقیقت و شجاعت",
            chat_id, message_id,
            reply_markup=kb
        )


    def show_user_management(self, chat_id, message_id, bot):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("📊 آمار کاربران", callback_data="user_stats"),
            types.InlineKeyboardButton("👥 کاربران فعال", callback_data="active_users"),
            types.InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="search_user"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        )
        bot.edit_message_text(
            "👥 مدیریت کاربران:\nلطفاً یک گزینه انتخاب کنید:",
            chat_id, message_id,
            reply_markup=kb
        )

    def handle_callback(self, call, bot):
        data = call.data
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        user_id = call.from_user.id

        # Only admins
        if not self.user_mgr.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ دسترسی ندارید.", show_alert=True)
            return

        # Routing
        if data == 'admin_questions':
            self.show_question_management(chat_id, msg_id, bot)
        elif data == 'admin_users':
            self.show_user_management(chat_id, msg_id, bot)
        elif data == 'admin_games':
            self.show_game_statistics(chat_id, msg_id, bot)
        elif data == 'admin_back':
            self.show_main_menu(chat_id, msg_id, bot)

        # Question management
        elif data in ('add_question_truth', 'add_question_dare'):
            qtype = 'truth' if data.endswith('truth') else 'dare'
            self.start_add_question(chat_id, user_id, bot, qtype)
            bot.delete_message(chat_id, msg_id)
        elif data.startswith('set_question_diff_'):
            parts = data.split('_')
            if len(parts) >= 5:
                qtype = parts[3]
                level = parts[4]
                self.finish_add_question(chat_id, user_id, bot, qtype, level)
            else:
                bot.send_message(chat_id, "❌ اطلاعات ناقص است. لطفاً دوباره تلاش کنید.")
        elif data == 'list_questions_truth':
            self.list_questions(chat_id, msg_id, bot, 'truth')
        elif data == 'list_questions_dare':
            self.list_questions(chat_id, msg_id, bot, 'dare')
        elif data == 'question_stats':
            self.show_question_stats(chat_id, msg_id, bot)

        # Pagination
        elif data.startswith('questions_'):
            parts = data.split('_')
            qtype, direction, offset = parts[1], parts[2], int(parts[3])
            self.paginate_questions(chat_id, msg_id, bot, qtype, direction, offset)

        # User management
        elif data == 'user_stats':
            self.show_user_stats(chat_id, msg_id, bot)
        elif data == 'active_users':
            self.show_active_users(chat_id, msg_id, bot)
        elif data == 'search_user':
            self.start_user_search(chat_id, user_id, bot)
            bot.delete_message(chat_id, msg_id)

        # Active games
        elif data == 'list_active_games':
            self.list_active_games(chat_id, msg_id, bot)

        bot.answer_callback_query(call.id)

    def show_question_management(self, chat_id, message_id, bot):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("➕ افزودن حقیقت", callback_data="add_question_truth"),
            types.InlineKeyboardButton("➕ افزودن شجاعت", callback_data="add_question_dare"),
            types.InlineKeyboardButton("📋 لیست حقیقت", callback_data="list_questions_truth"),
            types.InlineKeyboardButton("📋 لیست شجاعت", callback_data="list_questions_dare"),
            types.InlineKeyboardButton("📊 آمار سؤالات", callback_data="question_stats"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        )
        bot.edit_message_text(
            "📝 مدیریت سؤالات:",
            chat_id, message_id,
            reply_markup=kb
        )

    def start_add_question(self, chat_id, user_id, bot, question_type):
        # Step 1: ask text
        self.pending_requests[user_id] = {'action': f'add_question_{question_type}', 'step': 1}
        title = 'حقیقت' if question_type == 'truth' else 'شجاعت'
        msg = bot.send_message(
            chat_id,
            f"لطفاً متن سؤال {title} را وارد کنید:\nبرای لغو، /cancel را ارسال کنید."
        )
        bot.register_next_step_handler(msg, self.process_question_text, question_type, bot)

    def process_question_text(self, message, question_type, bot):
        user_id = message.from_user.id
        chat_id = message.chat.id
        text = (message.text or '').strip()
        # cancel
        if text == '/cancel':
            self.pending_requests.pop(user_id, None)
            bot.send_message(chat_id, "❌ عملیات لغو شد.")
            return
        if len(text) < 5:
            bot.send_message(chat_id, "⚠️ طول متن کم است. حداقل 5 کاراکتر.")
            bot.register_next_step_handler(message, self.process_question_text, question_type, bot)
            return
        # store text and ask difficulty
        self.pending_requests[user_id].update({'step': 2, 'text': text})
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("آسان", callback_data=f"set_question_diff_{question_type}_easy"),
            types.InlineKeyboardButton("متوسط", callback_data=f"set_question_diff_{question_type}_medium"),
            types.InlineKeyboardButton("سخت", callback_data=f"set_question_diff_{question_type}_hard"),
            types.InlineKeyboardButton("مختلط", callback_data=f"set_question_diff_{question_type}_mixed")
        )
        bot.send_message(chat_id, "لطفاً سطح دشواری را انتخاب کنید:", reply_markup=kb)

    def finish_add_question(self, chat_id, user_id, bot, question_type, difficulty):
        # validate pending
        req = self.pending_requests.get(user_id)
        if not req or req.get('step') != 2:
            bot.send_message(chat_id, "❌ روند افزودن سؤال معتبر نیست.")
            return
        text = req.get('text')
        table = 'truth_questions' if question_type == 'truth' else 'dare_questions'
        # insert
        self.db.execute(
            f"INSERT INTO {table} (question_text, difficulty, category) VALUES (?, ?, 'عمومی')",
            (text, difficulty)
        )
        self.db.commit()
        self.pending_requests.pop(user_id, None)
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("➕ افزودن سوال دیگر", callback_data=f"add_question_{question_type}"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_questions")
        )
        bot.send_message(chat_id, f"✅ سوال با سطح {difficulty} اضافه شد.", reply_markup=kb)

    def list_questions(self, chat_id, message_id, bot, question_type, offset=0, limit=5):
        table = 'truth_questions' if question_type == 'truth' else 'dare_questions'
        title = 'حقیقت' if question_type == 'truth' else 'شجاعت'
        rows = self.db.execute(
            f"SELECT question_id, question_text, difficulty FROM {table} ORDER BY question_id DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        text = f"📋 لیست {title} (صفحه {offset//limit+1}):\n" if rows else f"📭 هیچ {title} یافت نشد."
        for r in rows:
            diff = r['difficulty'] or 'متوسط'
            text += f"#{r['question_id']}: {r['question_text']} (سطح: {diff})\n"
        kb = types.InlineKeyboardMarkup(row_width=3)
        kb.add(
            types.InlineKeyboardButton("⬅️ قبلی", callback_data=f"questions_{question_type}_prev_{offset}"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_questions"),
            types.InlineKeyboardButton("➡️ بعدی", callback_data=f"questions_{question_type}_next_{offset}"),
        )
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)

    def paginate_questions(self, chat_id, message_id, bot, qtype, direction, offset):
        new_offset = max(0, offset + (5 if direction == 'next' else -5))
        self.list_questions(chat_id, message_id, bot, qtype, new_offset)

    def show_question_stats(self, chat_id, message_id, bot):
        truth_cnt = self.db.execute('SELECT COUNT(*) cnt FROM truth_questions').fetchone()['cnt']
        dare_cnt = self.db.execute('SELECT COUNT(*) cnt FROM dare_questions').fetchone()['cnt']
        popular_truth = self.db.execute('SELECT question_text, times_used FROM truth_questions ORDER BY times_used DESC LIMIT 1').fetchone()
        popular_dare = self.db.execute('SELECT question_text, times_used FROM dare_questions ORDER BY times_used DESC LIMIT 1').fetchone()
        text = f"📊 آمار سؤالات:\n🔵 حقیقت: {truth_cnt}\n🔴 شجاعت: {dare_cnt}\n"
        if popular_truth: text += f"پربازدید حقیقت: {popular_truth['question_text']} ({popular_truth['times_used']})\n"
        if popular_dare: text += f"پربازدید شجاعت: {popular_dare['question_text']} ({popular_dare['times_used']})\n"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_questions"))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)

    # توابع مدیریت کاربران

    def show_user_stats(self, chat_id, message_id, bot):
        total = self.db.execute('SELECT COUNT(*) as cnt FROM users').fetchone()['cnt']
        active = self.db.execute(
            "SELECT COUNT(DISTINCT telegram_id) as cnt FROM game_history WHERE timestamp>=datetime('now','-7 days')"
        ).fetchone()['cnt']
        text = (
            f"📊 آمار کاربران:\n\n"
            f"👥 تعداد کل کاربران: {total}\n"
            f"🕒 کاربران فعال (۷ روز اخیر): {active}"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users"))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)

    def show_active_users(self, chat_id, message_id, bot, page=0):
        limit, offset = 10, page * 10
        rows = self.db.execute(
            """
            SELECT u.telegram_id, u.first_name, u.username,
                   COUNT(h.history_id) as activity
              FROM users u
              LEFT JOIN game_history h
                ON u.telegram_id = h.player_id
               AND h.timestamp >= datetime('now','-30 days')
             GROUP BY u.telegram_id
             ORDER BY activity DESC
             LIMIT ? OFFSET ?
            """, (limit, offset)
        ).fetchall()

        if not rows:
            text = "👥 هیچ کاربر فعالی یافت نشد."
        else:
            text = "👥 کاربران فعال (۳۰ روز اخیر):\n\n"
            for i, r in enumerate(rows, start=offset + 1):
                name = self.user_mgr.get_name(r['telegram_id'])
                text += f"{i}. {name} — {r['activity']} فعالیت\n"

        kb = types.InlineKeyboardMarkup(row_width=3)
        kb.add(
            types.InlineKeyboardButton("⬅️ قبلی", callback_data=f"active_users_prev_{page}"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users"),
            types.InlineKeyboardButton("➡️ بعدی", callback_data=f"active_users_next_{page}")
        )
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)

    def show_game_statistics(self, chat_id, message_id, bot):
        total = self.db.execute("SELECT COUNT(*) as cnt FROM games").fetchone()['cnt']
        active = self.db.execute(
            "SELECT COUNT(*) as cnt FROM games WHERE status IN ('waiting','started')"
        ).fetchone()['cnt']
        today = self.db.execute(
            "SELECT COUNT(*) as cnt FROM games WHERE DATE(created_at)=DATE('now')"
        ).fetchone()['cnt']
        popular = self.db.execute(
            "SELECT game_mode FROM games GROUP BY game_mode ORDER BY COUNT(*) DESC LIMIT 1"
        ).fetchone()
        popular_mode = popular['game_mode'] if popular else '—'

        text = (
            "🎮 آمار بازی‌ها:\n\n"
            f"🔢 کل بازی‌ها: {total}\n"
            f"⏳ بازی‌های فعال: {active}\n"
            f"📅 بازی‌های امروز: {today}\n"
            f"⭐️ محبوب‌ترین حالت: {popular_mode}"
        )
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("🎮 بازی‌های فعال", callback_data="list_active_games"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        )
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)

    def start_user_search(self, chat_id, user_id, bot):
        """شروع فرآیند جستجوی کاربر"""
        self.pending_requests[user_id] = {
            'action': 'search_user',
            'step': 1
        }

        msg = bot.send_message(
            chat_id,
            "لطفاً شناسه تلگرام یا نام کاربری شخص مورد نظر را وارد کنید:\n\nبرای لغو عملیات، /cancel را بفرستید."
        )

        # ایجاد یک هندلر موقت برای این درخواست
        bot.register_next_step_handler(msg, self.process_user_search, bot)

    def process_user_search(self, message, bot):
        """پردازش درخواست جستجوی کاربر"""
        user_id = message.from_user.id
        chat_id = message.chat.id

        # بررسی دستور /cancel
        if message.text == '/cancel':
            if user_id in self.pending_requests:
                del self.pending_requests[user_id]
            bot.send_message(chat_id, "❌ عملیات جستجو لغو شد.")
            return

        try:
            search_term = message.text.strip()

            # اگر عدد است، به عنوان شناسه جستجو می‌کنیم
            if search_term.isdigit():
                user = self.db.execute(
                    "SELECT * FROM users WHERE telegram_id = ?",
                    (int(search_term),)
                ).fetchone()
            else:
                # جستجو بر اساس نام کاربری
                if search_term.startswith('@'):
                    search_term = search_term[1:]
                user = self.db.execute(
                    "SELECT * FROM users WHERE username LIKE ?",
                    (f"%{search_term}%",)
                ).fetchone()

            if not user:
                bot.send_message(chat_id, "❌ کاربر مورد نظر یافت نشد.")
                # منوی ادمین
                kb = types.InlineKeyboardMarkup()
                kb.add(
                    types.InlineKeyboardButton("🔍 جستجوی مجدد", callback_data="search_user"),
                    types.InlineKeyboardButton("🔙 بازگشت به منوی کاربران", callback_data="admin_users")
                )
                bot.send_message(chat_id, "انتخاب کنید:", reply_markup=kb)
                return

            stats = self.user_mgr.get_stats(user['telegram_id'])

            text = f"""👤 اطلاعات کاربر:

🆔 شناسه: {user['telegram_id']}
👤 نام: {user['first_name']} {user['last_name'] if user['last_name'] else ''}
🔤 نام کاربری: {'@' + user['username'] if user['username'] else 'ندارد'}
📅 تاریخ عضویت: {user['date_joined']}

📊 آمار:
🎮 بازی‌ها: {stats['games_played']}
🔵 حقیقت: {stats['truths_chosen']}
🔴 شجاعت: {stats['dares_chosen']}
⭐️ امتیاز: {stats['points']}
"""

            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("🔍 جستجوی کاربر دیگر", callback_data="search_user"),
                types.InlineKeyboardButton("🔙 بازگشت به منوی کاربران", callback_data="admin_users")
            )
            bot.send_message(chat_id, text, reply_markup=kb)

            # پاکسازی درخواست
            if user_id in self.pending_requests:
                del self.pending_requests[user_id]

        except Exception as e:
            bot.send_message(chat_id, f"❌ خطا در جستجوی کاربر: {str(e)}")
            if user_id in self.pending_requests:
                del self.pending_requests[user_id]

    def list_active_games(self, chat_id, message_id, bot):
        """نمایش لیست بازی‌های فعال"""
        games = self.db.execute(
            """SELECT game_id, creator_id, players, game_mode, difficulty, created_at 
               FROM games 
               WHERE status IN ('waiting', 'started') 
               ORDER BY last_activity DESC 
               LIMIT 10"""
        ).fetchall()

        if not games:
            text = "🎮 هیچ بازی فعالی وجود ندارد."
        else:
            text = "🎮 بازی‌های فعال:\n\n"
            for g in games:
                creator_name = self.user_mgr.get_name(g['creator_id'])
                players_count = len(json.loads(g['players']))
                status_text = 'در انتظار' if players_count == 1 else 'در حال انجام'

                text += f"🆔 {g['game_id']}: {g['game_mode']} (سطح {g['difficulty']})\n"
                text += f"👤 سازنده: {creator_name}\n"
                text += f"👥 تعداد بازیکنان: {players_count}\n"
                text += f"📊 وضعیت: {status_text}\n"
                text += f"🕒 تاریخ شروع: {g['created_at']}\n\n"

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_games"))
        bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)

    def is_action_pending(self, user_id):
        """بررسی اینکه آیا کاربر درخواستی در حال انتظار دارد"""
        return user_id in self.pending_requests

    def get_pending_action(self, user_id):
        """دریافت نوع درخواست در حال انتظار"""
        if user_id in self.pending_requests:
            return self.pending_requests[user_id]['action']
        return None