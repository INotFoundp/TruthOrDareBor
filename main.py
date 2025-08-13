import logging
import json
import telebot
from telebot import types
from config import BOT_TOKEN
from db import Database
from user import UserManager
from game import GameManager
from admin import AdminManager
from membership import MembershipChecker, require_membership

# پیکربندی لاگر
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# نمونه‌سازی ماژول‌ها
db = Database()
user_mgr = UserManager(db)
game_mgr = GameManager(db)
bot = telebot.TeleBot(BOT_TOKEN)

# ایجاد سیستم بررسی عضویت
membership_checker = MembershipChecker(bot)


# /start handler - بدون بررسی عضویت
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_mgr.register(message.from_user)
    welcome_text = "سلام! به ربات حقیقت و شجاعت خوش آمدید! 🎮\n\nاز دکمه‌های زیر استفاده کنید:"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🎮 بازی جدید"),
        types.KeyboardButton("📊 آمار من"),
        types.KeyboardButton("📜 راهنما"),
        types.KeyboardButton("👥 دعوت دوستان")
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


# Admin command - با بررسی عضویت
@bot.message_handler(commands=['admin'])
@require_membership(membership_checker)
def handle_admin_command(message):
    user_id = message.from_user.id
    if not user_mgr.is_admin(user_id):
        return
    # نمایش منوی ادمین با پیام جدید
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📝 مدیریت سؤالات", callback_data="admin_questions"),
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
        types.InlineKeyboardButton("🎮 آمار بازی‌ها", callback_data="admin_games"),
    )
    bot.send_message(message.chat.id, "🔐 پنل مدیریت:", reply_markup=kb)


# Main menu callbacks - با بررسی عضویت
@bot.callback_query_handler(func=lambda c: c.data.startswith('btn_'))
@require_membership(membership_checker)
def main_menu_handler(call):
    data = call.data
    user_id = call.from_user.id
    try:
        if data == "btn_new_game":
            kb = types.InlineKeyboardMarkup()
            kb.row(
                types.InlineKeyboardButton("🎲 کلاسیک", callback_data="new_game_classic"),
                types.InlineKeyboardButton("🔥 چالشی +18", callback_data="new_game_challenge"),
                types.InlineKeyboardButton("🎭 عملکردی", callback_data="new_game_performance")
            )
            bot.edit_message_text("🎮 لطفاً نوع بازی را انتخاب کنید:",
                                  call.message.chat.id, call.message.message_id,
                                  reply_markup=kb)
        elif data == "btn_stats":
            stats = user_mgr.get_stats(user_id)
            text = (
                f"📊 آمار شما:"
                f"🎮 بازی‌ها: {stats['games_played']}"
                f"🔵 حقیقت: {stats['truths_chosen']}"
                f"🔴 شجاعت: {stats['dares_chosen']}"
                f"⭐️ امتیاز: {stats['points']}"
            )
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        elif data == "btn_help":
            bot.edit_message_text("📖 راهنما:برای شروع روی 🎮 بازی جدید کلیک کنید.",
                                  call.message.chat.id, call.message.message_id)
        elif data == "btn_invite":
            link = f"https://t.me/{bot.get_me().username}?start={user_id}"
            bot.send_message(call.message.chat.id, f"🔗 لینک دعوت:{link}")
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"main_menu error: {e}")
        bot.answer_callback_query(call.id, "خطا رخ داد، دوباره تلاش کنید.", show_alert=True)


# Main menu text handler - با بررسی عضویت
@bot.message_handler(func=lambda m: m.text in ["🎮 بازی جدید", "📊 آمار من", "📜 راهنما", "👥 دعوت دوستان"])
@require_membership(membership_checker)
def main_menu_text_handler(message):
    text = message.text
    chat_id = message.chat.id

    if text == "🎮 بازی جدید":
        # همان چیزی که در قبل در btn_new_game داشتیم:
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("🎲 کلاسیک", callback_data="new_game_classic"),
            types.InlineKeyboardButton("🔥 چالشی +18", callback_data="new_game_challenge"),
            types.InlineKeyboardButton("🎭 عملکردی", callback_data="new_game_performance")
        )
        bot.send_message(chat_id, "🎮 لطفاً نوع بازی را انتخاب کنید:", reply_markup=kb)

    elif text == "📊 آمار من":
        stats = user_mgr.get_stats(message.from_user.id)
        resp = f"📊 آمار شما:\n🎮 بازی‌ها: {stats['games_played']}\n🔵 حقیقت: {stats['truths_chosen']}\n🔴 شجاعت: {stats['dares_chosen']}\n⭐️ امتیاز: {stats['points']}"
        bot.send_message(chat_id, resp)

    elif text == "📜 راهنما":
        bot.send_message(chat_id, "📖 راهنما: برای شروع روی 🎮 بازی جدید بزنید و مراحل را دنبال کنید.")

    elif text == "👥 دعوت دوستان":
        link = f"https://t.me/{bot.get_me().username}?start={message.from_user.id}"
        bot.send_message(chat_id, f"🔗 لینک دعوت:\n{link}")


