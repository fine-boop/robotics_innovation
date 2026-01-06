from flask import Flask, render_template, request, redirect, flash, url_for, session
import time
import sqlite3
from colorama import Fore, Style, init
from datetime import datetime
import os
import secrets

init(autoreset=True)
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

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
        FOREIGN KEY(owner) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""CREATE TABLE IF NOT EXISTS site_members(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   site_id INTEGER,
                   user_id INTEGER,
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

    file.close()
    return line


@app.route('/')
def home():
    return render_template('home.html')
@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        conn, cursor = init_conn()
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        if not email or not name or not password:
            flash('Something went wrong.', 'red')
            exit()
        print(console_log('User ' + name + ' has begun signup proccess', 'info'))
        try:
            cursor.execute('INSERT INTO users (email, name, password) VALUES (?, ?, ?)', (email, name, password))
            conn.commit()
            print(console_log('Created account: ' + name, 'success'))
            flash('Successfully created account!', 'green')
        except sqlite3.Error as e:
            print(console_log(e, 'error'))
        finally:
            conn.close()
            return redirect('/signup')
    return render_template('signup.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        conn, cursor = init_conn()
        email = request.form['email']
        password = request.form['password']
        if not email or not password:
            flash('Something went wrong.', 'red')
            return redirect('/login')
        print(console_log('User ' + email + ' has begun login proccess', 'info'))
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
        session['name'] = user_data[1]
        conn.close()
        return redirect('/')
    return render_template('login.html')

@app.route('/logout')
def logout():
    if session['email']:
        print(console_log('User ' + session['email'] +  ' has logged out', 'info'))
        session.clear()
        return redirect('/')

@app.route('/my_sites')
def my_sites():
    if 'email' not in session:
        print(console_log('User with no account attempted to access /my_sites enpoint', 'warn'))
        return redirect('/login')
        
    conn , cursor = init_conn()
    sites = []
    uid = cursor.execute('SELECT id FROM users WHERE email = ?', (session['email'],)).fetchone()[0]
    sites_ids = cursor.execute('SELECT site_id FROM site_members WHERE user_id = ?', (uid,)).fetchall()
    if not sites_ids:
        conn.close()
        return render_template('my_sites.html', no_sites = True)
    for id in sites_ids:
        id = id[0]
        site = cursor.execute('SELECT name, owner FROM sites WHERE id = ?', (id,)).fetchone()
        if site:
            sites.append(site)
        else:
            print(console_log('Something went wrong line 157.', 'error'))
    conn.close()
    return render_template('my_sites.html', sites=sites)

@app.route('/join_site', methods = ["GET", "POST"])
def join_site():
    if 'email' not in session:
        return redirect('/')
    conn, cursor = init_conn()

    if request.method == "POST":
        site_name = request.form['site_name']
        site_password = request.form['site_password']
        if not site_name or not site_password:
            flash('You must include both fields!')
            return redirect('/join_site')
        site_exists = cursor.execute('SELECT 1 FROM sites WHERE name = ?', (site_name,)).fetchone()
        if not site_exists:
            flash('Site does not exist!')
            return redirect('/join_site')
        password = cursor.execute('SELECT password FROM sites WHERE name  = ?', (site_name,)).fetchone()[0]
        if site_password != password:
            flash('Invalid creds!')
            return redirect('/create site')
        site_id = cursor.execute('SELECT id FROM sites WHERE name = ?', (site_name,)).fetchone()[0]
        session['site'] = site_id
        flash(f'Joined {site_name} successfully!')
        conn.close()
    else:
        data = []
        sites = cursor.execute('SELECT name FROM sites').fetchall()
        for user in sites:
            data.append(user[0])

    return render_template('join_site.html', data = data)

@app.route('/create_site', methods = ["GET", "POST"])
def create_site():
    if 'email' not in session:
        return redirect('/')
    if request.method == "POST":
        conn, cursor = init_conn()
        site_name = request.form['site_name']
        site_password = request.form['site_password']
        site_members = request.form['site_members']

        if not site_name or not site_password or not site_members:
            flash('Error')
            return redirect('/create_site')
        creator_id = cursor.execute('SELECT id FROM users WHERE email = ?', (session['email'],)).fetchone()[0]
        does_it_exist = cursor.execute('SELECT 1 FROM sites WHERE name = ?', (site_name,)).fetchone()
        if does_it_exist == True:
            flash('Site already exists!')
            return redirect('/create_site')
        try:
            cursor.execute('INSERT INTO sites (name, owner, password) VALUES (?, ?, ?) ', (site_name, creator_id, site_password))
            console_log('User ' + session['email'] + 'successfully created site' + site_name, 'success')
            conn.commit()
            flash('Successfully created site ' + site_name + '!')
            return redirect('/create_site')
        except sqlite3.Error as e:
            flash('Error')
            print(console_log(session['email'] + 'got an error when creating site: ' + str(e), 'error'))
            return redirect('/create_site')
        finally:
            conn.close()



if __name__ == '__main__':
    os.system('log.txt')
    init_db()
    app.run(debug=True)