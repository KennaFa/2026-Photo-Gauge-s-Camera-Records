from flask import Flask, request, redirect, render_template, flash, url_for, session
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename

# ================================
# CONFIGURE ARTS
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Use /tmp for DB on Render so write permissions exist
DB_FILE = os.path.join("/tmp", "cameralite3.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app = Flask(__name__)
app.secret_key = "camera_secret_key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================================
# DB FUNC
# ================================
def create_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Create the cameras table if it doesn't exist."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            CameraBrand TEXT NOT NULL,
            CameraModel TEXT NOT NULL,
            CameraType TEXT NOT NULL,
            email TEXT NOT NULL,
            year_date TEXT NOT NULL,
            description TEXT DEFAULT '',
            photo TEXT DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()

def migrate_database():
    """Add the 'photo' column if it doesn't exist."""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE cameras ADD COLUMN photo TEXT DEFAULT NULL")
        print("Column 'photo' added successfully!")
    except sqlite3.OperationalError:
        print("Column 'photo' already exists.")
    conn.commit()
    conn.close()

# Initialize DB and run migrations
initialize_database()
migrate_database()

# ================================
# HELP FUNC
# ================================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ================================
# ROUTES
# ================================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        year_date = request.form.get("year_date")

        if not email or not year_date:
            flash("Please enter Email and Date", "danger")
            return redirect(url_for("login"))

        conn = create_connection()
        user = conn.execute(
            "SELECT * FROM cameras WHERE email=? AND year_date=?",
            (email, year_date)
        ).fetchone()
        conn.close()

        if user:
            session["user_email"] = email
            flash("Login successful!", "success")
            return redirect(url_for("register"))
        else:
            flash("Invalid Email or Date", "danger")

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
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_filename = f"uploads/{filename}"

        if not all([brand, model, ctype, email, date]):
            flash("All fields are required!", "danger")
            return redirect(url_for("register"))

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            flash("Date must be YYYY-MM-DD", "danger")
            return redirect(url_for("register"))

        cursor = conn.cursor()

        if cid:  # edit existing record
            if "user_email" not in session:
                flash("Login required to edit records", "danger")
                return redirect(url_for("login"))

            if photo_filename:
                cursor.execute("""
                    UPDATE cameras
                    SET CameraBrand=?, CameraModel=?, CameraType=?, email=?, year_date=?, photo=?
                    WHERE id=?
                """, (brand, model, ctype, email, date, photo_filename, cid))
            else:
                cursor.execute("""
                    UPDATE cameras
                    SET CameraBrand=?, CameraModel=?, CameraType=?, email=?, year_date=?
                    WHERE id=?
                """, (brand, model, ctype, email, date, cid))
            flash("Camera updated successfully!", "success")
        else:  # add new record
            cursor.execute("""
                INSERT INTO cameras (CameraBrand, CameraModel, CameraType, email, year_date, photo)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (brand, model, ctype, email, date, photo_filename))
            flash("Camera added successfully!", "success")

        conn.commit()

    cameras = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
    conn.close()
    return render_template("pager.html", cameras=cameras, edit=None)


@app.route("/edit/<int:id>")
def edit_camera(id):
    if "user_email" not in session:
        flash("Login required to edit records", "danger")
        return redirect(url_for("login"))

    conn = create_connection()
    edit = conn.execute("SELECT * FROM cameras WHERE id=?", (id,)).fetchone()
    cameras = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
    conn.close()
    return render_template("pager.html", cameras=cameras, edit=edit)


@app.route("/delete/<int:id>")
def delete_camera(id):
    if "user_email" not in session:
        flash("Login required to delete records", "danger")
        return redirect(url_for("login"))

    conn = create_connection()
    conn.execute("DELETE FROM cameras WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Camera deleted successfully!", "success")
    return redirect(url_for("register"))


@app.route("/CRW")
def cards_view():
    conn = create_connection()
    cameras = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
    conn.close()
    return render_template("CRW.html", cameras=cameras)


@app.route("/update_description/<int:id>", methods=["POST"])
def update_description(id):
    new_desc = request.form.get("description", "")
    conn = create_connection()
    conn.execute("UPDATE cameras SET description=? WHERE id=?", (new_desc, id))
    conn.commit()
    conn.close()
    flash("Description updated!", "success")
    return redirect(url_for("cards_view"))


@app.route("/logout")
def logout():
    session.pop("user_email", None)
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))


# ================================
# RUNNING IN THE 90s
# ================================
if __name__ == "__main__":
    # debug=True is ok on Render for initial testing
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
