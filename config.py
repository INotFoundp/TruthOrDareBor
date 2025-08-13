import logging

BOT_TOKEN = "7316154018:AAGBmMBIn7fszYdQQhEsOPxDasrYxWZGj8M"
DATABASE_PATH = "bot_database.db"

# لیست ادمین‌ها (Telegram User ID)
ADMIN_IDS = [6602283244,1333298972,1470641798]  # ID های ادمین‌ها را اینجا قرار دهید

# API برای چک کردن کانال‌ها
MEMBERSHIP_API_URL = "http://172.245.81.156:3000/api/channel"

# تنظیمات لاگ‌گیری پیشرفته
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s',
    handlers=[
        logging.FileHandler("bot_debug.log"),
        logging.StreamHandler()
    ]
)