# New game mode selection - با بررسی عضویت
@bot.callback_query_handler(func=lambda c: c.data.startswith('new_game_'))
@require_membership(membership_checker)
def new_game_handler(call):
    try:
        mode = call.data.split('_')[-1]
        kb = types.InlineKeyboardMarkup()
        kb.row(
            types.InlineKeyboardButton("آسان", callback_data=f"set_diff_{mode}_easy"),
            types.InlineKeyboardButton("متوسط", callback_data=f"set_diff_{mode}_medium"),
        )
        kb.row(types.InlineKeyboardButton("سخت", callback_data=f"set_diff_{mode}_hard"),
               types.InlineKeyboardButton("مختلط", callback_data=f"set_diff_{mode}_mixed")
               )
        bot.edit_message_text("🎯 لطفاً سطح دشواری را انتخاب کنید:",
                              call.message.chat.id, call.message.message_id,
                              reply_markup=kb)
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"new_game error: {e}")


# Set difficulty and create game - با بررسی عضویت
@bot.callback_query_handler(func=lambda c: c.data.startswith('set_diff_'))
@require_membership(membership_checker)
def set_diff_handler(call):
    try:
        # استخراج mode و difficulty
        _, _, mode, diff = call.data.split('_')
        creator = call.from_user.id
        game_id = game_mgr.create_game(creator, diff, mode)

        # کیبورد با دکمه‌ی switch_inline_query برای ارسال بازی در چت/گروه
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton(
                "🚀 شروع بازی در چت",
                switch_inline_query=f"{mode}_{diff}"
            ),
            types.InlineKeyboardButton(
                "👥 دعوت دوستان",
                callback_data=f"invite_game_{game_id}"
            )
        )

        # پیام جدید در همان چت/گروه
        bot.send_message(
            call.message.chat.id,
            f"🎮 بازی با مود «{mode}» و سختی «{diff}» آماده است! برای ارسال در دکمه کلیک کنید.",
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"set_diff error: {e}")
        bot.answer_callback_query(call.id, "خطا در ایجاد بازی.", show_alert=True)


