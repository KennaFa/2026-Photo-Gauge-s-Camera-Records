from flask import Flask, request, redirect, render_template, flash, url_for, session
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import shutil

# ================================
# CONFIGURATION
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = "/tmp"  # Render writable folder
DB_FILE = os.path.join(TMP_DIR, "cameralite3.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app = Flask(__name__)
app.secret_key = "camera_secret_key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

# ================================
# DATABASE
# ================================
def create_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    if not os.path.exists(DB_FILE):
        local_db = os.path.join(BASE_DIR, "cameralite3.db")
        if os.path.exists(local_db):
            shutil.copy(local_db, DB_FILE)

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            CameraBrand TEXT NOT NULL,
            CameraModel TEXT NOT NULL,
            CameraType TEXT NOT NULL,
            email TEXT NOT NULL,
            year_date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def migrate_photo_column():
    conn = create_connection()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE cameras ADD COLUMN photo TEXT")
        conn.commit()
        print("✅ photo column added")
    except sqlite3.OperationalError:
        print("✔ photo column exists")
    finally:
        conn.close()

def migrate_description_column():
    conn = create_connection()
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE cameras ADD COLUMN description TEXT DEFAULT ''")
        conn.commit()
        print("✅ description column added")
    except sqlite3.OperationalError:
        print("✔ description column exists")
    finally:
        conn.close()

# Run migrations
initialize_database()
migrate_photo_column()
migrate_description_column()

# ================================
# HELPERS
# ================================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ================================
# ROUTES
# ================================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        year_date = request.form.get("year_date")

        conn = create_connection()
        user = conn.execute("SELECT * FROM cameras WHERE email=? AND year_date=?", (email, year_date)).fetchone()
        conn.close()

        if user:
            session["user_email"] = email
            return redirect(url_for("register"))
        else:
            flash("Invalid login", "danger")

    return render_template("login.html")

@app.route("/rgstr", methods=["GET", "POST"])
def register():
    conn = create_connection()

    if request.method == "POST":
        cid = request.form.get("id")
        brand = request.form.get("CameraBrand")
        model = request.form.get("CameraModel")
        ctype = request.form.get("CameraType")
        email = request.form.get("email")
        date = request.form.get("year_date")
        file = request.files.get("photo")

        photo_filename = None
        if file and allowed_file(file.filename):
            name = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], name))
            photo_filename = f"uploads/{name}"

        cur = conn.cursor()

        if cid:
            if photo_filename:
                cur.execute("""
                    UPDATE cameras SET CameraBrand=?, CameraModel=?, CameraType=?, email=?, year_date=?, photo=?
                    WHERE id=?
                """, (brand, model, ctype, email, date, photo_filename, cid))
            else:
                cur.execute("""
                    UPDATE cameras SET CameraBrand=?, CameraModel=?, CameraType=?, email=?, year_date=?
                    WHERE id=?
                """, (brand, model, ctype, email, date, cid))
        else:
            cur.execute("""
                INSERT INTO cameras (CameraBrand, CameraModel, CameraType, email, year_date, photo, description)
                VALUES (?, ?, ?, ?, ?, ?, '')
            """, (brand, model, ctype, email, date, photo_filename))

        conn.commit()

    cameras = conn.execute("SELECT * FROM cameras ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("pager.html", cameras=cameras, edit=None)

@app.route("/CRW")
def cards_view():
    conn = create_connection()
    cameras = conn.execute("SELECT * FROM cameras ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("CRW.html", cameras=cameras)

@app.route("/update_description/<int:id>", methods=["POST"])
def update_description(id):
    new_desc = request.form.get("description", "")

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("UPDATE cameras SET description=? WHERE id=?", (new_desc, id))
    conn.commit()
    conn.close()

    return redirect(url_for("cards_view"))

@app.route("/delete/<int:id>")
def delete_camera(id):
    conn = create_connection()
    conn.execute("DELETE FROM cameras WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("register"))

@app.route("/logout")
def logout():
    session.pop("user_email", None)
    return redirect(url_for("login"))

# ================================
# RUN
# ================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
