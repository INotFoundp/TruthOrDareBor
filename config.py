import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "truth_dare.db")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
GAME_TIMEOUT = int(os.getenv("GAME_TIMEOUT", "3600")) # seconds
CHANNEL_API_URL = "http://172.245.81.156:3000/api/channel"