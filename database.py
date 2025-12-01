# database.py
import sqlite3
from datetime import time

DB_FILE = "bookings.db"

class Database:
    def __init__(self, db_file=DB_FILE):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.cur = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT,
            user_room TEXT,
            month TEXT,
            day INTEGER,
            start TEXT,
            end TEXT
        )
        """)
        self.conn.commit()

    def add_booking(self, user_name, user_room, month, day, start_time, end_time):
        s = start_time.strftime("%H:%M")
        e = end_time.strftime("%H:%M")
        self.cur.execute("""
            INSERT INTO bookings(user_name, user_room, month, day, start, end)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_name, user_room, month, day, s, e))
        self.conn.commit()
        return self.cur.lastrowid

    def is_busy(self, month, day, start_time, end_time):
        """True если есть пересечение с существующей бронью."""
        s_check = start_time
        e_check = end_time
        self.cur.execute("SELECT start, end FROM bookings WHERE month = ? AND day = ?", (month, day))
        rows = self.cur.fetchall()
        for s,e in rows:
            sh, sm = map(int, s.split(":"))
            eh, em = map(int, e.split(":"))
            s_exist = time(sh, sm)
            e_exist = time(eh, em)
            # перекрытие если не (новая закончилась до существующей или новая началась после существующей)
            if not (e_check <= s_exist or s_check >= e_exist):
                return True
        return False

    def get_user_bookings(self, user_name, user_room):
        self.cur.execute("""
            SELECT id, user_room, month, day, start, end FROM bookings
            WHERE user_name = ? AND user_room = ?
            ORDER BY month, day, start
        """, (user_name, user_room))
        rows = self.cur.fetchall()
        return [{"id": r[0], "room": r[1], "month": r[2], "day": r[3], "start": r[4], "end": r[5]} for r in rows]

    def get_bookings_by_date(self, month, day):
        self.cur.execute("""
            SELECT id, user_name, user_room, start, end FROM bookings
            WHERE month = ? AND day = ?
            ORDER BY start
        """, (month, day))
        rows = self.cur.fetchall()
        return [{"id": r[0], "user": r[1], "room": r[2], "start": r[3], "end": r[4]} for r in rows]

    def delete_booking(self, booking_id):
        self.cur.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        self.conn.commit()

    def get_all_bookings(self):
        self.cur.execute("SELECT user_name, user_room, month, day, start, end FROM bookings ORDER BY month, day, start")
        rows = self.cur.fetchall()
        return [{"user": r[0], "room": r[1], "month": r[2], "day": r[3], "start": r[4], "end": r[5]} for r in rows]

    def top5(self):
        self.cur.execute("""
            SELECT user_name, COUNT(*) as cnt FROM bookings
            GROUP BY user_name ORDER BY cnt DESC LIMIT 5
        """)
        return [{"user": r[0], "count": r[1]} for r in self.cur.fetchall()]
