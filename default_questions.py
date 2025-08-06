import sqlite3
from config import DB_PATH  # اطمینان حاصل کن که فایل config.py مسیر DB_PATH رو درست داره

DEFAULT_TRUTH_QUESTIONS = [
    # Easy
    {"question_text": "آیا تا حالا نمره دروغ به خانواده‌ات گفتی؟", "difficulty": "easy", "category": "family"},
    {"question_text": "آخرین باری که گریه کردی کی بود؟", "difficulty": "easy", "category": "emotions"},
    {"question_text": "آیا تا به حال گوشی یکی رو بی‌اجازه چک کردی؟", "difficulty": "easy", "category": "privacy"},
    {"question_text": "آیا تا حالا تقلب کردی؟", "difficulty": "easy", "category": "school"},
    {"question_text": "آیا از کسی که در حال حاضر در جمع هست خوشت میاد؟", "difficulty": "easy", "category": "love"},

    # Medium
    {"question_text": "ترسناک‌ترین چیزی که تا به حال تجربه کردی چی بوده؟", "difficulty": "medium", "category": "fear"},
    {"question_text": "آیا تابه‌حال به کسی که دوستت داشته نه گفتی؟", "difficulty": "medium",
     "category": "relationship"},
    {"question_text": "اگه بتونی یه چیز از گذشته‌ات عوض کنی چی خواهد بود؟", "difficulty": "medium",
     "category": "personal"},
    {"question_text": "آیا تا حالا به کسی حسادت کردی؟ چرا؟", "difficulty": "medium", "category": "feelings"},
    {"question_text": "کدوم دروغی که گفتی هنوز عذاب وجدان داری براش؟", "difficulty": "medium", "category": "regret"},

    # Hard
    {"question_text": "بزرگ‌ترین گناهی که کردی چی بوده؟", "difficulty": "hard", "category": "confession"},
    {"question_text": "آیا تا حالا عاشق شدی ولی به کسی نگفتی؟", "difficulty": "hard", "category": "love"},
    {"question_text": "اگه کسی بخواد بزرگ‌ترین رازت رو بدونه، چی می‌گی؟", "difficulty": "hard", "category": "secret"},
    {"question_text": "بدترین خیانتی که دیدی یا کردی چی بوده؟", "difficulty": "hard", "category": "betrayal"},
    {"question_text": "چه چیزی از خودت بیشتر از همه پنهان می‌کنی؟", "difficulty": "hard", "category": "self"},
]

DEFAULT_DARE_QUESTIONS = [
    # Easy
    {"question_text": "صدای گربه یا سگ دربیار!", "difficulty": "easy", "category": "fun"},
    {"question_text": "با لهجه ترکی/جنوبی یه جمله بگو!", "difficulty": "easy", "category": "accent"},
    {"question_text": "یه دور اتاق بدو!", "difficulty": "easy", "category": "physical"},
    {"question_text": "یه آهنگ بخون (آرومم قبوله!)", "difficulty": "easy", "category": "music"},
    {"question_text": "با چشم بسته یکی از بازیکن‌ها رو لمس کن و حدس بزن کیه.", "difficulty": "easy",
     "category": "guess"},

    # Medium
    {"question_text": "اسم کسی که دوستش داری رو زمزمه کن.", "difficulty": "medium", "category": "love"},
    {"question_text": "عکس آخر توی گالریت رو نشون بده.", "difficulty": "medium", "category": "privacy"},
    {"question_text": "به مدت 1 دقیقه فقط با دست اشاره حرف بزن.", "difficulty": "medium", "category": "silent"},
    {"question_text": "یه وویس ضبط کن و تو گروه بفرست که بگی 'من خیلی خجالتی‌ام!'", "difficulty": "medium",
     "category": "voice"},
    {"question_text": "با یکی از بازیکن‌ها دست بده و تا ۱۵ ثانیه ول نکن.", "difficulty": "medium",
     "category": "awkward"},

    # Hard
    {"question_text": "یه پیام خجالت‌آور به مخاطب خاصی بفرست (و نشون بده).", "difficulty": "hard", "category": "crazy"},
    {"question_text": "یه چیز مسخره بخور یا بنوش.", "difficulty": "hard", "category": "gross"},
    {"question_text": "اسم کسی رو که ازش بدت میاد بگو (واقعاً).", "difficulty": "hard", "category": "bold"},
    {"question_text": "به یکی پیام بده و اعتراف کن که دوستش داری (حتی اگه واقعیت نداره).", "difficulty": "hard",
     "category": "risk"},
    {"question_text": "به انتخاب جمع یه حرکت خنده‌دار یا خجالت‌آور انجام بده.", "difficulty": "hard",
     "category": "group_dare"},
]


def insert_defaults():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Truth
    cursor.execute("SELECT COUNT(*) FROM truth_questions")
    if cursor.fetchone()[0] == 0:
        for q in DEFAULT_TRUTH_QUESTIONS:
            cursor.execute("""
                INSERT INTO truth_questions (question_text, difficulty, category)
                VALUES (?, ?, ?)
            """, (q["question_text"], q["difficulty"], q["category"]))
        print(f"✅ {len(DEFAULT_TRUTH_QUESTIONS)} truth questions inserted.")

    # Dare
    cursor.execute("SELECT COUNT(*) FROM dare_questions")
    if cursor.fetchone()[0] == 0:
        for q in DEFAULT_DARE_QUESTIONS:
            cursor.execute("""
                INSERT INTO dare_questions (question_text, difficulty, category)
                VALUES (?, ?, ?)
            """, (q["question_text"], q["difficulty"], q["category"]))
        print(f"✅ {len(DEFAULT_DARE_QUESTIONS)} dare questions inserted.")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    insert_defaults()
