import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton , InlineQuery, CallbackQuery, Message, InlineQueryResultArticle, InputTextMessageContent
from functools import wraps
import json
import logging


logger = logging.getLogger(__name__)


class MembershipChecker:
    def __init__(self, bot, api_url="http://172.245.81.156:3000/api/channel"):
        self.bot = bot
        self.api_url = api_url

    def get_mandatory_channels(self):
        """دریافت لیست کانال‌های اجباری از API"""
        try:
            response = requests.get(self.api_url)
            data = response.json()

            if data.get("ok") and data.get("data"):
                # فقط کانال‌هایی که MandatoryMembership=True است
                return [channel for channel in data["data"] if channel.get("MandatoryMembership", False)]
            return []
        except Exception as e:
            logger.error(f"خطا در دریافت لیست کانال‌ها: {e}")
            return []

    def check_user_membership(self, user_id, channel_id):
        """بررسی عضویت کاربر در یک کانال"""
        try:
            chat_member = self.bot.get_chat_member(f"@{channel_id}", user_id)
            return chat_member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logger.error(f"خطا در بررسی عضویت کانال {channel_id}: {e}")
            return False

    def get_unjoined_channels(self, user_id):
        """دریافت لیست کانال‌هایی که کاربر عضو نیست"""
        mandatory_channels = self.get_mandatory_channels()
        unjoined_channels = []

        for channel in mandatory_channels:
            channel_id = channel.get("id")
            if not self.check_user_membership(user_id, channel_id):
                unjoined_channels.append(channel)

        return unjoined_channels

    def create_join_keyboard(self, unjoined_channels):
        """ساخت کیبورد inline برای عضویت در کانال‌ها"""
        keyboard = InlineKeyboardMarkup()

        for channel in unjoined_channels:
            channel_id = channel.get("id")
            button = InlineKeyboardButton(
                text="📢 عضویت در کانال",
                url=f"https://t.me/{channel_id}"
            )
            keyboard.add(button)

        # دکمه بررسی مجدد
        check_button = InlineKeyboardButton(
            text="✅ بررسی مجدد عضویت",
            callback_data="check_membership"
        )
        keyboard.add(check_button)

        return keyboard


def require_membership(membership_checker):
    """Decorator برای بررسی عضویت اجباری"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not args:
                return func(*args, **kwargs)

            obj = args[0]

            # ✅ InlineQuery
            if isinstance(obj, InlineQuery):
                user_id = obj.from_user.id
                unjoined_channels = membership_checker.get_unjoined_channels(user_id)

                if unjoined_channels:
                    keyboard = membership_checker.create_join_keyboard(unjoined_channels)
                    result = InlineQueryResultArticle(
                        id="membership_required",
                        title="🔒 عضویت در کانال‌ها الزامی است",
                        description="برای استفاده از ربات باید عضو کانال‌ها شوید",
                        input_message_content=InputTextMessageContent(
                            "🔒 کاربر گرامی، لطفاً برای استفاده از ربات عضو کانال‌های زیر شوید:"
                        ),
                        reply_markup=keyboard
                    )

                    membership_checker.bot.answer_inline_query(
                        obj.id,
                        [result],
                        cache_time=1
                    )
                    return

            # ✅ CallbackQuery
            elif isinstance(obj, CallbackQuery):
                user_id = obj.from_user.id
                chat_id = obj.message.chat.id if obj.message else None

                unjoined_channels = membership_checker.get_unjoined_channels(user_id)

                if unjoined_channels:
                    keyboard = membership_checker.create_join_keyboard(unjoined_channels)

                    if chat_id:
                        membership_checker.bot.send_message(
                            chat_id,
                            "🔒 کاربر گرامی، لطفاً برای استفاده از ربات عضو کانال‌های زیر شوید:",
                            reply_markup=keyboard
                        )

                    membership_checker.bot.answer_callback_query(
                        obj.id,
                        "⚠️ برای استفاده از ربات باید عضو کانال‌ها شوید!",
                        show_alert=True
                    )
                    return

            # ✅ Message
            elif isinstance(obj, Message):
                user_id = obj.from_user.id
                chat_id = obj.chat.id

                unjoined_channels = membership_checker.get_unjoined_channels(user_id)

                if unjoined_channels:
                    keyboard = membership_checker.create_join_keyboard(unjoined_channels)

                    membership_checker.bot.send_message(
                        chat_id,
                        "🔒 کاربر گرامی، لطفاً برای استفاده از ربات عضو کانال‌های زیر شوید:",
                        reply_markup=keyboard
                    )
                    return

            # ✅ همه چیز اوکیه، ادامه بده
            return func(*args, **kwargs)

        return wrapper

    return decorator