# Inline Query handler - با بررسی عضویت
@bot.inline_handler(lambda q: True)
@require_membership(membership_checker)
def inline_query_handler(inline_query):
    try:
        # برای inline query فقط سه گزینه اصلی با سطح مختلط نمایش داده می‌شود
        results = []
        import time
        current_time = int(time.time())

        # مود کلاسیک - مختلط
        classic_id = f"classic_mixed_{current_time}"
        classic_kb = types.InlineKeyboardMarkup()
        game_id_classic = game_mgr.create_game(inline_query.from_user.id, "mixed", "classic")
        classic_kb.row(
            types.InlineKeyboardButton("👥 پیوستن به بازی", callback_data=f"join_game_{game_id_classic}"))
        classic_content = types.InputTextMessageContent(
            f"🎮 بازی حقیقت و شجاعت - مود کلاسیک\n👤 {inline_query.from_user.first_name}\n👥 1 نفر"
        )
        classic_result = types.InlineQueryResultArticle(
            id=classic_id,
            title="🎲 بازی کلاسیک",
            description="حالت استاندارد بازی با سوالات متنوع",
            input_message_content=classic_content,
            reply_markup=classic_kb
        )
        results.append(classic_result)

        # مود چالشی - مختلط
        challenge_id = f"challenge_mixed_{current_time}"
        challenge_kb = types.InlineKeyboardMarkup()
        game_id_challenge = game_mgr.create_game(inline_query.from_user.id, "mixed", "challenge")
        challenge_kb.row(
            types.InlineKeyboardButton("👥 پیوستن به بازی", callback_data=f"join_game_{game_id_challenge}"))
        challenge_content = types.InputTextMessageContent(
            f"🎮 بازی حقیقت و شجاعت - مود چالشی +18\n👤 {inline_query.from_user.first_name}\n👥 1 نفر"
        )
        challenge_result = types.InlineQueryResultArticle(
            id=challenge_id,
            title="🔥 بازی چالشی +18",
            description="سوالات و چالش‌های هیجان‌انگیز",
            input_message_content=challenge_content,
            reply_markup=challenge_kb
        )
        results.append(challenge_result)

        # مود عملکردی - مختلط
        performance_id = f"performance_mixed_{current_time}"
        performance_kb = types.InlineKeyboardMarkup()
        game_id_performance = game_mgr.create_game(inline_query.from_user.id, "mixed", "performance")
        performance_kb.row(
            types.InlineKeyboardButton("👥 پیوستن به بازی", callback_data=f"join_game_{game_id_performance}"))
        performance_content = types.InputTextMessageContent(
            f"🎮 بازی حقیقت و شجاعت - مود عملکردی\n👤 {inline_query.from_user.first_name}\n👥 1 نفر"
        )
        performance_result = types.InlineQueryResultArticle(
            id=performance_id,
            title="🎭 بازی عملکردی",
            description="چالش‌های نمایشی و اجرایی",
            input_message_content=performance_content,
            reply_markup=performance_kb
        )
        results.append(performance_result)

        bot.answer_inline_query(inline_query.id, results, cache_time=1)

    except Exception as e:
        logger.error(f"inline_query error: {e}")
        # در صورت خطا، پیام مناسب به کاربر نشان بده
        result = types.InlineQueryResultArticle(
            id="error",
            title="خطای داخلی",
            description="لطفاً مجدداً تلاش کنید",
            input_message_content=types.InputTextMessageContent("خطایی رخ داد. لطفاً مجدداً تلاش کنید.")
        )
        bot.answer_inline_query(inline_query.id, [result], cache_time=5)

