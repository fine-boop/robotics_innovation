from flask import Flask, render_template, request, redirect, flash, url_for, session, Response, stream_with_context, send_from_directory, jsonify
import time
import sqlite3
import threading
from colorama import Fore, Style, init
from datetime import datetime
import os
import secrets
import time
# import RPi.GPIO as GPIO
# from hx711 import HX711
import signal
import sys
import cv2
import json
import subprocess
import requests
import shutil

ready_downloads = []

init(autoreset=True)
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

server_url = 'http://109.255.108.201'


# Camera management and streaming/capture endpoints

camera = None
camera_active = False

# Locks to protect camera access and capture state
camera_lock = threading.Lock()
capture_lock = threading.Lock()
capture_in_progress = False


# Hardware pins and calibration
DT_PIN = 5
SCK_PIN = 6
REFERENCE_UNIT = -45.98148148148146



PIENV_PYTHON = "/home/pi/pienv/bin/python"   # adjust username if needed
SCRIPT_PATH = "weight_subproc.py"   # path to the script above





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
        password TEXT,
        location TEXT,
        FOREIGN KEY(owner) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
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
                   scan_path TEXT UNIQUE,
                   FOREIGN KEY(site_found) REFERENCES sites(id) ON DELETE CASCADE,
                   FOREIGN KEY(user_found) REFERENCES users(id) ON DELETE CASCADE
                   )""")
    conn.commit()
    conn.close()







def init_conn():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    return conn, cursor



def get_average_weight_subproc(samples=10, dt_pin=5, sck_pin=6, reference_unit=1.0, timeout=10):
    try:
        result = subprocess.run(
            [PIENV_PYTHON, SCRIPT_PATH, str(dt_pin), str(sck_pin), str(reference_unit), str(samples)],
            capture_output=True,
            text=True,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        print("Weight subprocess timed out")
        return None

    if result.returncode != 0:
        print("Weight subprocess error:", result.stderr.strip())
        return None

    output = result.stdout.strip()
    if output == "None" or output == "":
        return None

    try:
        return float(output)
    except ValueError:
        print("Unexpected output from weight subprocess:", output)
        return None











def console_log(arg, level):
    timestamp = datetime.now().isoformat()
    if level == "error":
        line = Fore.RED + '[ERROR] ' + arg + Style.RESET_ALL
        # print(Fore.RED + '[ERROR] ' + arg + Style.RESET_ALL)
        with open('log.txt', 'a') as file:
            file.write(timestamp + ' [ERROR] ' + arg + '\n')
    elif level == "success":
        # print(Fore.GREEN + '[SUCCESS] ' + arg + Style.RESET_ALL)
        line = Fore.GREEN + '[SUCCESS] ' + arg + Style.RESET_ALL
        with open('log.txt', 'a') as file:
            file.write(timestamp + ' [SUCCESS] ' + arg + '\n')
    elif level == "info":
        line = Fore.BLUE + '[INFO] ' + arg + Style.RESET_ALL
        # print(Fore.CYAN + '[INFO] ' + arg + Style.RESET_ALL)
        with open('log.txt', 'a') as file:
            file.write(timestamp + ' [INFO] ' + arg + '\n')
    elif level == "warn":
        line = Style.RESET_ALL + f"\033[33m[WARN] {arg}\033[0m"
        # print(Fore.CYAN + '[WARN] ' + arg + Style.RESET_ALL)
        with open('log.txt', 'a') as file:
            file.write(timestamp + ' [WARN] ' + arg + '\n')
    return line





@app.route('/')
def home():
    return render_template('home.html')






@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        conn, cursor = init_conn()
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        if not email or not name or not password:
            flash('Something went wrong.', 'red')
        try:
            cursor.execute('INSERT INTO users (email, name, password) VALUES (?, ?, ?)', (email, name, password))
            uid = cursor.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
            conn.commit()
            conn.close()
            session['name'] = name
            session['email'] = email
            session['password'] = password
            session['uid'] = uid
            print(console_log('Created account: ' + name, 'success'))
            return redirect('/')
        except sqlite3.Error as e:
            print(console_log(str(e), 'error'))
        finally:
            conn.close()
    return render_template('signup.html')



@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        conn, cursor = init_conn()
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            flash('Something went wrong.', 'red')
            return redirect('/login')
        user_data = cursor.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchall()
        if not user_data:
            print(console_log('User ' + email + ' tried to log into a nonexistent account', 'info'))
            flash('Account does not exist!', 'red')
            return redirect('/login')
        user_data = user_data[0]
        if user_data[3] != password:
            flash('Invalid credidentials! ')
            print(console_log('User ' + email + ' failed login with incorrect password: '+ password, 'info'))
            return redirect('/login')
        print(console_log('User ' + email + ' sucessfully logged in', 'success'))
        session['email'] = email
        session['name'] = user_data[2]
        session['password'] = password
        session['uid'] = user_data[0]
        conn.close()
        if session['email'] == 'admin@admin':
            session['admin'] = True
        return redirect('/')
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'uid' in session:
        print(console_log('User ' + session['email'] +  ' has logged out', 'info'))
        session.clear()
        return redirect('/')
    else:
        return redirect('/')




@app.route('/my_sites/manage_site/<int:site_id>', methods=["GET", "POST"])
def manage_site(site_id):
    if 'uid' not in session:
        print(console_log('User with no account attempted to access /my_sites/manage_site endpoint', 'warn'))
        return redirect('/login')

    conn, cursor = init_conn()

    # Get site info, check ownership
    site_row = cursor.execute(
        "SELECT name FROM sites WHERE id = ? AND owner = ?",
        (site_id, session['uid'])
    ).fetchone()

    if not site_row:
        conn.close()
        print(console_log(f'{session["email"]} tried to access management of site id: {site_id}', 'warn'))
        return redirect('/')

    site = site_row[0]

    # Get current members
    member_rows = cursor.execute(
        "SELECT user_id FROM site_members WHERE site_id = ?",
        (site_id,)
    ).fetchall()

    members = []
    member_ids = set()
    for row in member_rows:
        user = cursor.execute(
            "SELECT id, name FROM users WHERE id = ?",
            (row[0],)
        ).fetchone()
        if user and user[0] is not None and user[1] is not None:
            members.append((user[0], user[1]))
            member_ids.add(user[0])

    # Get users not in the site
    users_not_in_site = cursor.execute(
        "SELECT id, name FROM users WHERE id != ?",
        (session['uid'],)
    ).fetchall()

    users_not_in_site = [
        (u[0], u[1]) for u in users_not_in_site
        if u[0] is not None and u[1] is not None and u[0] not in member_ids
    ]

    # Handle POST form submission
    if request.method == "POST":
        action = request.form.get('action')
        selected_members = request.form.getlist('members_select')

        if action == "add":
            for user_id in selected_members:
                # Check if user is already a member
                exists = cursor.execute(
                    "SELECT 1 FROM site_members WHERE site_id = ? AND user_id = ?",
                    (site_id, user_id)
                ).fetchone()
                if not exists:
                    cursor.execute(
                        "INSERT INTO site_members (site_id, user_id) VALUES (?, ?)",
                        (site_id, user_id)
                    )
            conn.commit()
            flash("Members added successfully.")

        elif action == "remove":
            for user_id in selected_members:
                # Check if user is actually a member
                exists = cursor.execute(
                    "SELECT 1 FROM site_members WHERE site_id = ? AND user_id = ?",
                    (site_id, user_id)
                ).fetchone()
                if exists:
                    cursor.execute(
                        "DELETE FROM site_members WHERE site_id = ? AND user_id = ?",
                        (site_id, user_id)
                    )
            conn.commit()
            flash("Members removed successfully.")

        return redirect(f'/my_sites/manage_site/{site_id}')

    conn.close()
    return render_template(
        'members.html',
        site=site,
        members=members,
        users_not_in_site=users_not_in_site
    )










@app.route('/my_sites', methods = ['GET', 'POST'])
def my_sites():
    if 'uid' not in session:
        print(console_log('User with no account attempted to access /my_sites enpoint', 'warn'))
        return redirect('/login') 
    conn , cursor = init_conn()
    sites = []
    uid = cursor.execute('SELECT id FROM users WHERE email = ?', (session['email'],)).fetchone()[0]
    if request.method == 'POST' and 'uid' in session:
        site_to_leave = request.form.get('site_to_leave')
        if not site_to_leave:
            print(console_log('User ' + session['email'], 'warn'))
            flash('Something went wrong 1')
            return redirect('/my_sites')
        if not site_to_leave.isdigit():
            print(console_log('Unexpected error in my_sites (leaving site), user may be tampering with requests', 'warn'))
            flash('Something went wrong 2')
            return redirect('/my_sites')
        site_to_leave = int(site_to_leave)
        site_info = cursor.execute('SELECT id, name, owner from SITES WHERE id = ?', (site_to_leave,)).fetchone()
        if not site_info:
            print(console_log('User ' + session['email'] + ' tried to leave a nonexistent site', 'error'))
            flash('Something went wrong 3')
            return redirect('/my_sites')
        print(site_info[2])
        print(session['uid'])
        if site_info[2] == session['uid']:
            flash('Action not possible!')
            print(console_log(f'User {session["email"]} tried removing themselves from a site they own, {site_info[1]}', 'info'))
            conn.close()
            return redirect('/my_sites')

        try:
            cursor.execute('DELETE FROM site_members WHERE site_id = ? AND user_id = ?', (site_to_leave, uid))
            conn.commit()
            conn.close()
            print(console_log(session['email'] + ' successfully left the site ' +  site_info[1], 'success'))
            flash('Successfully left ' + site_info[1] + '!')
            return redirect('/my_sites')
        except sqlite3.Error as e:
            flash('Something went wrong 4')
            print(console_log(session['email'] + ' incountered error ' + str(e) + ' when leaving a site', 'error'))
            conn.close()
            return redirect('/my_sites')
        finally:
            conn.close()
    


    sites_ids = cursor.execute('SELECT site_id FROM site_members WHERE user_id = ?', (uid,)).fetchall()
    if not sites_ids:
        conn.close()
        return render_template('my_sites.html', sites=sites)
    for site_id in sites_ids:
        site_id = site_id[0]
        site = cursor.execute('SELECT name, owner FROM sites WHERE id = ?', (site_id,)).fetchone()
        if not site:
            print(console_log('Something went wrong line 157.', 'error'))
            flash('Something went wrong')
            return redirect('/my_sites')
        
        owner_name = cursor.execute('SELECT name FROM users WHERE id = ?', (site[1],)).fetchone()[0]
        site_name = site[0]
        owner_id = site[1]
        sites.append((site_id, site_name, owner_name, owner_id))
    return render_template('my_sites.html', sites=sites)


@app.route('/profile', methods = ["GET", "POST"])
def my_profile():
    if 'uid' not in session:
        return redirect('/')
    conn, cursor = init_conn()
    id, name = cursor.execute('SELECT id, name FROM users WHERE email = ?', (session['email'],)).fetchone()
    if request.method == 'POST' and 'uid' in session:
        thing_to_change = request.form.get('thing_to_change')
        if thing_to_change == 'email':
            new_email = request.form.get('email')
            if new_email == session['email']:
                flash('New email cannot be the same as the old one!')
                print(console_log(session['email'] + ' tried to update their email but reused the old one', 'info'))
                return redirect('/my_site')
            try:
                cursor.execute('UPDATE users SET email = ? WHERE email = ?', (new_email, session['email']))
                print(console_log('Successfully updated ' + session['email'] + ' to ' + new_email + '!', 'success'))
                conn.commit()
            except sqlite3.Error as e:
                flash('Error')
                print(console_log(f'Error at my_sites when changing {session["email"]}s email', 'error'))
                return redirect('/my_sites')
            finally:
                conn.close()
        elif thing_to_change == 'name':
            new_name = request.form.get('name')
            if new_name == session['name']:
                flash('New name cannot be the same as the old one!')
                print(console_log(session['email'] + ' tried to update their name but reused the old one', 'info'))
                return redirect('/my_site')
            try:
                cursor.execute('UPDATE users SET name = ? WHERE name = ?', (new_name, session['name']))
                print(console_log('Successfully updated ' + session['name'] + ' to ' + new_name + '!', 'success'))
                conn.commit()
            except sqlite3.Error as e:
                flash('Error')
                print(console_log(f'Error at my_sites when changing {session["email"]}s name', 'error'))
                return redirect('/my_sites')
            finally:
                conn.close()
        elif thing_to_change == 'password':
            new_name = request.form.get('password')
            if new_name == session['password']:
                flash('New password cannot be the same as the old one!')
                print(console_log(session['email'] + ' tried to update their password but reused the old one', 'info'))
                return redirect('/my_site')
            try:
                cursor.execute('UPDATE users SET password = ? WHERE password = ?', (new_name, session['password']))
                print(console_log('Successfully updated ' + session['password'] + ' to ' + new_name + '!', 'success'))
                conn.commit()
            except sqlite3.Error as e:
                flash('Error')
                print(console_log(f'Error at my_sites when changing {session["email"]}s password', 'error'))
                return redirect('/my_sites')
            finally:
                conn.close()
    return render_template('my_profile.html')



@app.route('/join_site', methods = ["GET", "POST"])
def join_site():
    if 'uid' not in session:
        return redirect('/')
    conn, cursor = init_conn()
    sites_names = cursor.execute('SELECT name FROM sites').fetchall()
    if request.method == 'POST' and 'uid' in session:
        site_name = request.form.get('name')
        site_password = request.form.get('password')
        if not cursor.execute('SELECT 1 FROM sites WHERE name = ?', (site_name,)).fetchone():
            flash('Site does not exist!')
            print(console_log(f'{session["email"]} tried to join a nonexistent site', 'info'))
            conn.close()
            return redirect('/join_site')
        site_info = cursor.execute('SELECT id, password, owner FROM sites WHERE name = ?', (site_name,)).fetchone()
        site_id = site_info[0]
        if site_info[1] != site_password:
            flash('Incorrect password')
            print(console_log(f'{session["email"]} entered the wrong password to join {site_name}. Correcet password {site_info[1]}', 'info'))
            conn.close()
            return redirect('/join_site')
        is_user_in_site = cursor.execute('SELECT user_id FROM site_members WHERE site_id = ?', (site_id,)).fetchone()
        does_user_own_site = cursor.execute('SELECT owner FROM sites WHERE id = ?', (site_id,)).fetchone()
        if does_user_own_site:
            flash('You are already in this site!')
            print(console_log(f'{session["email"]} tried to join a site they own, {site_name}', 'info'))
            conn.close()
            return redirect('/join_site')
        if is_user_in_site:
            flash('You are already in this site!')
            print(console_log(f'{session["email"]} tried to join a site they are already in, {site_name}', 'info'))
            conn.close()
            return redirect('/join_site')
        try:
            cursor.execute('INSERT INTO site_members (site_id, user_id) VALUES (?, ?)', (site_id, session['uid']))
            conn.commit()
            flash(f'Successfully joined {site_name}!')
            print(console_log(f'{session["email"]} successfully joined {site_name}', 'success'))
        except sqlite3.Error as e:
            print(console_log(f'Error in join site: {e}', 'error'))
            flash("Error")
        finally:
            conn.close()
            return redirect('/join_site')
    return render_template('join_site.html', sites_names = sites_names)

@app.route('/create_site', methods = ["GET", "POST"])
def create_site():
    if 'uid' not in session:
        print(console_log('User not logged in tried to access create_site endpoint', 'warn'))
        return redirect('/')
    conn, cursor = init_conn()
    users_names = cursor.execute('SELECT id, name FROM users WHERE id  != ?', (session['uid'],)).fetchall()
    if request.method == 'POST' and 'uid' in session:
        site_name = request.form.get('name')
        site_password = request.form.get('password')
        site_members = request.form.getlist('site_members')
        site_location = request.form.get('location')
        if cursor.execute('SELECT 1 FROM sites WHERE name = ?', (site_name,)).fetchone():
            print(console_log(f'{session["email"]} tried to create the site {site_name}, already exists', 'info'))
            flash('Site exists!')
            conn.close()
            return redirect('/create_site')
        try:
            cursor.execute('INSERT INTO sites (name, owner, location, password) VALUES (?, ?, ?, ?)', (site_name, session['uid'], site_location, site_password))
            site_id = cursor.execute('SELECT id FROM sites WHERE name = ?', (site_name,)).fetchone()[0]
            cursor.execute('INSERT INTO site_members (site_id, user_id) VALUES (?, ?)', (site_id, session['uid']))
            for member in site_members:
                cursor.execute('INSERT INTO site_members (site_id, user_id) VALUES (?, ?)', (site_id, member))
                name = cursor.execute('SELECT name FROM users WHERE id = ?', (member,)).fetchone()[0]
                print(console_log(f'{session["email"]} added {name} to {site_name}!', 'info'))
            conn.commit()
            flash(f'Successfully created {site_name} and added {len(site_members)} members!')
            print(console_log(f'User {session["email"]} successfully created {site_name} and added {len(site_members)} members!', 'success'))
        except sqlite3.Error as e:
            print(console_log(f'{session["email"]} hit the error {e} when making a new site', 'error'))
            flash('Error')
        finally:
            conn.close()
    return render_template('/create_site.html', users_names = users_names)

@app.route('/sites', methods=["GET", "POST"])
def browse_sites():
    # if not session['admin']:
    #     return redirect('/')

    conn, cursor = init_conn()

    # Only fetch SAFE fields for users
    users = cursor.execute('SELECT id, email, name FROM users').fetchall()

    sites = cursor.execute('SELECT id, name, owner FROM sites').fetchall()
    artefacts = cursor.execute('SELECT * FROM artefacts').fetchall()
    site_members = cursor.execute('SELECT * FROM site_members').fetchall()
    
    conn.close()
    return render_template(
        'user_browse_sites.html',
        sites=sites,
        artefacts=artefacts,
        site_members=site_members,
        users=users
    )


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session['admin']:
        print(console_log('User tried to access browse sites endpoint.', 'warn'))
        return redirect('/')
    conn, cursor = init_conn()
    users = cursor.execute('SELECT * FROM users').fetchall()
    sites = cursor.execute('SELECT * FROM sites').fetchall()
    artefacts = cursor.execute('SELECT * FROM artefacts').fetchall()
    site_members = cursor.execute('SELECT * FROM site_members').fetchall()

    return render_template('admin_browse_sites.html', sites=sites, artefacts=artefacts, site_members=site_members, users=users)




@app.route('/log_artefact', methods = ["GET", "POST"])
def log_artefact():
    if not 'uid' in session:
        print(console_log('User not logged in tried to access /log_artefact endpoint', 'warn'))
        return redirect('/')
    conn, cursor = init_conn()
    sites = []
    sites_user_is_in = cursor.execute('SELECT site_id FROM site_members WHERE user_id = ?', (session['uid'],)).fetchall()
    if not sites_user_is_in:
        return render_template('log_artefact.html', no_sites=True)

    for site in sites_user_is_in:
        site_id = site[0]
        site_name = cursor.execute('SELECT name FROM sites WHERE id = ?', (site_id,)).fetchone()[0]
        sites.append((site_id, site_name))

    if request.method == 'POST' and 'uid' in session:
        artefact_name = request.form.get('name')
        form_weight = request.form.get('weight')
        site = request.form.get('site')

        # Try to measure weight from HX711 first (average of first 10 samples)
        measured = get_average_weight_subproc(
            samples=10,
            dt_pin=DT_PIN,
            sck_pin=SCK_PIN,
            reference_unit=REFERENCE_UNIT,
            timeout=10
        )
        if measured is not None:
            chosen_weight = measured
            print(console_log(f'{session["email"]} measured artefact weight: {chosen_weight}kg', 'info'))
        else:
            # Fallback to provided form value if measurement is not available
            try:
                chosen_weight = float(form_weight) if form_weight is not None and form_weight != '' else None
            except Exception:
                chosen_weight = None
            print(console_log(f'{session["email"]} could not measure weight; using form value: {chosen_weight}', 'warn'))

        try:
            cursor.execute('INSERT INTO artefacts (name, weight, site_found, user_found) VALUES (?, ?, ?, ?)', (artefact_name, chosen_weight, site, session['uid']))
            print(console_log(f'{session["email"]} just logged an artefact', 'success'))
            conn.commit()

            # Start camera for live preview and capture
            start_camera()
            conn.close()

            # Render capture UI so user can preview and capture photos
            return render_template('log_artefact.html', sites=sites, capture_mode=True, artefact_name=artefact_name, measured_weight=chosen_weight, form_weight=form_weight)

        except sqlite3.Error as e:
            print(console_log(f'{session["email"]} hit error {e} when logging artefact', 'error'))
            flash('Error')
        finally:
            conn.close()
    return render_template('log_artefact.html', sites=sites) 





def start_camera():
    global camera, camera_active
    with camera_lock:
        if camera is None:
            print(console_log('Starting camera for live preview', 'info'))
            camera = cv2.VideoCapture(0)
            if not camera.isOpened():
                print(console_log('Camera failed to open', 'error'))
                camera = None
                camera_active = False
            else:
                camera_active = True
        else:
            # ensure state is accurate
            if camera.isOpened():
                camera_active = True
            else:
                camera_active = False


def stop_camera():
    global camera, camera_active
    with camera_lock:
        if camera is not None:
            print(console_log('Stopping camera', 'info'))
            try:
                camera.release()
            except Exception as e:
                print(console_log(f'Error releasing camera: {e}', 'error'))
            camera = None
            camera_active = False


def gen_frames():
    global camera, camera_active
    print(console_log('Video stream generator started', 'info'))
    if camera is None or not camera.isOpened():
        print(console_log('Camera not initialized for streaming', 'warn'))
        return

    while camera_active and camera is not None:
        success, frame = camera.read()
        if not success:
            print(console_log('Failed to read frame', 'error'))
            break
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    print(console_log('Video stream generator stopped', 'info'))


@app.route('/artefact_video')
def artefact_video():
    global camera_active
    if not camera_active or camera is None:
        return 'Camera off', 403
    return Response(stream_with_context(gen_frames()), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/capture_artefact/<artefact_name>')
def capture_artefact(artefact_name):
    global camera, camera_active, capture_in_progress
    print(console_log(f'Request to capture for {artefact_name}', 'info'))

    # If another capture is in progress, immediately notify client and exit
    with capture_lock:
        if capture_in_progress:
            print(console_log('Capture already in progress, rejecting new request', 'warn'))
            def already():
                payload = {'status': 'error', 'message': 'capture_in_progress'}
                yield f"data: {json.dumps(payload)}\n\n"
            return Response(already(), mimetype='text/event-stream')
        capture_in_progress = True

    # Ensure camera is running (try to start it)
    if camera is None or not getattr(camera, 'isOpened', lambda: False)():
        print(console_log('Camera not initialized, attempting to start it...', 'info'))
        start_camera()
        # wait a moment for camera to become ready
        timeout = 3.0
        waited = 0.0
        interval = 0.2
        while (camera is None or not getattr(camera, 'isOpened', lambda: False)()) and waited < timeout:
            time.sleep(interval)
            waited += interval
        if camera is None or not getattr(camera, 'isOpened', lambda: False)():
            print(console_log('Camera failed to initialize for capture', 'error'))
            with capture_lock:
                capture_in_progress = False
            def no_cam():
                payload = {'status': 'error', 'message': 'camera_unavailable'}
                yield f"data: {json.dumps(payload)}\n\n"
            return Response(no_cam(), mimetype='text/event-stream')

    # Resolve artefact id to use as directory name (prefer numeric id if provided, else find latest by name and user)
    artefact_id = None
    try:
        artefact_id = int(artefact_name)
    except Exception:
        conn2, cursor2 = init_conn()
        row = cursor2.execute(
            "SELECT id FROM artefacts WHERE name = ? AND user_found = ? ORDER BY id DESC LIMIT 1",
            (artefact_name, session.get('uid'))
        ).fetchone()
        if not row:
            row = cursor2.execute("SELECT id FROM artefacts WHERE name = ? ORDER BY id DESC LIMIT 1", (artefact_name,)).fetchone()
        conn2.close()
        if row:
            artefact_id = row[0]

    if artefact_id is None:
        with capture_lock:
            capture_in_progress = False
        def no_artefact():
            payload = {'status': 'error', 'message': 'artefact_not_found'}
            yield f"data: {json.dumps(payload)}\n\n"
        return Response(no_artefact(), mimetype='text/event-stream')

    photos_dir = os.path.join('photos', str(artefact_id))
    os.makedirs(photos_dir, exist_ok=True)
    captured = 0
    errors = []

    def generate():
        nonlocal captured
        try:
            # notify client that capture started
            payload = {'status': 'started'}
            yield f"data: {json.dumps(payload)}\n\n"

            for i in range(20):
                # read frame under camera lock to avoid races with stop_camera
                with camera_lock:
                    try:
                        success, frame = camera.read()
                    except Exception as e:
                        print(console_log(f'Exception reading camera: {e}', 'error'))
                        success = False
                        frame = None

                if not success or frame is None:
                    errors.append(i)
                    payload = {'frame': i+1, 'total': 20, 'status': 'error'}
                    yield f"data: {json.dumps(payload)}\n\n"
                    time.sleep(1)
                    continue

                # write file under camera lock as well
                try:
                    path = os.path.join(photos_dir, f"{i}.jpg")
                    with camera_lock:
                        cv2.imwrite(path, frame)
                    captured += 1
                    payload = {'frame': i+1, 'total': 20, 'status': 'captured'}
                    yield f"data: {json.dumps(payload)}\n\n"
                except Exception as e:
                    print(console_log(f'Error writing photo {i}: {e}', 'error'))
                    errors.append(i)
                    payload = {'frame': i+1, 'total': 20, 'status': 'error'}
                    yield f"data: {json.dumps(payload)}\n\n"
                time.sleep(1)
        finally:
            # ensure camera is stopped and flag reset
            try:
                stop_camera()
            finally:
                with capture_lock:
                    capture_in_progress = False
            payload = {'status': 'done', 'captured': captured, 'errors': errors}
            yield f"data: {json.dumps(payload)}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/photos/<artefact_name>/<path:filename>')
def serve_photo(artefact_name, filename):
    # Resolve artefact id if printable numeric, otherwise try to find record by name
    artefact_id = None
    try:
        artefact_id = int(artefact_name)
    except Exception:
        conn, cursor = init_conn()
        row = cursor.execute("SELECT id FROM artefacts WHERE name = ? ORDER BY id DESC LIMIT 1", (artefact_name,)).fetchone()
        conn.close()
        if row:
            artefact_id = row[0]

    if artefact_id is None:
        return 'Not found', 404

    directory = os.path.join('photos', str(artefact_id))
    if not os.path.exists(os.path.join(directory, filename)):
        return 'Not found', 404
    return send_from_directory(directory, filename)



@app.route('/remote', methods=["GET", "POST"])
def remote():
    return render_template('remote.html')



@app.route('/upload_queue', methods=["GET", "POST"])
def upload_queue():
    conn, cursor = init_conn()
    completion = []
    folder_names = os.listdir('photos')
    if not folder_names:
        return jsonify({"queue": "empty"})
    for folder in folder_names[:]:
        int_name = int(folder)
        name = cursor.execute('SELECT name FROM artefacts WHERE id = ?', (int_name,)).fetchone()[0]
        os.system(f'zip -r zips/{folder}.zip photos/{folder}')
        print(console_log(f'{session["email"]} zipped {folder}. Now in zips/{folder}.zip. Awaiting post to server_url...', 'info'))
        with open(f'zips/{folder}.zip', 'rb') as f:
            files = {"file": f}
            resp = requests.post(f'{server_url}/upload/', files=files)
            time.sleep(1)
            if resp.status_code == 200:
                print(console_log(f'{session["email"]} successfully uploaded {folder}.zip to server_url {server_url}', 'success'))
            elif resp.status_code == 500:
                print(console_log(f'{session["email"]} hit an error when uploading {folder}.zip to server_url {server_url}', 'error'))

            completion.append({'name': folder, 'status': resp.status_code})
            shutil.rmtree(f'photos/{folder}')
    return jsonify(completion)

@app.route('/get_queue')
def get_queue():
    conn, cursor = init_conn()
    folder_names = os.listdir('photos')
    queue = []
    if not folder_names:
        return jsonify({"queue": "empty"})
    
    for folder in folder_names:
        folder = int(folder)
        name = cursor.execute('SELECT name FROM artefacts WHERE id = ?', (folder,)).fetchone()[0]
        queue.append({"id": folder, "name": name})

    return jsonify({"queue": queue})

@app.route('/view_queue')
def view_queue():
    return render_template('view_queue.html')

@app.route('/connect', methods=["GET"])
def connect():    
    error = None
    status = None

    try:
        r = requests.get(server_url, timeout=10)
        status = r.status_code
    except Exception as e:
        print("Error when connecting!", e)
        error = f"{str(e)}"
    return jsonify({"status": status, "error": error})


@app.route('/download')
def main_download():
    return jsonify(download())

def download():
    conn, cursor = init_conn()

    successes = {
    }
    for artefact_id in ready_downloads[:]:
        path = None
        name = None
        try:
            name = cursor.execute('SELECT name FROM artefacts WHERE id = ?', (artefact_id,)).fetchone()[0]
            r = requests.get(server_url + '/download/' + artefact_id, timeout=10)
            r.raise_for_status()

            path = f'/models/{artefact_id}'
            with open(path, 'wb') as f:
                f.write(r.content)
            print(console_log(f'Successfully downloaded 3d model of {name}', 'success'))
            successes[artefact_id] = {'path': path, 'name': name}
            ready_downloads.remove(artefact_id)
        except Exception as e:
            print(console_log(f"Failed to download {artefact_id}: {e}", 'error'))
        finally:
            time.sleep(.5)
        
    return successes


@app.route('/check', methods=['POST'])
def check():
    try:
        data = request.json
        artefact_id = int(data.get('number'))
        ready_downloads.append(artefact_id)
        successes = download()
        return jsonify(successes)
    except Exception as e:
        print(console_log('Error when server_url sending data', 'error'))


#prototype
# @app.route('/server_url', methods=['GET', 'POST'])
# def server_url():
#     url = '109.255.108.201'
#     conn, cursor = init_conn()
#     photos_dir = 'photos'
#     queue = []
#     status = False
#     ready_to_download = False

#     completion = []
#     for folder in os.listdir(photos_dir):
#         folder_path = os.path.join(photos_dir, folder)
#         queue.append(folder)
    
    
#     if request.method == 'POST':
#         if 'connect' in request.form:
#             try:
#                 print(console_log(f'Connecting to {url}', 'info'))
#                 r = requests.get('http//' +url, timeout=5)
#                 if r.status == 200:
#                     print(console_log('server_url is online!', 'info'))     
                    
#                 else:
#                     print(console_log('server_url is offline!', 'info'))
#             except Exception as e:
#                 print(console_log(f'Error when connecting to server_url, {str(e)}', 'info'))

#         elif 'upload' in request.form:
#             #uploading
#             if not queue:
#                 flash('There are is nothing in queue!')
#                 return redirect('/server_url')
#             #zip and upload each folder individually
#             for folder in queue:
#                 os.system(f'zip -r {folder}.zip {folder}')
#                 with open(f'{folder}.zip', 'rb') as f:
#                     files = {"file": f}
#                     resp = requests.post(f'{url}/upload/', files=files)
#                     time.sleep(1)
#                     completion.append(resp.status_code, folder)
#                     return render_template('server_url.html', completion=completion, queue=queue)

#         elif 'download' in request.form:
#             check = requests.get('http://'+ url + '/check')
#             ready_to_download = check.text
#             if ready_to_download == 'nothing':
#                 conn.close()
#                 return render_template('server_url.html', ready_to_download=False)



@app.route('/photos_list/<artefact_name>')
def photos_list(artefact_name):
    # Resolve artefact id like other endpoints
    artefact_id = None
    try:
        artefact_id = int(artefact_name)
    except Exception:
        conn, cursor = init_conn()
        row = cursor.execute("SELECT id FROM artefacts WHERE name = ? ORDER BY id DESC LIMIT 1", (artefact_name,)).fetchone()
        conn.close()
        if row:
            artefact_id = row[0]

    if artefact_id is None:
        return jsonify([])

    directory = os.path.join('photos', str(artefact_id))
    if not os.path.exists(directory):
        return jsonify([])
    files = sorted([f for f in os.listdir(directory) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    return jsonify(files)


@app.route('/save_artefact', methods=['POST'])
def save_artefact():
    # Persist the photo folder path to the latest artefact logged by this user with the given name
    if 'uid' not in session:
        return jsonify({'ok': False, 'error': 'unauthenticated'}), 403
    data = request.get_json() or request.form
    artefact_name = data.get('artefact_name')
    if not artefact_name:
        return jsonify({'ok': False, 'error': 'missing_name'}), 400

    conn, cursor = init_conn()
    row = cursor.execute(
        "SELECT id FROM artefacts WHERE name = ? AND user_found = ? ORDER BY id DESC LIMIT 1",
        (artefact_name, session['uid'])
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({'ok': False, 'error': 'not_found'}), 404

    artefact_id = row[0]
    # Save path using artefact id rather than the name
    scan_path = os.path.join('photos', str(artefact_id))
    try:
        cursor.execute('UPDATE artefacts SET scan_path = ? WHERE id = ?', (scan_path, artefact_id))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'ok': False, 'error': str(e)}), 500
    conn.close()
    return jsonify({'ok': True, 'redirect': url_for('log_artefact')})


print('SERVER' + server_url)

if __name__ == '__main__':
    print(console_log('Starting server_url', 'info'))
    init_db()
    app.run(debug=False)