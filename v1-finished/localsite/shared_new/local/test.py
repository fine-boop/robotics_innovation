from flask import Flask, render_template, request, session, redirect, flash, Response, jsonify, stream_with_context, send_from_directory
import sqlite3
from datetime import datetime
import secrets
from pathlib import Path
import cv2
import time
import json

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ================= DEBUG =================
DEBUG = True

def debug(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

def debug_error(msg):
    print(f"[ERROR] {msg}")
# ========================================

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
                       id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       email TEXT UNIQUE,
                       name TEXT,
                       password TEXT
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS sites(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        owner INTEGER,
        FOREIGN KEY(owner) REFERENCES users(id) ON DELETE CASCADE
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS site_members(
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       site_id INTEGER,
                       user_id INTEGER,
                       UNIQUE(site_id, user_id),
                       FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE,
                       FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS artefacts(
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT,
                       site_found INT,
                       user_found INT,
                       weight FLOAT,
                       FOREIGN KEY(site_found) REFERENCES sites(id) ON DELETE CASCADE,
                       FOREIGN KEY(user_found) REFERENCES users(id) ON DELETE CASCADE
    )""")
    conn.commit()
    # Seed example data for development (idempotent)
    cursor.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (email, name, password) VALUES (?, ?, ?)",
                       ("test@example.com", "Test User", "password"))
        user_id = cursor.lastrowid
        cursor.execute("INSERT OR IGNORE INTO sites (name, owner) VALUES (?, ?)",
                       ("Example Site", user_id))
        site_id = cursor.lastrowid
        cursor.execute("INSERT OR IGNORE INTO site_members (site_id, user_id) VALUES (?, ?)",
                       (site_id, user_id))
        conn.commit()
    conn.close()

def init_conn():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    return conn, cursor

# Auto-login dev user in DEBUG mode so example site shows up immediately
@app.before_request
def auto_login_dev_user():
    if DEBUG and 'uid' not in session:
        conn, cursor = init_conn()
        row = cursor.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",)).fetchone()
        conn.close()
        if row:
            session['uid'] = row[0]
            debug("Auto-logged in test user for DEBUG")

# ================= CAMERA =================
camera = None
camera_active = False

def start_camera():
    global camera, camera_active
    if camera is None:
        debug("Starting camera")
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            debug_error("Camera failed to open")
            camera = None
            camera_active = False
        else:
            debug("Camera opened")
            camera_active = True
    else:
        debug("Camera already running")
        # Ensure state reflects camera availability
        if camera.isOpened():
            camera_active = True

def stop_camera():
    global camera, camera_active
    if camera is not None:
        debug("Stopping camera")
        camera.release()
        camera = None
        camera_active = False
    else:
        debug("Camera already stopped")

def gen_frames():
    global camera, camera_active
    debug("Video stream generator started")
    if camera is None or not camera.isOpened():
        debug_error("Camera not initialized for streaming")
        return

    while camera_active and camera is not None:
        success, frame = camera.read()
        if not success:
            debug_error("Failed to read frame")
            break

        _, buffer = cv2.imencode(".jpg", frame)
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" +
               buffer.tobytes() +
               b"\r\n")
    debug("Video stream generator stopped")

# ================= ROUTES =================
@app.route('/')
def home():
    return render_template("a.html")

@app.route("/log_artefact", methods=["GET", "POST"])
def log_artefact():
    global camera_active
    debug("Entered /log_artefact")

    if "uid" not in session:
        debug_error("Unauthenticated access attempt")
        return redirect("/")

    conn, cursor = init_conn()

    sites_user_is_in = cursor.execute(
        "SELECT site_id FROM site_members WHERE user_id = ?",
        (session["uid"],)
    ).fetchall()

    if not sites_user_is_in:
        conn.close()
        return render_template("log_artefact.html", no_sites=True)

    sites = []
    for site in sites_user_is_in:
        site_id = site[0]
        site_name = cursor.execute(
            "SELECT name FROM sites WHERE id = ?",
            (site_id,)
        ).fetchone()[0]
        sites.append((site_id, site_name))

    if request.method == "POST":
        artefact_name = request.form.get("name")
        weight = request.form.get("weight")
        site = request.form.get("site")

        debug(f"Logging artefact | name={artefact_name}, weight={weight}, site={site}")

        try:
            cursor.execute(
                "INSERT INTO artefacts (name, weight, site_found, user_found) VALUES (?, ?, ?, ?)",
                (artefact_name, weight, site, session["uid"])
            )
            conn.commit()
            debug("Artefact inserted into DB")

            # Start camera for live preview
            start_camera()
            camera_active = True
            debug("Camera activated for live preview")

            flash(f"Successfully logged {artefact_name}")
            conn.close()
            return render_template(
                "log_artefact.html",
                sites=sites,
                capture_mode=True,
                artefact_name=artefact_name
            )

        except Exception as e:
            debug_error(f"DB insert failed: {e}")
            flash("Error logging artefact")
            conn.close()

    return render_template("log_artefact.html", sites=sites)

@app.route("/artefact_video")
def artefact_video():
    global camera_active
    debug(f"/artefact_video requested | camera_active={camera_active}")
    if not camera_active or camera is None:
        debug("Rejected video request (camera inactive)")
        return "Camera off", 403
    return Response(stream_with_context(gen_frames()), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/capture_artefact/<artefact_name>")
def capture_artefact(artefact_name):
    global camera_active, camera
    debug(f"Starting capture | artefact_name={artefact_name}")

    if camera is None or not camera.isOpened():
        debug_error("Camera not initialized for capture")
        return jsonify({"error": "Camera not initialized"}), 400

    # Resolve artefact id to use as directory name
    artefact_id = None
    try:
        artefact_id = int(artefact_name)
    except Exception:
        # best-effort: if test harness inserted the artefact it's likely created by current user
        # fall back to latest by name
        conn2, cursor2 = init_conn()
        row = cursor2.execute("SELECT id FROM artefacts WHERE name = ? ORDER BY id DESC LIMIT 1", (artefact_name,)).fetchone()
        conn2.close()
    photos_dir = Path("photos") / str(artefact_id)
    photos_dir.mkdir(parents=True, exist_ok=True)
    captured = 0
    errors = []

    def generate():
        nonlocal captured
        for i in range(20):
            if camera is None or not camera.isOpened():
                errors.append(i)
                payload = {'frame': i+1, 'total': 20, 'status': 'error'}
                yield f"data: {json.dumps(payload)}\n\n"
                continue

            success, frame = camera.read()
            if success:
                path = photos_dir / f"{i}.jpg"
                cv2.imwrite(str(path), frame)
                captured += 1
                payload = {'frame': i+1, 'total': 20, 'status': 'captured'}
                yield f"data: {json.dumps(payload)}\n\n"
            else:
                errors.append(i)
                payload = {'frame': i+1, 'total': 20, 'status': 'error'}
                yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(1)

        # Stop camera at the end
        stop_camera()
        payload = {'status': 'done', 'captured': captured, 'errors': errors}
        yield f"data: {json.dumps(payload)}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route('/photos/<artefact_name>/<path:filename>')
def serve_photo(artefact_name, filename):
    artefact_id = None
    try:
        artefact_id = int(artefact_name)
    except Exception:
        row = cursor.execute("SELECT id FROM artefacts WHERE name = ? ORDER BY id DESC LIMIT 1", (artefact_name,)).fetchone()
        if row:
            artefact_id = row[0]

    if artefact_id is None:
        return 'Not found', 404

    directory = Path('photos') / str(artefact_id)
    path = directory / filename
    if not path.exists():
        return 'Not found', 404
    return send_from_directory(str(directory), filename)


@app.route('/photos_list/<artefact_name>')
def photos_list(artefact_name):
    artefact_id = None
    try:
        artefact_id = int(artefact_name)
    except Exception:
        row = cursor.execute("SELECT id FROM artefacts WHERE name = ? ORDER BY id DESC LIMIT 1", (artefact_name,)).fetchone()
        if row:
            artefact_id = row[0]

    if artefact_id is None:
        return jsonify([])

    directory = Path('photos') / str(artefact_id)
    if not directory.exists():
        return jsonify([])
    files = sorted([f.name for f in directory.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png')])
    return jsonify(files)


# ================= RUN =================
if __name__ == "__main__":
    init_db()
    debug("Starting Flask server")
    app.run(host="0.0.0.0", port=5000, debug=True)