# Game selection handler - با بررسی عضویت
@bot.callback_query_handler(func=lambda c: c.data.startswith('game_'))
@require_membership(membership_checker)
def game_selection_handler(call):
    try:
        # تشخیص نوع بازی
        mode = call.data.split('_')[1]  # گرفتن مود بازی از callback_data

        # ایجاد کیبورد برای انتخاب سطح دشواری
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("آسان", callback_data=f"set_diff_{mode}_easy"),
            types.InlineKeyboardButton("متوسط", callback_data=f"set_diff_{mode}_medium"),
        )
        kb.row(
            types.InlineKeyboardButton("سخت", callback_data=f"set_diff_{mode}_hard"),
            types.InlineKeyboardButton("مختلط", callback_data=f"set_diff_{mode}_mixed")
        )

        # ویرایش پیام برای نمایش گزینه‌های سطح دشواری
        bot.edit_message_text(
            f"🎯 لطفاً سطح دشواری بازی {mode} را انتخاب کنید:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"game_selection error: {e}")
        bot.answer_callback_query(call.id, "خطا در انتخاب بازی، دوباره تلاش کنید.", show_alert=True)


# Game flow: join, start, action, complete, end_game - با بررسی عضویت
@bot.callback_query_handler(
    func=lambda c: any(
        c.data.startswith(prefix)
        for prefix in ['join_game_', 'start_game_', 'action_', 'complete_', 'end_game_']
    )
)
@require_membership(membership_checker)
def game_flow_handler(call):
    data = call.data.split('_')
    user_id = call.from_user.id

    # Helper to edit messages (normal or inline)
    def edit_text(text, kb=None):
        if call.message:
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=kb
            )
        else:
            bot.edit_message_text(
                text,
                inline_message_id=call.inline_message_id,
                reply_markup=kb
            )

    # Helper function to get player names safely
    def get_player_names(player_ids):
        """دریافت نام بازیکنان با کنترل خطا"""
        names = []
        for uid in player_ids:
            # استفاده از تابع get_display_name که هم username و هم name را چک می‌کند
            display_name = user_mgr.get_display_name(uid)
            names.append(display_name)
        return ', '.join(names) if names else "هیچ بازیکنی"

    try:
        # JOIN GAME
        if data[0] == 'join' and data[1] == 'game':
            gid = int(data[2])
            # بررسی بیشتر برای اطمینان از وضعیت بازی
            row = db.execute("SELECT status FROM games WHERE game_id=?", (gid,)).fetchone()

            if not row:
                bot.answer_callback_query(call.id, "❌ بازی یافت نشد.", show_alert=True)
                return

            if row['status'] != 'waiting':
                bot.answer_callback_query(call.id, "❌ بازی قبلا شروع شده یا تمام شده است.", show_alert=True)
                return

            if not user_mgr.is_registered(user_id):
                bot.answer_callback_query(call.id, "⚠️ لطفا /start را بزنید.", show_alert=True)
                return

            added = game_mgr.add_player(gid, user_id)
            bot.answer_callback_query(
                call.id,
                "✅ به بازی پیوستید!" if added else "❌ شما قبلا وارد بازی شدید.",
                show_alert=True
            )

            # بارگذاری مجدد لیست بازیکنان از دیتابیس
            updated = db.execute(
                "SELECT players FROM games WHERE game_id=?", (gid,)
            ).fetchone()
            players = json.loads(updated['players']) if updated['players'] else []

            # ساخت رشته خوانا از نام بازیکنان با کنترل خطا
            names = get_player_names(players)

            # ساخت کیبورد پویا
            kb = types.InlineKeyboardMarkup()
            kb.row(types.InlineKeyboardButton("👥 پیوستن", callback_data=f"join_game_{gid}"))

            # فقط اگر حداقل ۲ بازیکن دارند، دکمه شروع را اضافه کن
            if len(players) > 1:
                kb.row(types.InlineKeyboardButton("🚀 شروع بازی", callback_data=f"start_game_{gid}"))
            else:
                # پیامی موقتی به کاربر اضافه کن تا بداند منتظر عضو بیشتر است
                bot.answer_callback_query(call.id, "👥 منتظر بازیکن بیشتر برای شروع بازی...", show_alert=False)

            edit_text(f"👥 بازیکنان: {names}", kb)

        # START GAME
        elif data[0] == 'start' and data[1] == 'game':
            gid = int(data[2])

            # فراخوانی لیست بازیکنان
            row = db.execute("SELECT creator_id, players FROM games WHERE game_id=?", (gid,)).fetchone()
            if not row:
                bot.answer_callback_query(call.id, "❌ بازی یافت نشد.", show_alert=True)
                return

            players = json.loads(row['players']) if row['players'] else []

            # چک تعداد
            if len(players) < 2:
                bot.answer_callback_query(call.id, "❌ برای شروع بازی به حداقل ۲ بازیکن نیاز است.", show_alert=True)
                return

            # چک اینکه فقط سازنده بتواند بازی را شروع کند
            if user_id != row['creator_id']:
                bot.answer_callback_query(call.id, "❌ فقط سازنده می‌تواند بازی را شروع کند.", show_alert=True)
                return

            game_mgr.start_game(gid)
            first_row = db.execute("SELECT current_player FROM games WHERE game_id=?", (gid,)).fetchone()
            if not first_row:
                bot.answer_callback_query(call.id, "❌ خطا در شروع بازی.", show_alert=True)
                return

            first = first_row['current_player']
            first_name = user_mgr.get_display_name(first)

            # دکمه‌های حقیقت/شجاعت و پایان بازی
            kb = types.InlineKeyboardMarkup()
            kb.row(
                types.InlineKeyboardButton("🔵 حقیقت", callback_data=f"action_{gid}_truth"),
                types.InlineKeyboardButton("🔴 شجاعت", callback_data=f"action_{gid}_dare")
            )
            kb.row(types.InlineKeyboardButton("🛑 پایان بازی", callback_data=f"end_game_{gid}"))
            bot.answer_callback_query(call.id, "✅ بازی شروع شد!")
            edit_text(f"🎯 نوبت: {first_name}\nحقیقت یا شجاعت؟", kb)

        # ACTION (truth/dare)
        elif data[0] == 'action':
            gid, act = int(data[1]), data[2]
            # اعتبارسنجی وضعیت بازی و نوبت
            game_row = db.execute(
                "SELECT current_player, status FROM games WHERE game_id=?", (gid,)
            ).fetchone()
            if not game_row or game_row['status'] != 'started':
                bot.answer_callback_query(call.id, "❌ بازی فعالی نیست.", show_alert=True)
                return
            if user_id != game_row['current_player']:
                bot.answer_callback_query(call.id, "❌ نوبت شما نیست.", show_alert=True)
                return

            # ۱) دریافت اطلاعات کامل بازی (شامل game_mode)
            game_info = db.execute(
                "SELECT difficulty, game_mode FROM games WHERE game_id=?", (gid,)
            ).fetchone()

            if not game_info:
                bot.answer_callback_query(call.id, "❌ اطلاعات بازی یافت نشد.", show_alert=True)
                return

            diff = game_info['difficulty']
            game_mode = game_info['game_mode']

            # ۲) دریافت سوال مناسب با game_mode
            q = game_mgr.get_random_question(act, diff, game_mode)

            # ۳) ثبت اکشن و دریافت history_id
            hid = game_mgr.record_action(gid, user_id, act, q)

            # آماده‌سازی دکمه‌های کامل کردن اکشن
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("✅ انجام شد", callback_data=f"complete_{gid}_{hid}_1"),
                types.InlineKeyboardButton("❌ انجام نشد", callback_data=f"complete_{gid}_{hid}_0")
            )
            bot.answer_callback_query(call.id)
            edit_text(f"❓ {q}", kb)

        # COMPLETE ACTION
        elif data[0] == 'complete':
            # data = ['complete', gid_str, hid_str, flag_str]
            if len(data) < 4:
                logger.error(f"Invalid callback_data format: {data}")
                bot.answer_callback_query(call.id, "⚠️ خطای داخلی، دوباره تلاش کنید.", show_alert=True)
                return

            gid_str, hid_str, flag_str = data[1], data[2], data[3]

            # چک مقدماتی
            if not hid_str or hid_str.lower() == 'none':
                logger.error(f"Invalid history_id in callback_data: {data}")
                bot.answer_callback_query(call.id, "⚠️ خطای داخلی، دوباره تلاش کنید.", show_alert=True)
                return

            # تبدیل ایمن
            try:
                gid = int(gid_str)
                hid = int(hid_str)
                done_flag = (flag_str == '1')
            except ValueError:
                logger.error(f"Invalid numeric values in callback_data: {data}")
                bot.answer_callback_query(call.id, "⚠️ خطای داخلی، دوباره تلاش کنید.", show_alert=True)
                return

            # بررسی مالک رکورد
            rec = db.execute(
                "SELECT player_id, action_type FROM game_history WHERE history_id=?",
                (hid,)
            ).fetchone()
            if not rec:
                bot.answer_callback_query(call.id, "❌ رکورد پیدا نشد.", show_alert=True)
                return
            if user_id != rec['player_id']:
                bot.answer_callback_query(call.id, "❌ شما اجازه ندارید.", show_alert=True)
                return

            # تکمیل اکشن و به‌روزرسانی آمار
            game_mgr.complete_action(hid, done_flag)
            typ = rec['action_type']
            pts = (5 if typ == 'truth' else 10) if done_flag else 0
            user_mgr.update_stats(
                user_id,
                truths=(1 if typ == 'truth' else 0),
                dares=(1 if typ == 'dare' else 0),
                points=pts
            )

            # نوبت بعدی
            nxt = game_mgr.next_turn(gid)
            nxt_name = user_mgr.get_display_name(nxt)

            kb = types.InlineKeyboardMarkup()
            kb.row(
                types.InlineKeyboardButton("🔵 حقیقت", callback_data=f"action_{gid}_truth"),
                types.InlineKeyboardButton("🔴 شجاعت", callback_data=f"action_{gid}_dare")
            )
            kb.row(types.InlineKeyboardButton("🛑 پایان بازی", callback_data=f"end_game_{gid}"))
            bot.answer_callback_query(call.id)
            edit_text(
                f"✅ نتیجه: {'انجام شد' if done_flag else 'انجام نشد'}\n"
                f"🎯 نوبت: {nxt_name}",
                kb
            )

        # END GAME
        elif data[0] == 'end' and data[1] == 'game':
            gid = int(data[2])
            game = db.execute("SELECT creator_id FROM games WHERE game_id=?", (gid,)).fetchone()
            if not game:
                bot.answer_callback_query(call.id, "❌ بازی یافت نشد.", show_alert=True)
                return

            if user_id != game['creator_id']:
                bot.answer_callback_query(call.id, "❌ فقط سازنده می‌تواند بازی را پایان دهد.", show_alert=True)
                return

            # فراخوانی متد end_game که هم status رو می‌بندد و هم آمار users.games_played رو بالا می‌برد
            success = game_mgr.end_game(gid)
            if not success:
                bot.answer_callback_query(call.id, "⚠️ خطا در پایان بازی، دوباره تلاش کنید.", show_alert=True)
                return

            bot.answer_callback_query(call.id, "🛑 بازی با موفقیت پایان یافت.")
            edit_text("🔚 بازی به پایان رسید. برای شروع دوباره /start را بزنید.")

    except ValueError as ve:
        logger.error(f"ValueError in game_flow: {ve}")
        bot.answer_callback_query(call.id, "⚠️ خطا در پردازش اطلاعات، دوباره تلاش کنید.", show_alert=True)
    except json.JSONDecodeError as je:
        logger.error(f"JSON decode error in game_flow: {je}")
        bot.answer_callback_query(call.id, "⚠️ خطا در خواندن اطلاعات بازی، دوباره تلاش کنید.", show_alert=True)
    except Exception as e:
        logger.error(f"game_flow error: {e}")
        bot.answer_callback_query(call.id, "⚠️ خطایی رخ داد، دوباره تلاش کنید.", show_alert=True)


