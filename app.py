from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from datetime import datetime
import os
import uuid

app = Flask(__name__)
app.secret_key = "tractor-booking-secret-key"
DB = "/tmp/database.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'farmer'
    );

    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        model TEXT,
        rent REAL NOT NULL,
        description TEXT,
        image TEXT,
        available INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        equipment_id INTEGER NOT NULL,
        booking_date TEXT NOT NULL,
        duration INTEGER NOT NULL,
        location TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(equipment_id) REFERENCES equipment(id)
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        method TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        payment_id TEXT,
        created_at TEXT,
        FOREIGN KEY(booking_id) REFERENCES bookings(id)
    );
    """)

    admin = conn.execute("SELECT id FROM users WHERE email=?", ("admin@gmail.com",)).fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO users(name,phone,email,password,role) VALUES(?,?,?,?,?)",
            ("Administrator", "9999999999", "admin@gmail.com", "admin123", "admin")
        )

    count = conn.execute("SELECT COUNT(*) AS c FROM equipment").fetchone()["c"]
    if count == 0:
        equipment = [
            ("Mahindra Tractor", "Tractor", "575 DI", 900, "Powerful tractor suitable for ploughing and farming work.", "tractor.jpg", 1),
            ("Rotavator", "Tillage", "Fieldking", 700, "Used for soil preparation and seed-bed preparation.", "rotavator.jpg", 1),
            ("Cultivator", "Tillage", "Shaktiman", 550, "Suitable for loosening and aerating agricultural soil.", "cultivator.jpg", 1),
            ("Seed Drill", "Sowing", "KS Agrotech", 650, "Machine for accurate and efficient seed sowing.", "seed-drill.jpg", 1),
            ("Plough", "Tillage", "Mould Board", 500, "Heavy-duty plough for primary soil preparation.", "plough.jpg", 1),
            ("Water Tanker", "Irrigation", "5000 Litre", 800, "Water tanker for farm irrigation and water transport.", "tanker.jpg", 1),
        ]
        conn.executemany(
            "INSERT INTO equipment(name,category,model,rent,description,image,available) VALUES(?,?,?,?,?,?,?)",
            equipment
        )
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def index():
    conn = get_db()
    equipment = conn.execute("SELECT * FROM equipment WHERE available=1 ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("index.html", equipment=equipment)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        phone = request.form["phone"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users(name,phone,email,password) VALUES(?,?,?,?)",
                (name, phone, email, password)
            )
            conn.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?", (email, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("index"))

        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/equipment/<int:eid>")
def equipment_details(eid):
    conn = get_db()
    item = conn.execute("SELECT * FROM equipment WHERE id=?", (eid,)).fetchone()
    conn.close()
    if not item:
        flash("Equipment not found.", "danger")
        return redirect(url_for("index"))
    return render_template("equipment_details.html", item=item)

@app.route("/book/<int:eid>", methods=["GET", "POST"])
@login_required
def book(eid):
    conn = get_db()
    item = conn.execute("SELECT * FROM equipment WHERE id=?", (eid,)).fetchone()
    conn.close()

    if not item or not item["available"]:
        flash("Equipment is currently unavailable.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        booking_date = request.form["booking_date"]
        duration = int(request.form["duration"])
        location = request.form["location"].strip()

        if not location:
            flash("Please enter farm location.", "warning")
            return render_template("booking.html", item=item)

        conn = get_db()
        conflict = conn.execute("""
            SELECT id FROM bookings
            WHERE equipment_id=? AND booking_date=? AND status IN ('Pending','Approved')
        """, (eid, booking_date)).fetchone()

        if conflict:
            conn.close()
            flash("This equipment is already booked for that date.", "danger")
            return render_template("booking.html", item=item)

        cur = conn.execute("""
            INSERT INTO bookings(user_id,equipment_id,booking_date,duration,location,status,created_at)
            VALUES(?,?,?,?,?,'Pending',?)
        """, (
            session["user_id"], eid, booking_date, duration, location,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        flash("Booking request submitted successfully. Please complete payment.", "success")
        return redirect(url_for("payment", bid=cur.lastrowid))

    return render_template("booking.html", item=item)

@app.route("/my-bookings")
@login_required
def my_bookings():
    conn = get_db()
    bookings = conn.execute("""
        SELECT b.*, e.name AS equipment_name, e.rent,
               (e.rent * b.duration) AS total
        FROM bookings b
        JOIN equipment e ON e.id=b.equipment_id
        WHERE b.user_id=?
        ORDER BY b.id DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return render_template("my_bookings.html", bookings=bookings)


@app.route("/payment/<int:bid>", methods=["GET", "POST"])
@login_required
def payment(bid):
    conn = get_db()
    booking = conn.execute("""
        SELECT b.*, e.name AS equipment_name, e.rent,
               (e.rent * b.duration) AS total
        FROM bookings b JOIN equipment e ON e.id=b.equipment_id
        WHERE b.id=? AND b.user_id=?
    """, (bid, session["user_id"])).fetchone()
    existing = conn.execute(
        "SELECT * FROM payments WHERE booking_id=? ORDER BY id DESC LIMIT 1", (bid,)
    ).fetchone()
    conn.close()

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("my_bookings"))

    if existing and existing["status"] == "Paid":
        return render_template("payment.html", booking=booking, payment=existing,
                               razorpay_key=os.getenv("RAZORPAY_KEY_ID", ""))

    return render_template("payment.html", booking=booking, payment=existing,
                           razorpay_key=os.getenv("RAZORPAY_KEY_ID", ""))

