# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, time
from database import Database

app = Flask(__name__)
app.secret_key = "replace_this_with_random_secret"  # поменяй перед деплоем

db = Database()

# Months (как ты просил)
MONTHS = ["Ноябрь 2025", "Декабрь 2025", "Январь 2026", "Февраль 2026",
          "Март 2026", "Апрель 2026", "Май 2026", "Июнь 2026"]

# интервалы
ONE_HOUR_SLOTS = [ "07:00","08:00","09:00","10:00","11:00","12:00",
                   "13:00","14:00","15:00","16:00","17:00","18:00",
                   "19:00","20:00","21:00","22:00","23:00" ]

TWO_HOUR_SLOTS = [
    ("07:00","09:00"),("09:00","11:00"),("11:00","13:00"),
    ("13:00","15:00"),("15:00","17:00"),("17:00","19:00"),
    ("19:00","21:00"),("21:00","23:00"),
]

THREE_HOUR_SLOTS = [
    ("07:00","10:00"),("10:00","13:00"),("13:00","16:00"),
    ("16:00","19:00"),("19:00","22:00"),
]

# ---------- helper ----------
def parse_hm(s):
    return datetime.strptime(s, "%H:%M").time()

def allowed_range(start, end):
    return time(7,0) <= start < end <= time(23,0)

# ---------- routes ----------
@app.route("/")
def index():
    return render_template("index.html")

# identify user (simple form)
@app.route("/identify", methods=["POST"])
def identify():
    name = request.form.get("name","").strip()
    room = request.form.get("room","").strip()
    if not name or not room:
        flash("Введите имя и номер комнаты.")
        return redirect(url_for("index"))
    session["user_name"] = name
    session["user_room"] = f"Комната {room}"
    return redirect(url_for("book_month"))

# booking: choose month
@app.route("/book")
def book_month():
    if "user_name" not in session:
        return redirect(url_for("index"))
    return render_template("book_month.html", months=MONTHS)

# choose day inside month
@app.route("/book/<month>")
def book_day(month):
    if "user_name" not in session:
        return redirect(url_for("index"))
    if month not in MONTHS:
        flash("Неверный месяц.")
        return redirect(url_for("book_month"))
    return render_template("book_day.html", month=month)

# choose duration after selecting month/day and room stored in session
@app.route("/book/<month>/<int:day>", methods=["POST"])
def choose_duration(month, day):
    if "user_name" not in session:
        return redirect(url_for("index"))
    room = request.form.get("room","").strip()
    if not room:
        flash("Введите номер комнаты.")
        return redirect(url_for("book_day", month=month))
    session["room"] = f"Комната {room}"
    session["month"] = month
    session["day"] = day
    return render_template("choose_duration.html", month=month, day=day)

# show slots depending on duration
@app.route("/slots/<int:duration>")
def show_slots(duration):
    if "user_name" not in session or "month" not in session:
        return redirect(url_for("index"))
    month = session["month"]
    day = session["day"]
    slots = []
    if duration == 1:
        for s in ONE_HOUR_SLOTS:
            sh = int(s.split(":")[0]); eh = sh+1
            slots.append((f"{sh:02d}:00", f"{eh:02d}:00"))
    elif duration == 2:
        slots = TWO_HOUR_SLOTS
    elif duration == 3:
        slots = THREE_HOUR_SLOTS
    else:
        flash("Неверная длительность.")
        return redirect(url_for("choose_duration", month=month, day=day))
    # filter free slots
    free = []
    for s,e in slots:
        s_t = parse_hm(s); e_t = parse_hm(e)
        if not db.is_busy(month, day, s_t, e_t):
            free.append((s,e))
    return render_template("choose_slot.html", month=month, day=day, duration=duration, slots=free)

# custom range
@app.route("/custom_range", methods=["GET","POST"])
def custom_range():
    if "user_name" not in session or "month" not in session:
        return redirect(url_for("index"))
    month = session["month"]; day = session["day"]
    if request.method=="POST":
        rng = request.form.get("range","")
        try:
            p1,p2 = rng.split("-")
            s = parse_hm(p1.strip()); e = parse_hm(p2.strip())
        except:
            flash("Неверный формат. Пример: 12:00-15:00")
            return redirect(url_for("custom_range"))
        if not allowed_range(s,e):
            flash("Можно бронировать только в диапазоне 07:00–23:00.")
            return redirect(url_for("custom_range"))
        if db.is_busy(month, day, s, e):
            flash("Этот диапазон уже занят.")
            return redirect(url_for("custom_range"))
        # create
        db.add_booking(session["user_name"], session["room"], month, day, s, e)
        flash("Бронь подтверждена.")
        return redirect(url_for("my_bookings"))
    return render_template("custom_range.html")

# book a specific slot (POST)
@app.route("/book_slot", methods=["POST"])
def book_slot():
    if "user_name" not in session or "month" not in session:
        return redirect(url_for("index"))
    month = session["month"]; day = session["day"]
    start = request.form.get("start"); end = request.form.get("end")
    s = parse_hm(start); e = parse_hm(end)
    if not allowed_range(s,e):
        flash("Можно бронировать только в диапазоне 07:00–23:00.")
        return redirect(url_for("show_slots", duration=1))
    if db.is_busy(month, day, s, e):
        flash("Слот уже занят.")
        return redirect(url_for("show_slots", duration=1))
    db.add_booking(session["user_name"], session["room"], month, day, s, e)
    flash("Бронь подтверждена.")
    return redirect(url_for("my_bookings"))

# my bookings
@app.route("/my_bookings")
def my_bookings():
    if "user_name" not in session or "room" not in session:
        return redirect(url_for("index"))
    rows = db.get_user_bookings(session["user_name"], session["room"])
    return render_template("my_bookings.html", rows=rows)

# cancel booking
@app.route("/cancel/<int:bid>", methods=["POST"])
def cancel(bid):
    db.delete_booking(bid)
    flash("Бронь удалена.")
    return redirect(url_for("my_bookings"))

# schedule: choose month -> day -> show bookings
@app.route("/schedule")
def schedule():
    return render_template("schedule.html", months=MONTHS)

@app.route("/schedule/<month>/<int:day>")
def schedule_day(month, day):
    rows = db.get_bookings_by_date(month, day)
    return render_template("schedule.html", months=MONTHS, month=month, day=day, rows=rows)

# support
@app.route("/support")
def support():
    return render_template("support.html")

# top5
@app.route("/top5")
def top5():
    data = db.top5()
    return render_template("top5.html", data=data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
