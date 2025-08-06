from db import Database

class UserManager:
    def __init__(self, db: Database):
        self.db = db

    def register(self, user):
        self.db.execute(
            "INSERT OR IGNORE INTO users(telegram_id, username, first_name, last_name, date_joined) VALUES (?, ?, ?, ?, datetime('now'))",
            (user.id, user.username or '', user.first_name or '', user.last_name or '')
        )
        self.db.execute(
            "UPDATE users SET username=?, first_name=?, last_name=? WHERE telegram_id=?",
            (user.username or '', user.first_name or '', user.last_name or '', user.id)
        )
        self.db.commit()

    def is_registered(self, user_id):
        row = self.db.execute("SELECT 1 FROM users WHERE telegram_id=?", (user_id,)).fetchone()
        return bool(row)

    def is_admin(self, user_id):
        from config import ADMIN_IDS
        return user_id in ADMIN_IDS

    def get_stats(self, user_id):
        row = self.db.execute(
            "SELECT games_played, truths_chosen, dares_chosen, points FROM users WHERE telegram_id=?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else {'games_played':0,'truths_chosen':0,'dares_chosen':0,'points':0}

    def update_stats(self, user_id, truths=0, dares=0, points=0):
        self.db.execute(
            "UPDATE users SET truths_chosen=truths_chosen+?, dares_chosen=dares_chosen+?, points=points+? WHERE telegram_id=?",
            (truths, dares, points, user_id)
        )
        self.db.commit()

    def get_username(self, user_id):
        """دریافت نام کاربری (username) کاربر"""
        try:
            row = self.db.execute(
                "SELECT username FROM users WHERE telegram_id=?",
                (user_id,)
            ).fetchone()

            if row and row['username']:
                return row['username'].strip()
            return None
        except Exception as e:
            return None

    def get_name(self, user_id):
        """دریافت نام کامل کاربر"""
        try:
            row = self.db.execute(
                "SELECT first_name, last_name FROM users WHERE telegram_id=?",
                (user_id,)
            ).fetchone()

            if not row:
                return None

            first = row['first_name'] or ""
            last = row['last_name'] or ""

            # اگر هر دو خالی باشند
            full_name = f"{first} {last}".strip()
            if not full_name:
                return None

            return full_name
        except Exception as e:
            return None

    def get_display_name(self, user_id):
        """دریافت نام نمایشی کاربر (اولویت با username)"""
        try:
            row = self.db.execute(
                "SELECT username, first_name, last_name FROM users WHERE telegram_id=?",
                (user_id,)
            ).fetchone()

            if not row:
                return f"کاربر {user_id}"

            # اولویت با username
            if row['username'] and row['username'].strip():
                return f"@{row['username'].strip()}"

            # در غیر این صورت از نام استفاده کن
            first = row['first_name'] or ""
            last = row['last_name'] or ""
            full_name = f"{first} {last}".strip()

            if full_name:
                return full_name
            else:
                return f"کاربر {user_id}"

        except Exception as e:
            return f"کاربر {user_id}"