@app.route("/payment/success/<int:bid>", methods=["POST"])
@login_required
def payment_success(bid):
    payment_id = request.form.get("payment_id", "").strip()
    if not payment_id:
        payment_id = "DEMO-" + uuid.uuid4().hex[:12].upper()

    conn = get_db()
    booking = conn.execute(
        "SELECT b.*, e.rent FROM bookings b JOIN equipment e ON e.id=b.equipment_id "
        "WHERE b.id=? AND b.user_id=?", (bid, session["user_id"])
    ).fetchone()
    if not booking:
        conn.close()
        flash("Booking not found.", "danger")
        return redirect(url_for("my_bookings"))

    amount = booking["rent"] * booking["duration"]
    conn.execute(
        "INSERT INTO payments(booking_id,amount,method,status,payment_id,created_at) "
        "VALUES(?,?,?,?,?,?)",
        (bid, amount, "Razorpay", "Paid", payment_id,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    flash("Payment successful! Booking payment has been recorded.", "success")
    return redirect(url_for("my_bookings"))

@app.route("/chatbot", methods=["POST"])
def chatbot():
    message = request.json.get("message", "").strip().lower() if request.is_json else ""
    if not message:
        return {"reply": "Please type your question."}

    answers = [
        (("hello", "hi", "hey", "namaste"), "Hello! 👋 I’m AgriBook Assistant. How can I help you?"),
        (("book", "booking"), "To book equipment, open an equipment card, choose a date, duration and farm location, then submit the booking request."),
        (("payment", "pay", "razorpay"), "After submitting a booking, you can pay the total amount through the Razorpay payment gateway. Test mode can be used for your college demo."),
        (("cancel",), "Pending bookings can be cancelled from the My Bookings page."),
        (("tractor", "equipment", "machine"), "We provide tractors, rotavators, cultivators, seed drills, ploughs and water tankers."),
        (("admin",), "The admin can approve/reject bookings and add or delete equipment from the dashboard."),
        (("price", "rent", "rate", "cost"), "Equipment rent is shown per day on each equipment details/booking page."),
        (("contact", "help", "support"), "For project support, please contact the system administrator through your college project team."),
    ]
    for keywords, reply in answers:
        if any(k in message for k in keywords):
            return {"reply": reply}
    return {"reply": "I can help with bookings, equipment, rent, payments, cancellations and admin features. Try asking: “How do I book a tractor?”"}

@app.route("/cancel/<int:bid>")
@login_required
def cancel_booking(bid):
    conn = get_db()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE id=? AND user_id=?", (bid, session["user_id"])
    ).fetchone()
    if booking and booking["status"] == "Pending":
        conn.execute("UPDATE bookings SET status='Cancelled' WHERE id=?", (bid,))
        conn.commit()
        flash("Booking cancelled.", "success")
    else:
        flash("Only pending bookings can be cancelled.", "warning")
    conn.close()
    return redirect(url_for("my_bookings"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db()
    stats = {
        "farmers": conn.execute("SELECT COUNT(*) c FROM users WHERE role='farmer'").fetchone()["c"],
        "equipment": conn.execute("SELECT COUNT(*) c FROM equipment").fetchone()["c"],
        "bookings": conn.execute("SELECT COUNT(*) c FROM bookings").fetchone()["c"],
        "pending": conn.execute("SELECT COUNT(*) c FROM bookings WHERE status='Pending'").fetchone()["c"],
    }
    bookings = conn.execute("""
        SELECT b.*, u.name AS farmer, u.phone, e.name AS equipment_name,
               (e.rent*b.duration) AS total
        FROM bookings b
        JOIN users u ON u.id=b.user_id
        JOIN equipment e ON e.id=b.equipment_id
        ORDER BY b.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin_dashboard.html", stats=stats, bookings=bookings)

@app.route("/admin/booking/<int:bid>/<action>")
@admin_required
def update_booking(bid, action):
    status = "Approved" if action == "approve" else "Rejected"
    conn = get_db()
    conn.execute("UPDATE bookings SET status=? WHERE id=?", (status, bid))
    conn.commit()
    conn.close()
    flash(f"Booking {status.lower()}.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/equipment", methods=["GET", "POST"])
@admin_required
def manage_equipment():
    conn = get_db()
    if request.method == "POST":
        conn.execute("""
            INSERT INTO equipment(name,category,model,rent,description,image,available)
            VALUES(?,?,?,?,?,?,1)
        """, (
            request.form["name"], request.form["category"], request.form["model"],
            float(request.form["rent"]), request.form["description"],
            request.form.get("image", "equipment.jpg")
        ))
        conn.commit()
        flash("Equipment added.", "success")
    equipment = conn.execute("SELECT * FROM equipment ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("manage_equipment.html", equipment=equipment)

@app.route("/admin/equipment/delete/<int:eid>")
@admin_required
def delete_equipment(eid):
    conn = get_db()
    conn.execute("DELETE FROM equipment WHERE id=?", (eid,))
    conn.commit()
    conn.close()
    flash("Equipment deleted.", "success")
    return redirect(url_for("manage_equipment"))

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
