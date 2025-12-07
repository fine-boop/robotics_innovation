from flask import Flask, request, render_template, flash, redirect, session, url_for
import sqlite3
import os
import secrets
from datetime import datetime
import random



app = Flask(__name__)
app.secret_key = secrets.token_hex(64)

def init_db():
    # os.system('rm database.db')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   email TEXT UNIQUE,
                   username TEXT UNIQUE,
                   password TEXT
                   )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS artefacts(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT UNIQUE,
                   user_that_logged TEXT,
                   weight REAL,
                   dimensions REAL,
                   photos_location TEXT UNIQUE,
                   model_file_location TEXT UNIQUE,
                   date_modified TEXT,
                   site_found TEXT,
                   coords REAL
                   )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS sites(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   site_name TEXT UNIQUE)""")
    conn.commit()
    conn.close()

def logout():
    session.clear()

@app.route('/postit', methods = ["POST",])
def postit():
    if request.method == 'POST' and 'logout' in request.form:
        logout()
    
    return redirect('/')


@app.route('/', methods = ["GET", "POST"])
def home():
    show_form = False
    item_logged = False
    item_exists = False
    log_artefact_pt1_success = False
    sites = []

    if request.method == 'POST' and 'show_form' in request.form:
        show_form = True
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT site_name FROM sites")
            col = cursor.fetchall()
            for x in col:
                sites.append(x[0])
        except sqlite3.DatabaseError:
            print("Error!")
        finally:
            conn.close()

        

    elif request.method == 'POST' and 'artefact_info' in request.form:

        item_name = request.form['item_name']
        site_found = request.form['site_found']
        user_that_logged = session['email']
        coords = request.form['latlng']

        date_modified = datetime.now()
        if item_name and site_found and coords:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO artefacts (user_that_logged, date_modified, name, site_found, weight, coords) VALUES(?, ?, ?, ?, ?, ?)", (user_that_logged, date_modified, item_name, site_found, 1, coords))
                log_artefact_pt1_success = 1
                print("data successfully written to db!")

                return """<h1>Log successful!</h1><a href="/"><button type="submit">Home</button><a>"""
            except sqlite3.IntegrityError:
                item_exists = True
                print('already exists! exists!!!!!!!!!!!!!!!!!!!!!')
                return render_template('index.html', item_exists = item_exists,  show_form = True, log_artefact_pt1_success = log_artefact_pt1_success)
            finally:
                print("Closing DB conn...")
                conn.commit()
                conn.close()
                print("DB conn closed successfully")
    
    return render_template('index.html', sites = sites, item_exists = item_exists, show_form = show_form, item_logged = item_logged, log_artefact_pt1_success = log_artefact_pt1_success)


@app.route('/add_site', methods = ["GET", "POST"])
def add_site():
    site_exists = False
    successful = False
    if request.method == "POST":
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        session['new_site_name'] = request.form.get('new_site_name')
        try:
            cursor.execute("INSERT INTO sites (site_name) VALUES (?)", (session['new_site_name'],))
            conn.commit()
            successful = True
        except sqlite3.IntegrityError:
            site_exists = True
        finally:
            conn.close()
        print(session['new_site_name'])
        print("Closed DB")
    return render_template('add_site.html', site_exists = site_exists, successful = successful)


@app.route('/admin_login', methods = ["GET", "POST"])
def admin_login():
    global user_is_admin
    if request.method == "POST":
            email = request.form.get('email')
            password = request.form.get('password')
            if email == 'pleasenerfevohogs@super.cell' and password == 'i<3kingjulian' or session.get('email') == 'julianbanim1@gmail.com':
                print('Successful admin login')
                session['user_is_admin'] = True
                return redirect(url_for('admin'))
            else:
                print("Failed login!!!")
                either_meme = random.choice([True, False])
                if either_meme:
                    return """<img src="/static/hill.jpg">"""
                else:
                    return """<img src="/static/images.jpeg">"""
    return render_template('admin_login.html')


@app.route('/about')
def about():
    return render_template('about.html')



@app.route('/admin', methods=["GET", "POST"])
def admin():
    if not session.get('user_is_admin'):
        return "<h1>fuck off ya melt</h1>"

    # Initialize flags and data
    shredded_db = False
    file_not_found = False
    shredded_users = False
    shredded_artefacts = False
    user_info = None
    artefacts_info = None

    if request.method == "POST":
        if 'shred_db' in request.form:
            try:
                os.remove('database.db')
                shredded_db = True
                init_db()
            except FileNotFoundError:
                file_not_found = True

        elif 'shred_users' in request.form:
            try:
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute("DROP TABLE users")
                conn.commit()
                init_db()
                shredded_users = True
            except sqlite3.Error:
                print("SQL error")

        elif 'shred_artefacts' in request.form:
            try:
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute("DROP TABLE artefacts")
                conn.commit()
                init_db()
                shredded_artefacts = True
            except sqlite3.Error:
                print("SQL error")

        elif 'dump_users' in request.form:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            user_info = cursor.fetchall()

        elif 'dump_artefacts' in request.form:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM artefacts")
            artefacts_info = cursor.fetchall()

    return render_template(
        'admin.html',
        user_is_admin=True,
        shredded_db=shredded_db,
        file_not_found=file_not_found,
        shredded_users=shredded_users,
        shredded_artefacts=shredded_artefacts,
        user_info=user_info,
        artefacts_info=artefacts_info
    )










@app.route('/signup', methods = ["GET", "POST"])
def signup():
    email = False
    username = False
    password = False
    email_or_uid_in_use = False
    if request.method == "POST":
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (email, username, password) VALUES (?, ?, ?)", (email, username, password))
            conn.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            email_or_uid_in_use = True
            print("Email/Username is already in use.")
            return render_template('signup.html', email_or_uid_in_use = email_or_uid_in_use)   
        finally:
            conn.close()

    return render_template('signup.html')


@app.route('/login', methods=["POST", "GET"])
def login():
    invalid_creds = False
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email and password:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            row_exists = cursor.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,)).fetchone()
            if row_exists:
                row = cursor.execute("SELECT * FROM users WHERE email = ? LIMIT 1", (email,)).fetchone()
                email_on_db = row[1]
                username_on_the_db = row[2]
                password_on_db = row[3]
                if password_on_db == password:
                    session['email'] = email_on_db
                    session['username'] = username_on_the_db
                    conn.close()
                    return redirect('/')
                    
                else:
                    invalid_creds = True
            else:
                invalid_creds = True
    return render_template('login.html', invalid_creds=invalid_creds)






if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)