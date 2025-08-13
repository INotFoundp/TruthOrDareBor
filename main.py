# main.py
import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton,
    InlineQueryResultArticle, InputTextMessageContent
)
import logging
import threading
import time

# imports داخلی
from config import BOT_TOKEN, DATABASE_PATH, MEMBERSHIP_API_URL, ADMIN_IDS
from database import Database
from user import UserManager
from game import GameManager
from admin import AdminManager
from membership import MembershipChecker, require_membership

# تنظیم logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TruthDareBot:
    def __init__(self):
        self.bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
        self.db = Database(DATABASE_PATH)
        self.user_manager = UserManager(self.db)
        self.game_manager = GameManager(self.db, self.user_manager)
        self.admin_manager = AdminManager(self.db, self.user_manager)
        self.membership_checker = MembershipChecker(self.bot, MEMBERSHIP_API_URL)

        # Game storage برای نگهداری اطلاعات موقت
        self.temp_games = {}
        self.admin_states = {}  # حالت‌های مدیریت ادمین

        self.setup_handlers()
        self.init_sample_questions()

    def init_sample_questions(self):
        """اضافه کردن نمونه سؤالات اولیه"""
        sample_questions = [
            # Truth questions
            ("آخرین باری که دروغ گفتی درباره چه بود؟", "truth", "classic"),
            ("بزرگترین ترست که داری چیست؟", "truth", "classic"),
            ("اگر فقط یک آرزو داشتی چه آرزویی می‌کردی؟", "truth", "classic"),
            ("کدوم شخص مشهور رو دوست داری؟", "truth", "classic"),
            ("بدترین کاری که تا حالا کردی چی بوده؟", "truth", "classic"),

            # Dare questions
            ("20 بار پشت سر هم بپر!", "dare", "classic"),
            ("یک دقیقه مثل سگ راه برو!", "dare", "classic"),
            ("به شخص کناری بگو که عاشقشی!", "dare", "classic"),
            ("10 ثانیه مثل میمون صدا در بیار!", "dare", "classic"),
            ("یک داستان خنده‌دار برای همه تعریف کن!", "dare", "classic"),

            # Challenge mode
            ("بزرگترین اشتباه زندگیت چی بوده؟", "truth", "challenge"),
            ("درباره چه چیزی بیشتر از همه شرم می‌کشی؟", "truth", "challenge"),
            ("5 دقیقه بدون حرف زدن بمان!", "dare", "challenge"),
            ("چشمات رو ببند و 1 دقیقه بدون دیدن حرکت کن!", "dare", "challenge")
        ]

        for question_text, question_type, mode in sample_questions:
            self.admin_manager.add_question(question_text, question_type, mode)

    def setup_handlers(self):
        """تنظیم handler های ربات"""

        @self.bot.message_handler(commands=['start'])
        @require_membership(self.membership_checker)
        def start_command(message):
            self.handle_start(message)

        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            self.handle_help(message)

        @self.bot.message_handler(commands=['stats'])
        @require_membership(self.membership_checker)
        def stats_command(message):
            self.handle_stats(message)

        @self.bot.message_handler(commands=['admin'])
        def admin_command(message):
            self.handle_admin_panel(message)

        @self.bot.callback_query_handler(func=lambda call: True)
        @require_membership(self.membership_checker)
        def callback_query(call):
            self.handle_callback(call)

        @self.bot.inline_handler(func=lambda query: True)
        @require_membership(self.membership_checker)
        def inline_query(query):
            self.handle_inline_query(query)

        @self.bot.message_handler(func=lambda message: True)
        @require_membership(self.membership_checker)
        def handle_message(message):
            self.handle_text_message(message)

    def create_main_keyboard(self):
        """ایجاد کیبورد اصلی"""
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("🎮 بازی جدید"))
        keyboard.add(KeyboardButton("📊 آمار من"), KeyboardButton("❓ راهنما"))
        return keyboard

    def handle_start(self, message):
        """مدیریت دستور /start"""
        user = message.from_user

        # ثبت نام کاربر
        self.user_manager.register_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

        welcome_text = f"""
🎉 سلام {user.first_name}!

به ربات حقیقت یا شجاعت خوش اومدی! 🎭

🎯 برای شروع بازی روی دکمه "بازی جدید" کلیک کن
📊 برای دیدن آمارت از "آمار من" استفاده کن
❓ اگه کمک لازم داری "راهنما" رو بزن

بیا شروع کنیم! 🚀
"""

        self.bot.reply_to(
            message,
            welcome_text,
            reply_markup=self.create_main_keyboard()
        )

    def handle_help(self, message):
        """مدیریت دستور راهنما"""
        help_text = """
📖 راهنمای استفاده از ربات

🎮 <b>نحوه بازی:</b>
1️⃣ روی "بازی جدید" کلیک کن
2️⃣ نوع بازی رو انتخاب کن
3️⃣ بازی رو در گروه یا چت مشترک کن
4️⃣ منتظر بمان تا دوستات بپیوندن
5️⃣ بازی رو شروع کن و لذت ببر!

🎯 <b>انواع بازی:</b>
• کلاسیک: سؤالات معمولی و سرگرم‌کننده
• چالشی: سؤالات سخت‌تر و هیجان‌انگیزتر

💡 <b>امتیازدهی:</b>
• حقیقت: 10 امتیاز
• شجاعت: 15 امتیاز

📞 برای حمایت: @support_channel
"""

        self.bot.reply_to(message, help_text, reply_markup=self.create_main_keyboard())

    def handle_stats(self, message):
        """نمایش آمار کاربر"""
        user_stats = self.user_manager.get_user_stats(message.from_user.id)

        if user_stats:
            stats_text = f"""
📊 <b>آمار شما</b>

👤 نام: {user_stats['first_name']}
🎮 بازی‌های انجام شده: {user_stats['games_played']}
✅ حقیقت‌های پاسخ داده شده: {user_stats['truths_completed']}
💪 شجاعت‌های انجام شده: {user_stats['dares_completed']}
⭐ امتیاز کل: {user_stats['total_score']}
"""
        else:
            stats_text = "❌ آماری برای شما یافت نشد!"

        self.bot.reply_to(message, stats_text, reply_markup=self.create_main_keyboard())

    def handle_text_message(self, message):
        """مدیریت پیام‌های متنی"""
        text = message.text.strip()

        if text == "🎮 بازی جدید":
            self.show_game_modes(message)
        elif text == "📊 آمار من":
            self.handle_stats(message)
        elif text == "❓ راهنما":
            self.handle_help(message)
        else:
            # پیام پیش‌فرض
            self.bot.reply_to(
                message,
                "لطفاً از دکمه‌های موجود استفاده کنید.",
                reply_markup=self.create_main_keyboard()
            )

    def show_game_modes(self, message):
        """نمایش انواع بازی"""
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("🎯 کلاسیک", callback_data="mode_classic")
        )
        keyboard.add(
            InlineKeyboardButton("🔥 چالشی", callback_data="mode_challenge")
        )
        keyboard.add(
            InlineKeyboardButton("🔙 برگشت", callback_data="back_to_main")
        )

        self.bot.reply_to(
            message,
            "🎮 نوع بازی رو انتخاب کن:",
            reply_markup=keyboard
        )

    def handle_callback(self, call):
        """مدیریت callback query ها"""
        try:
            data = call.data
            user_id = call.from_user.id

            # دریافت اطلاعات پیام با بررسی وجود call.message
            message = call.message
            if message:
                message_id = message.message_id
                chat_id = message.chat.id
            else:
                message_id = None
                chat_id = None

            # دریافت inline_message_id برای پیام‌های اینلاین
            inline_message_id = call.inline_message_id

            # انتخاب نوع بازی
            if data.startswith("mode_"):
                mode = data.split("_")[1]
                game_code = self.game_manager.create_game(user_id, mode, chat_id)

                if game_code:
                    # ذخیره اطلاعات موقت
                    self.temp_games[game_code] = {
                        'mode': mode,
                        'creator_id': user_id,
                        'message_id': message_id,
                        'chat_id': chat_id
                    }

                    self.show_share_game(call, game_code, mode)
                else:
                    self.bot.answer_callback_query(call.id, "❌ خطا در ایجاد بازی!")

            # اشتراک‌گذاری بازی
            elif data.startswith("share_"):
                game_code = data.split("_")[1]
                self.handle_share_game(call, game_code)

            # پیوستن به بازی
            elif data.startswith("join_"):
                game_code = data.split("_")[1]
                self.handle_join_game(call, game_code)

            # شروع بازی
            elif data.startswith("start_game_"):
                game_code = data.split("_")[2]
                self.handle_start_game(call, game_code)

            # انتخاب حقیقت یا شجاعت
            elif data.startswith("choice_"):
                parts = data.split("_")
                choice = parts[1]  # truth or dare
                game_code = parts[2]
                self.handle_player_choice(call, choice, game_code)

            # نتیجه عمل
            elif data.startswith("result_"):
                parts = data.split("_")
                result = parts[1]  # done or failed
                game_code = parts[2]
                question_id = parts[3]
                self.handle_action_result(call, result, game_code, question_id)

            # پایان بازی
            elif data.startswith("end_game_"):
                game_code = data.split("_")[2]
                self.handle_end_game(call, game_code)

            # بررسی عضویت
            elif data == "check_membership":
                self.handle_membership_check(call)

            # ادمین
            elif data.startswith("admin_"):
                self.handle_admin_callback(call)

            # مدیریت سؤالات ادمین
            elif data.startswith("question_type_"):
                self.handle_question_type(call)

            elif data.startswith("question_mode_"):
                self.handle_question_mode(call)

            elif data.startswith("questions_list_"):
                self.handle_questions_list(call)

            elif data.startswith("delete_question_"):
                self.handle_delete_question(call)

            # برگشت به منو اصلی
            elif data == "back_to_main":
                self.bot.edit_message_text(
                    "از دکمه‌های زیر استفاده کنید:",
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=self.create_main_keyboard()
                )

            elif data == "back_to_admin":
                self.show_admin_panel_inline(call)

        except Exception as e:
            logger.error(f"Error in callback handler: {e}", exc_info=True)
            self.bot.answer_callback_query(call.id, "❌ خطایی رخ داد!")

    def show_share_game(self, call, game_code, mode):
        """نمایش دکمه اشتراک‌گذاری بازی"""
        mode_names = {
            'classic': '🎯 کلاسیک',
            'challenge': '🔥 چالشی'
        }

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                "🚀 شروع بازی در چت",
                switch_inline_query=f"game_{game_code}"
            )
        )
        keyboard.add(
            InlineKeyboardButton("🔙 برگشت", callback_data="back_to_main")
        )

        text = f"""
🎮 بازی با موفقیت ایجاد شد!

🏷️ کد بازی: <code>{game_code}</code>
🎯 نوع: {mode_names.get(mode, mode)}

برای شروع بازی روی دکمه زیر کلیک کن و چت مورد نظرت رو انتخاب کن 👇
"""

        try:
            if call.inline_message_id:  # اگر پیام inline است
                self.bot.edit_message_text(
                    text,
                    inline_message_id=call.inline_message_id,
                    reply_markup=keyboard
                )
            else:  # پیام معمولی در چت
                self.bot.edit_message_text(
                    text,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Error in show_share_game: {e}")


    def handle_inline_query(self, query):
        """مدیریت inline query ها"""
        try:
            query_text = query.query.strip()

            # اگر کوئری مربوط به بازی خاص است
            if query_text.startswith("game_"):
                game_code = query_text.split("_")[1]
                game_info = self.game_manager.get_game_info(game_code)

                if game_info and game_info['status'] == 'waiting':
                    self.create_game_inline_result(query, game_code, game_info)
                else:
                    self.bot.answer_inline_query(query.id, [], cache_time=1)
            else:
                # منوی اصلی inline
                self.create_main_inline_menu(query)

        except Exception as e:
            logger.error(f"Error in inline query: {e}")
            self.bot.answer_inline_query(query.id, [], cache_time=1)

    def create_game_inline_result(self, query, game_code, game_info):
        """ایجاد نتیجه inline برای بازی"""
        mode_names = {
            'classic': '🎯 کلاسیک',
            'challenge': '🔥 چالشی'
        }

        players = self.game_manager.get_game_players(game_code)
        players_text = "\n".join([f"• {p['first_name']}" for p in players])

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(
                f"🎮 پیوستن به بازی ({len(players)} نفر)",
                callback_data=f"join_{game_code}"
            )
        )

        if len(players) >= 2:
            keyboard.add(
                InlineKeyboardButton(
                    "▶️ شروع بازی",
                    callback_data=f"start_game_{game_code}"
                )
            )

        text = f"""
🎮 <b>بازی حقیقت یا شجاعت</b>

🏷️ کد بازی: <code>{game_code}</code>
🎯 نوع: {mode_names.get(game_info['mode'], game_info['mode'])}
👥 بازیکنان ({len(players)} نفر):

{players_text}

برای پیوستن کلیک کن! 👇
"""

        result = InlineQueryResultArticle(
            id=f"game_{game_code}",
            title=f"🎮 بازی {mode_names.get(game_info['mode'], game_info['mode'])}",
            description=f"بازیکنان: {len(players)} نفر | برای پیوستن کلیک کن!",
            input_message_content=InputTextMessageContent(text),
            reply_markup=keyboard
        )

        self.bot.answer_inline_query(query.id, [result], cache_time=1)

    def create_main_inline_menu(self, query):
        """ایجاد منوی اصلی inline با امکان ساخت مستقیم بازی"""
        results = []

        # ایجاد بازی کلاسیک
        classic_result = InlineQueryResultArticle(
            id="create_classic",
            title="🎯 بازی کلاسیک",
            description="سؤالات معمولی و سرگرم‌کننده",
            input_message_content=InputTextMessageContent(
                "🎯 در حال ایجاد بازی کلاسیک..."
            ),
            reply_markup=self.create_direct_game_keyboard('classic', query.from_user.id)
        )

        # ایجاد بازی چالشی
        challenge_result = InlineQueryResultArticle(
            id="create_challenge",
            title="🔥 بازی چالشی",
            description="سؤالات سخت‌تر و هیجان‌انگیزتر",
            input_message_content=InputTextMessageContent(
                "🔥 در حال ایجاد بازی چالشی..."
            ),
            reply_markup=self.create_direct_game_keyboard('challenge', query.from_user.id)
        )

        results.extend([classic_result, challenge_result])
        self.bot.answer_inline_query(query.id, results, cache_time=1)

    def create_direct_game_keyboard(self, mode, user_id):
        """ایجاد کیبورد برای بازی مستقیم"""
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            "🎮 ایجاد بازی",
            callback_data=f"direct_create_{mode}_{user_id}"
        ))
        return keyboard

    def handle_join_game(self, call, game_code):
        """مدیریت پیوستن به بازی"""
        user_id = call.from_user.id

        # بررسی وجود بازی
        game_info = self.game_manager.get_game_info(game_code)
        if not game_info:
            self.bot.answer_callback_query(call.id, "❌ بازی یافت نشد!", show_alert=True)
            return

        # بررسی وضعیت بازی
        if game_info['status'] != 'waiting':
            self.bot.answer_callback_query(call.id, "❌ بازی قبلاً شروع شده است!", show_alert=True)
            return

        # ثبت نام کاربر
        self.user_manager.register_user(
            telegram_id=user_id,
            username=call.from_user.username,
            first_name=call.from_user.first_name
        )

        # بررسی عضویت قبلی
        existing_player = self.db.execute_query(
            "SELECT id FROM game_players WHERE game_code = ? AND player_id = ?",
            (game_code, user_id), fetch=True
        )

        if existing_player:
            self.bot.answer_callback_query(call.id, "✅ شما قبلاً به این بازی پیوسته‌اید!")
            return

        # اضافه کردن به بازی
        success = self.game_manager.add_player_to_game(game_code, user_id)

        if success:
            if call.inline_message_id:  # اگر inline است
                self.update_game_message(call, game_code)
            else:
                self.update_game_message(call.message, game_code)
            self.bot.answer_callback_query(call.id, "✅ با موفقیت به بازی پیوستید!")


    def handle_start_game(self, call, game_code):
        """مدیریت شروع بازی"""
        user_id = call.from_user.id
        first_player = self.game_manager.start_game(game_code, user_id)

        if first_player:
            # بررسی نوع پیام (معمولی یا اینلاین)
            if call.message:
                # پیام معمولی در چت
                self.show_player_turn(call.message, game_code, first_player)
            elif call.inline_message_id:
                # پیام اینلاین
                self.show_player_turn_inline(call.inline_message_id, game_code, first_player)
            else:
                logger.error("Neither message nor inline_message_id found in handle_start_game")
                self.bot.answer_callback_query(call.id, "❌ خطا در شروع بازی!")
                return

            self.bot.answer_callback_query(call.id, "🎮 بازی شروع شد!")
        else:
            self.bot.answer_callback_query(call.id, "❌ نمی‌توانید این بازی را شروع کنید!", show_alert=True)

    def update_game_message(self, message, game_code):
        """به‌روزرسانی پیام بازی"""
        try:
            game_info = self.game_manager.get_game_info(game_code)
            if not game_info:
                return

            players = self.game_manager.get_game_players(game_code)
            mode_names = {
                'classic': '🎯 کلاسیک',
                'challenge': '🔥 چالشی'
            }

            players_text = "\n".join([f"• {p['first_name']}" for p in players])

            if game_info['status'] == 'waiting':
                keyboard = InlineKeyboardMarkup()
                keyboard.add(
                    InlineKeyboardButton(
                        f"🎮 پیوستن به بازی ({len(players)} نفر)",
                        callback_data=f"join_{game_code}"
                    )
                )

                if len(players) >= 2:
                    keyboard.add(
                        InlineKeyboardButton(
                            "▶️ شروع بازی",
                            callback_data=f"start_game_{game_code}"
                        )
                    )

                text = f"""
🎮 <b>بازی حقیقت یا شجاعت</b>

🏷️ کد بازی: <code>{game_code}</code>
🎯 نوع: {mode_names.get(game_info['mode'], game_info['mode'])}
👥 بازیکنان ({len(players)} نفر):

{players_text}

{'⚠️ حداقل 2 نفر برای شروع لازم است' if len(players) < 2 else '✅ آماده شروع!'}
"""

                if hasattr(message, 'inline_message_id'):  # بررسی پیام inline
                    self.bot.edit_message_text(
                        text,
                        inline_message_id=message.inline_message_id,
                        reply_markup=keyboard
                    )
                else:
                    self.bot.edit_message_text(
                        text,
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        reply_markup=keyboard
                    )
        except Exception as e:
            logger.error(f"Error updating game message: {e}")

    def show_player_turn_inline(self, inline_message_id, game_code, current_player):
        """نمایش نوبت بازیکن برای پیام‌های اینلاین"""
        try:
            game_info = self.game_manager.get_game_info(game_code)
            players = self.game_manager.get_game_players(game_code)

            mode_names = {
                'classic': '🎯 کلاسیک',
                'challenge': '🔥 چالشی'
            }

            keyboard = InlineKeyboardMarkup()

            # دکمه‌های انتخاب برای بازیکن فعلی
            if current_player['player_id'] == game_info['current_player_id']:
                keyboard.add(
                    InlineKeyboardButton("💭 حقیقت", callback_data=f"choice_truth_{game_code}"),
                    InlineKeyboardButton("💪 شجاعت", callback_data=f"choice_dare_{game_code}")
                )

            # دکمه پایان بازی (فقط برای سازنده)
            keyboard.add(
                InlineKeyboardButton("🏁 پایان بازی", callback_data=f"end_game_{game_code}")
            )

            text = f"""
    🎮 <b>بازی در حال انجام</b>

    🏷️ کد بازی: <code>{game_code}</code>
    🎯 نوع: {mode_names.get(game_info['mode'], game_info['mode'])}

    👤 نوبت: <b>{current_player['first_name']}</b>

    انتخاب کن: حقیقت یا شجاعت؟ 🤔
    """

            self.bot.edit_message_text(
                text,
                inline_message_id=inline_message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error showing player turn for inline: {e}")

    def show_player_turn(self, message, game_code, current_player):
        """نمایش نوبت بازیکن برای پیام‌های معمولی"""
        try:
            # بررسی وجود پیام و ویژگی‌های آن
            if message is None or not hasattr(message, 'chat') or not hasattr(message, 'message_id'):
                logger.error(f"Invalid message object in show_player_turn: {message}")
                return

            game_info = self.game_manager.get_game_info(game_code)
            players = self.game_manager.get_game_players(game_code)

            mode_names = {
                'classic': '🎯 کلاسیک',
                'challenge': '🔥 چالشی'
            }

            keyboard = InlineKeyboardMarkup()

            # دکمه‌های انتخاب برای بازیکن فعلی
            if current_player['player_id'] == game_info['current_player_id']:
                keyboard.add(
                    InlineKeyboardButton("💭 حقیقت", callback_data=f"choice_truth_{game_code}"),
                    InlineKeyboardButton("💪 شجاعت", callback_data=f"choice_dare_{game_code}")
                )

            # دکمه پایان بازی (فقط برای سازنده)
            keyboard.add(
                InlineKeyboardButton("🏁 پایان بازی", callback_data=f"end_game_{game_code}")
            )

            text = f"""
    🎮 <b>بازی در حال انجام</b>

    🏷️ کد بازی: <code>{game_code}</code>
    🎯 نوع: {mode_names.get(game_info['mode'], game_info['mode'])}

    👤 نوبت: <b>{current_player['first_name']}</b>

    انتخاب کن: حقیقت یا شجاعت؟ 🤔
    """

            self.bot.edit_message_text(
                text,
                chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error showing player turn: {e}")

    def show_game_results(self, message, game_code):
        """نمایش نتایج نهایی بازی"""
        try:
            players = self.game_manager.get_game_players(game_code)

            # محاسبه امتیازات و آمار هر بازیکن
            results = []
            for player in players:
                # دریافت آمار از جدول کاربران
                user_data = self.db.execute_query(
                    "SELECT truths_completed, dares_completed, total_score FROM users WHERE telegram_id = ?",
                    (player['player_id'],), fetch=True
                )

                if user_data and user_data[0]:
                    truths = user_data[0][0]
                    dares = user_data[0][1]
                    score = user_data[0][2]
                    results.append({
                        'name': player['first_name'],
                        'score': score,
                        'truths': truths,
                        'dares': dares
                    })
                else:
                    results.append({
                        'name': player['first_name'],
                        'score': 0,
                        'truths': 0,
                        'dares': 0
                    })

            # مرتب‌سازی بر اساس امتیاز
            results.sort(key=lambda x: x['score'], reverse=True)

            results_text = "\n".join([
                f"{i + 1}. {r['name']} - {r['score']} امتیاز"
                for i, r in enumerate(results)
            ])

            text = f"""
    🏆 <b>نتایج نهایی بازی</b>

    📊 <b>رتبه‌بندی:</b>
    {results_text}

    🎉 تبریک به همه بازیکنان!

    برای بازی مجدد از دستور /start استفاده کنید.
    """

            self.bot.edit_message_text(
                text,
                chat_id=message.chat.id,
                message_id=message.message_id
            )
        except Exception as e:
            logger.error(f"Error showing game results: {e}")

    def show_game_results_inline(self, inline_message_id, game_code):
        """نمایش نتایج نهایی بازی برای پیام‌های اینلاین"""
        try:
            players = self.game_manager.get_game_players(game_code)

            # محاسبه امتیازات و آمار هر بازیکن
            results = []
            for player in players:
                # دریافت آمار از جدول کاربران
                user_data = self.db.execute_query(
                    "SELECT truths_completed, dares_completed, total_score FROM users WHERE telegram_id = ?",
                    (player['player_id'],), fetch=True
                )

                if user_data and user_data[0]:
                    truths = user_data[0][0]
                    dares = user_data[0][1]
                    score = user_data[0][2]
                    results.append({
                        'name': player['first_name'],
                        'score': score,
                        'truths': truths,
                        'dares': dares
                    })
                else:
                    results.append({
                        'name': player['first_name'],
                        'score': 0,
                        'truths': 0,
                        'dares': 0
                    })

            # مرتب‌سازی بر اساس امتیاز
            results.sort(key=lambda x: x['score'], reverse=True)

            results_text = "\n".join([
                f"{i + 1}. {r['name']} - {r['score']} امتیاز"
                for i, r in enumerate(results)
            ])

            text = f"""
        🏆 <b>نتایج نهایی بازی</b>

        📊 <b>رتبه‌بندی:</b>
        {results_text}

        🎉 تبریک به همه بازیکنان!

        برای بازی مجدد از دستور /start استفاده کنید.
        """


            self.bot.edit_message_text(
                text,
                inline_message_id=inline_message_id
            )
        except Exception as e:
            logger.error(f"Error in show_game_results_inline: {e}")

    def handle_membership_check(self, call):
        """بررسی مجدد عضویت"""
        user_id = call.from_user.id
        unjoined_channels = self.membership_checker.get_unjoined_channels(user_id)

        if not unjoined_channels:
            self.bot.answer_callback_query(call.id, "✅ عضویت شما تأیید شد!")
            # اجرای عمل اصلی که قبلاً مسدود شده بود
            self.bot.edit_message_text(
                "✅ عضویت شما تأیید شد! حالا می‌توانید از ربات استفاده کنید.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=self.create_main_keyboard()
            )
        else:
            keyboard = self.membership_checker.create_join_keyboard(unjoined_channels)
            self.bot.answer_callback_query(
                call.id,
                "❌ هنوز عضو همه کانال‌ها نیستید!",
                show_alert=True
            )

    def show_question(self, message, game_code, question, choice, player_id):
        """نمایش سؤال به بازیکن برای پیام‌های معمولی"""
        try:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✅ انجام شد", callback_data=f"result_done_{game_code}_{question['id']}"),
                InlineKeyboardButton("❌ انجام نشد", callback_data=f"result_failed_{game_code}_{question['id']}")
            )

            choice_text = "💭 حقیقت" if choice == "truth" else "💪 شجاعت"

            # دریافت نام بازیکن
            players = self.game_manager.get_game_players(game_code)
            current_player_name = next(
                (p['first_name'] for p in players if p['player_id'] == player_id),
                "نامشخص"
            )

            text = f"""
    🎮 <b>سؤال برای {current_player_name}</b>

    {choice_text}: <b>{question['text']}</b>

    پس از انجام (یا عدم انجام) روی یکی از دکمه‌های زیر کلیک کن:
    """

            self.bot.edit_message_text(
                text,
                chat_id=message.chat.id,
                message_id=message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error in show_question: {e}")

    def show_question_inline(self, inline_message_id, game_code, question, choice, player_id):
        """نمایش سؤال به بازیکن برای پیام‌های اینلاین"""
        try:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✅ انجام شد", callback_data=f"result_done_{game_code}_{question['id']}"),
                InlineKeyboardButton("❌ انجام نشد", callback_data=f"result_failed_{game_code}_{question['id']}")
            )

            choice_text = "💭 حقیقت" if choice == "truth" else "💪 شجاعت"

            # دریافت نام بازیکن
            players = self.game_manager.get_game_players(game_code)
            current_player_name = next(
                (p['first_name'] for p in players if p['player_id'] == player_id),
                "نامشخص"
            )

            text = f"""
    🎮 <b>سؤال برای {current_player_name}</b>

    {choice_text}: <b>{question['text']}</b>

    پس از انجام (یا عدم انجام) روی یکی از دکمه‌های زیر کلیک کن:
    """

            self.bot.edit_message_text(
                text,
                inline_message_id=inline_message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error in show_question_inline: {e}")

    def handle_action_result(self, call, result, game_code, question_id):
        """مدیریت نتیجه اقدام"""
        try:
            user_id = call.from_user.id
            game_info = self.game_manager.get_game_info(game_code)

            # بررسی نوبت
            if game_info['current_player_id'] != user_id:
                self.bot.answer_callback_query(call.id, "❌ این نوبت شما نیست!")
                return

            completed = result == "done"

            # به‌روزرسانی آمار
            if completed:
                # دریافت نوع سؤال
                question_data = self.db.execute_query(
                    "SELECT question_type FROM questions WHERE id = ?",
                    (question_id,), fetch=True
                )

                if question_data:
                    question_type = question_data[0][0]
                    if question_type == 'truth':
                        self.user_manager.update_user_stats(user_id, truths_completed=1, score_add=10)
                    else:
                        self.user_manager.update_user_stats(user_id, dares_completed=1, score_add=15)

            # انتقال نوبت
            next_player = self.game_manager.next_turn(game_code)

            if next_player:
                # تشخیص نوع پیام (معمولی یا اینلاین)
                if call.inline_message_id:  # پیام اینلاین
                    self.show_player_turn_inline(
                        inline_message_id=call.inline_message_id,
                        game_code=game_code,
                        current_player=next_player
                    )
                elif call.message:  # پیام معمولی
                    self.show_player_turn(
                        message=call.message,
                        game_code=game_code,
                        current_player=next_player
                    )
                else:
                    logger.error("Neither message nor inline_message_id in handle_action_result")
                    self.bot.answer_callback_query(call.id, "❌ خطا در انتقال نوبت!")
                    return

                result_text = "انجام شد ✅" if completed else "انجام نشد ❌"
                points = "+10" if completed and question_data and question_data[0][
                    0] == 'truth' else "+15" if completed else "+0"
                self.bot.answer_callback_query(
                    call.id,
                    f"{result_text} {points} امتیاز!"
                )
            else:
                self.bot.answer_callback_query(call.id, "❌ خطا در انتقال نوبت!")
        except Exception as e:
            logger.error(f"Error in handle_action_result: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در پردازش نتیجه!")

    def handle_player_choice(self, call, choice, game_code):
        """مدیریت انتخاب بازیکن"""
        try:
            user_id = call.from_user.id
            game_info = self.game_manager.get_game_info(game_code)

            # بررسی نوبت
            if game_info['current_player_id'] != user_id:
                self.bot.answer_callback_query(call.id, "❌ نوبت شما نیست!", show_alert=True)
                return

            # دریافت سؤال تصادفی
            question = self.game_manager.get_random_question(choice, game_info['mode'])

            if not question:
                self.bot.answer_callback_query(call.id, "❌ سؤالی یافت نشد!")
                return

            # ثبت اقدام
            self.game_manager.record_action(game_code, user_id, question['id'], choice)

            # نمایش سؤال - تشخیص نوع پیام (معمولی یا اینلاین)
            if call.inline_message_id:  # پیام اینلاین
                self.show_question_inline(
                    inline_message_id=call.inline_message_id,
                    game_code=game_code,
                    question=question,
                    choice=choice,
                    player_id=user_id
                )
            elif call.message:  # پیام معمولی
                self.show_question(
                    message=call.message,
                    game_code=game_code,
                    question=question,
                    choice=choice,
                    player_id=user_id
                )
            else:
                logger.error("No message or inline_message_id found in handle_player_choice")
                self.bot.answer_callback_query(call.id, "❌ خطا در نمایش سوال!")

            choice_text = "حقیقت" if choice == "truth" else "شجاعت"
            self.bot.answer_callback_query(call.id, f"✅ {choice_text} انتخاب شد!")
        except Exception as e:
            logger.error(f"Error in handle_player_choice: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در پردازش انتخاب شما!")

    def handle_end_game(self, call, game_code):
        """مدیریت پایان بازی"""
        try:
            user_id = call.from_user.id
            game_info = self.game_manager.get_game_info(game_code)

            # بررسی دسترسی (فقط سازنده)
            if game_info['creator_id'] != user_id:
                self.bot.answer_callback_query(call.id, "❌ فقط سازنده بازی می‌تواند آن را پایان دهد!")
                return

            # پایان دادن به بازی
            success = self.game_manager.finish_game(game_code)

            if success:
                # نمایش نتایج نهایی - تشخیص نوع پیام
                if call.inline_message_id:  # پیام اینلاین
                    self.show_game_results_inline(
                        inline_message_id=call.inline_message_id,
                        game_code=game_code
                    )
                elif call.message:  # پیام معمولی
                    self.show_game_results(
                        message=call.message,
                        game_code=game_code
                    )
                else:
                    logger.error("Neither message nor inline_message_id in handle_end_game")
                    self.bot.answer_callback_query(call.id, "❌ خطا در پایان بازی!")
                    return

                self.bot.answer_callback_query(call.id, "🏁 بازی پایان یافت!")
            else:
                self.bot.answer_callback_query(call.id, "❌ خطا در پایان دادن به بازی!")
        except Exception as e:
            logger.error(f"Error in handle_end_game: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در پایان دادن به بازی!")


    def handle_admin_panel(self, message):
        """مدیریت پنل ادمین"""
        if not self.user_manager.is_admin(message.from_user.id):
            self.bot.reply_to(message, "❌ شما به این بخش دسترسی ندارید!")
            return

        self.show_admin_panel_inline(message)

    def show_admin_panel_inline(self, source):
        """نمایش پنل ادمین به صورت inline"""
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("📊 آمار کلی", callback_data="admin_general_stats"),
            InlineKeyboardButton("👥 کاربران برتر", callback_data="admin_top_users")
        )
        keyboard.add(
            InlineKeyboardButton("➕ افزودن سؤال", callback_data="admin_add_question"),
            InlineKeyboardButton("📝 مدیریت سؤالات", callback_data="admin_manage_questions")
        )
        keyboard.add(
            InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search_user")
        )

        if isinstance(source, telebot.types.CallbackQuery):
            self.bot.edit_message_text(
                "🔧 <b>پنل مدیریت</b>\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
                chat_id=source.message.chat.id,
                message_id=source.message.message_id,
                reply_markup=keyboard
            )
        else:
            self.bot.reply_to(
                source,
                "🔧 <b>پنل مدیریت</b>\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
                reply_markup=keyboard
            )

    def handle_admin_callback(self, call):
        """مدیریت callback های ادمین"""
        if not self.user_manager.is_admin(call.from_user.id):
            self.bot.answer_callback_query(call.id, "❌ دسترسی مجاز نیست!")
            return

        data = call.data.replace("admin_", "")

        if data == "general_stats":
            self.show_general_stats(call)
        elif data == "top_users":
            self.show_top_users(call)
        elif data == "add_question":
            self.start_add_question_process(call)
        elif data == "manage_questions":
            self.show_questions_management(call)
        elif data == "search_user":
            self.start_user_search_process(call)

    def show_general_stats(self, call):
        """نمایش آمار کلی"""
        try:
            stats = self.admin_manager.get_general_stats()

            text = f"""
📊 <b>آمار کلی ربات</b>

👥 کل کاربران: {stats.get('total_users', 0)}
🎮 کاربران فعال: {stats.get('active_users', 0)}
🎯 کل بازی‌ها: {stats.get('total_games', 0)}
⚡ بازی‌های فعال: {stats.get('active_games', 0)}

❓ کل سؤالات: {stats.get('total_questions', 0)}
💭 سؤالات حقیقت: {stats.get('truth_questions', 0)}
💪 سؤالات شجاعت: {stats.get('dare_questions', 0)}
"""

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("🔙 برگشت به پنل ادمین", callback_data="back_to_admin")
            )

            self.bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error showing general stats: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در دریافت آمار!")

    def show_top_users(self, call):
        """نمایش کاربران برتر"""
        try:
            top_users = self.admin_manager.get_top_users(10)

            if top_users:
                users_text = "\n".join([
                    f"{i + 1}. {user['first_name']} - {user['total_score']} امتیاز ({user['games_played']} بازی)"
                    for i, user in enumerate(top_users)
                ])
            else:
                users_text = "هیچ کاربر فعالی یافت نشد."

            text = f"""
🏆 <b>کاربران برتر</b>

{users_text}
"""

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("🔙 برگشت به پنل ادمین", callback_data="back_to_admin")
            )

            self.bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error showing top users: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در دریافت کاربران برتر!")

    def start_add_question_process(self, call):
        """شروع فرآیند اضافه کردن سؤال"""
        try:
            # ذخیره وضعیت ادمین
            admin_id = call.from_user.id
            self.admin_states[admin_id] = {'action': 'add_question', 'step': 'type'}

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("💭 حقیقت", callback_data="question_type_truth"),
                InlineKeyboardButton("💪 شجاعت", callback_data="question_type_dare")
            )
            keyboard.add(
                InlineKeyboardButton("🔙 انصراف", callback_data="back_to_admin")
            )

            self.bot.edit_message_text(
                "➕ <b>افزودن سؤال جدید</b>\n\nنوع سؤال را انتخاب کنید:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error starting add question process: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در شروع فرآیند!")

    def handle_question_type(self, call):
        """مدیریت انتخاب نوع سؤال"""
        try:
            admin_id = call.from_user.id
            question_type = call.data.split("_")[2]

            # ذخیره نوع سؤال
            self.admin_states[admin_id] = {
                'action': 'add_question',
                'step': 'mode',
                'type': question_type
            }

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("🎯 کلاسیک", callback_data="question_mode_classic"),
                InlineKeyboardButton("🔥 چالشی", callback_data="question_mode_challenge")
            )
            keyboard.add(
                InlineKeyboardButton("🔙 برگشت", callback_data="admin_add_question")
            )

            self.bot.edit_message_text(
                "➕ <b>افزودن سؤال جدید</b>\n\nحالت (مُد) بازی را انتخاب کنید:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error handling question type: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در انتخاب نوع سؤال!")

    def handle_question_mode(self, call):
        """مدیریت انتخاب حالت سؤال"""
        try:
            admin_id = call.from_user.id
            question_mode = call.data.split("_")[2]

            # ذخیره حالت سؤال
            self.admin_states[admin_id]['mode'] = question_mode
            self.admin_states[admin_id]['step'] = 'text'

            self.bot.edit_message_text(
                "➕ <b>افزودن سؤال جدید</b>\n\nمتن سؤال را ارسال کنید:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )

            # ثبت مرحله بعدی برای دریافت متن
            self.bot.register_next_step_handler(call.message, self.save_new_question)
        except Exception as e:
            logger.error(f"Error handling question mode: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در انتخاب حالت سؤال!")

    def save_new_question(self, message):
        """ذخیره سؤال جدید"""
        try:
            admin_id = message.from_user.id

            # بررسی وضعیت ادمین
            if admin_id not in self.admin_states or self.admin_states[admin_id]['action'] != 'add_question':
                self.bot.reply_to(message, "❌ فرآیند افزودن سؤال منقضی شده است!")
                return

            question_text = message.text.strip()
            if not question_text:
                self.bot.reply_to(message, "❌ متن سؤال نمی‌تواند خالی باشد!")
                return

            # دریافت نوع و حالت از وضعیت
            state = self.admin_states[admin_id]
            question_type = state.get('type')
            question_mode = state.get('mode')

            if not question_type or not question_mode:
                self.bot.reply_to(message, "❌ اطلاعات ناقص است!")
                return

            # افزودن سؤال
            success = self.admin_manager.add_question(question_text, question_type, question_mode)

            if success:
                self.bot.reply_to(message, "✅ سؤال با موفقیت افزوده شد!")
            else:
                self.bot.reply_to(message, "❌ خطا در افزودن سؤال!")

            # حذف وضعیت
            del self.admin_states[admin_id]

        except Exception as e:
            logger.error(f"Error saving new question: {e}")
            self.bot.reply_to(message, "❌ خطا در ذخیره سؤال!")

    def show_questions_management(self, call):
        """نمایش مدیریت سؤالات"""
        try:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("💭 سؤالات حقیقت", callback_data="questions_list_truth"),
                InlineKeyboardButton("💪 سؤالات شجاعت", callback_data="questions_list_dare")
            )
            keyboard.add(
                InlineKeyboardButton("🎯 سؤالات کلاسیک", callback_data="questions_list_classic"),
                InlineKeyboardButton("🔥 سؤالات چالشی", callback_data="questions_list_challenge")
            )
            keyboard.add(
                InlineKeyboardButton("🔙 برگشت به پنل ادمین", callback_data="back_to_admin")
            )

            self.bot.edit_message_text(
                "📝 <b>مدیریت سؤالات</b>\n\nکدام دسته را می‌خواهید مشاهده کنید؟",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error showing questions management: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در نمایش مدیریت سؤالات!")

    def handle_questions_list(self, call):
        """مدیریت نمایش لیست سؤالات"""
        try:
            list_type = call.data.split("_")[2]

            # تعیین نوع فیلتر
            filter_type = None
            filter_mode = None

            if list_type in ['truth', 'dare']:
                filter_type = list_type
            elif list_type in ['classic', 'challenge']:
                filter_mode = list_type

            # دریافت سؤالات
            questions = self.admin_manager.get_questions_list(
                question_type=filter_type,
                mode=filter_mode
            )

            if not questions:
                text = f"❌ هیچ سؤالی در دسته '{list_type}' یافت نشد."
                keyboard = InlineKeyboardMarkup()
                keyboard.add(
                    InlineKeyboardButton("🔙 برگشت", callback_data="admin_manage_questions")
                )
                self.bot.edit_message_text(
                    text,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboard
                )
                return

            # نمایش سؤالات
            text = f"📝 <b>لیست سؤالات ({list_type})</b>\n\n"
            for i, q in enumerate(questions):
                text += f"{i + 1}. {q['text']} (نوع: {q['type']}, مد: {q['mode']})\n"

            keyboard = InlineKeyboardMarkup()
            for i, q in enumerate(questions):
                keyboard.add(
                    InlineKeyboardButton(
                        f"❌ حذف سؤال {i + 1}",
                        callback_data=f"delete_question_{q['id']}"
                    )
                )
            keyboard.add(
                InlineKeyboardButton("🔙 برگشت", callback_data="admin_manage_questions")
            )

            self.bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error handling questions list: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در نمایش لیست سؤالات!")

    def handle_delete_question(self, call):
        """مدیریت حذف سؤال"""
        try:
            question_id = int(call.data.split("_")[2])
            success = self.admin_manager.delete_question(question_id)

            if success:
                self.bot.answer_callback_query(call.id, "✅ سؤال با موفقیت حذف شد!")
                # بازگشت به لیست سؤالات
                self.show_questions_management(call)
            else:
                self.bot.answer_callback_query(call.id, "❌ خطا در حذف سؤال!")
        except Exception as e:
            logger.error(f"Error deleting question: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در حذف سؤال!")

    def start_user_search_process(self, call):
        """شروع فرآیند جستجوی کاربر"""
        try:
            admin_id = call.from_user.id
            self.admin_states[admin_id] = {'action': 'search_user'}

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("🔙 انصراف", callback_data="back_to_admin")
            )

            self.bot.edit_message_text(
                "🔍 <b>جستجوی کاربر</b>\n\nآیدی عددی یا نام کاربری را ارسال کنید:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )

            # ثبت پیام انتظار پاسخ
            self.bot.register_next_step_handler(call.message, self.process_user_search)
        except Exception as e:
            logger.error(f"Error starting user search: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در شروع جستجو!")

    def process_user_search(self, message):
        """پردازش جستجوی کاربر"""
        if not self.user_manager.is_admin(message.from_user.id):
            return

        search_term = message.text.strip()
        users = self.user_manager.search_user(search_term)

        if users:
            results_text = ""
            for user in users[:10]:  # محدود به 10 نتیجه
                results_text += f"""
    👤 <b>{user[2]}</b> (@{user[1] or 'ندارد'})
    🆔 آیدی: <code>{user[0]}</code>
    🎮 بازی‌ها: {user[3]} | 💭 حقیقت: {user[4]} | 💪 شجاعت: {user[5]}
    ⭐ امتیاز: {user[6]}
    ➖➖➖➖➖➖➖➖➖➖
    """

            text = f"🔍 <b>نتایج جستجو برای:</b> {search_term}\n\n{results_text}"
        else:
            text = f"❌ هیچ کاربری با عبارت '{search_term}' یافت نشد."

        self.bot.reply_to(message, text)

    def run(self):
        """اجرای ربات"""
        logger.info("Bot is starting...")

        # پاک کردن webhook
        self.bot.remove_webhook()

        # شروع polling
        try:
            self.bot.polling(
                none_stop=True,
                interval=1,
                timeout=20,
                long_polling_timeout=20
            )
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)
            self.run()  # راه‌اندازی مجدد


if __name__ == "__main__":
    # اجرای ربات
    bot = TruthDareBot()
    bot.run()