# هندلر برای منوی ادمین
admin_mgr = AdminManager(db, user_mgr)

@bot.callback_query_handler(func=lambda c: c.data == 'btn_admin')
@require_membership(membership_checker)
def admin_panel(call):
    if not user_mgr.is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ دسترسی ندارید.", show_alert=True)
        return
    admin_mgr.show_main_menu(call.message.chat.id, call.message.message_id, bot)
    bot.answer_callback_query(call.id)


# هندلر callback‌های پنل ادمین - با بررسی عضویت
@bot.callback_query_handler(
    func=lambda c: (
            c.data.startswith('admin_')  # منوی اصلی ادمین
            or c.data.startswith('add_question_')  # افزودن سؤال
            or c.data.startswith('set_question_diff_')  # انتخاب سطح دشواری
            or c.data.startswith('list_questions_')  # لیست/پیمایش سؤالات
            or c.data in [
                'question_stats',
                'user_stats', 'active_users', 'search_user',
                'list_active_games'
            ]
    )
)
@require_membership(membership_checker)
def admin_callbacks(call):
    admin_mgr.handle_callback(call, bot)


# Handler برای callback بررسی مجدد عضویت
@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def check_membership_callback(call):
    """بررسی مجدد عضویت کاربر"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    # بررسی وضعیت عضویت
    unjoined_channels = membership_checker.get_unjoined_channels(user_id)

    if unjoined_channels:
        # هنوز در همه کانال‌ها عضو نشده
        keyboard = membership_checker.create_join_keyboard(unjoined_channels)
        try:
            bot.edit_message_text(
                "❌ هنوز در همه کانال‌ها عضو نشده‌اید. لطفاً عضو شوید:",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        except:
            # اگر پیام قابل ویرایش نبود
            bot.send_message(
                chat_id,
                "❌ هنوز در همه کانال‌ها عضو نشده‌اید. لطفاً عضو شوید:",
                reply_markup=keyboard
            )
    else:
        # در همه کانال‌ها عضو شده
        try:
            bot.edit_message_text(
                "✅ تبریک! شما در همه کانال‌های اجباری عضو شدید.\nحالا می‌توانید از تمام امکانات ربات استفاده کنید.",
                chat_id=chat_id,
                message_id=call.message.message_id
            )
        except:
            bot.send_message(
                chat_id,
                "✅ تبریک! شما در همه کانال‌های اجباری عضو شدید.\nحالا می‌توانید از تمام امکانات ربات استفاده کنید."
            )

    # پاسخ به callback
    bot.answer_callback_query(call.id)


# اجرای ربات
if __name__ == '__main__':
    print("🤖 ربات شروع شد...")
    print("برای توقف ربات Ctrl+C را فشار دهید")

    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"خطا در اجرای ربات: {e}")
    except KeyboardInterrupt:
        print("\n🛑 ربات متوقف شد.")