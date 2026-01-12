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
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        if not email or not name or not password:
            flash('Something went wrong.', 'red')
            exit()
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
@app.route('/my_sites', methods = ['GET', 'POST'])
def my_sites():
    if 'uid' not in session:
        print(console_log('User with no account attempted to access /my_sites enpoint', 'warn'))
        return redirect('/login') 
    conn , cursor = init_conn()
    sites = []
    uid = cursor.execute('SELECT id FROM users WHERE email = ?', (session['email'],)).fetchone()[0]
    if request.method == 'POST':
        site_to_leave = request.form['site_to_leave']
        if not site_to_leave:
            print(console_log('User ' + session['email'], 'warn'))
            flash('Something went wrong 1')
            return redirect('/my_sites')
        print(site_to_leave)
        if not site_to_leave.isdigit():
            print(console_log('Unexpected error in my_sites (leaving site), user may be tampering with requests', 'warn'))
            flash('Something went wrong 2')
            return redirect('/my_sites')
        site_to_leave = int(site_to_leave)
        site_info = cursor.execute('SELECT id, name from SITES WHERE id = ?', (site_to_leave,)).fetchone()
        if not site_info:
            print(console_log('User ' + session['email'] + ' tried to leave a nonexistent site', 'error'))
            flash('Something went wrong 3')
            return redirect('/my_sites')
        try:
            cursor.execute('DELETE FROM site_members WHERE site_id = ? AND user_id = ?', (site_to_leave, uid))
            conn.commit()
            print(console_log(session['email'] + ' successfully left the site ' +  site_info[1], 'success'))
            flash('Successfully left ' + site_info[1] + '!')
            return redirect('/my_sites')
        except sqlite3.Error as e:
            flash('Something went wrong 4')
            print(console_log(session['email'] + ' incountered error ' + str(e) + ' when leaving a site', 'error'))
            return redirect('/my_sites')
        finally:
            conn.close()
    sites_ids = cursor.execute('SELECT site_id FROM site_members WHERE user_id = ?', (uid,)).fetchall()
    if not sites_ids:
        conn.close()
        return render_template('my_sites.html', no_sites = True)
    for site_id in sites_ids:
        site_id = site_id[0]
        site = cursor.execute('SELECT name, owner FROM sites WHERE id = ?', (site_id,)).fetchone()
        if not site:
            print(console_log('Something went wrong line 157.', 'error'))
            flash('Something went wrong')
            return redirect('/my_sites')
        owner_name = cursor.execute('SELECT name FROM users WHERE id = ?', (site[1],)).fetchone()[0]
        site_name = site[0]
        sites.append((site_id, site_name, owner_name))
    return render_template('my_sites.html', sites=sites)

# @app.route('/create_site', methods = ["GET", "POST"])
# def create_site():
#     if 'uid' not in session:
#         return redirect('/')
#     if request.method == "POST":
#         conn, cursor = init_conn()
#         site_name = request.form['site_name']
#         site_password = request.form['site_password']
#         site_members = request.form['site_members']
#         if not site_name or not site_password or not site_members:
#             print(console_log('Unexpected error in create_sites, user may be tampering with requests', 'warn'))
#             flash('Error')
#             return redirect('/create_site')
#         creator_id = cursor.execute('SELECT id FROM users WHERE email = ?', (session['email'],)).fetchone()[0]
#         does_it_exist = cursor.execute('SELECT 1 FROM sites WHERE name = ?', (site_name,)).fetchone()
#         if does_it_exist == True:
#             flash('Site already exists!')
#             return redirect('/create_site')
#         try:
#             cursor.execute('INSERT INTO sites (name, owner, password) VALUES (?, ?, ?) ', (site_name, creator_id, site_password))
#             console_log('User ' + session['email'] + 'successfully created site' + site_name, 'success')
#             conn.commit()
#             flash('Successfully created site ' + site_name + '!')
#             return redirect('/create_site')
#         except sqlite3.Error as e:
#             flash('Error')
#             print(console_log(session['email'] + 'got an error when creating site: ' + str(e), 'error'))
#             return redirect('/create_site')
#         finally:
#             conn.close()

@app.route('/my_profile', methods = ["GET", "POST"])
def my_profile():
    if 'uid' not in session:
        return redirect('/')
    conn, cursor = init_conn()
    id, name = cursor.execute('SELECT id, name FROM users WHERE email = ?', (session['email'],)).fetchone()
    if request.method == 'POST':
        thing_to_change = request.form['thing_to_change']
        if thing_to_change == 'email':
            new_email = request.form['email']
            if new_email == session['email']:
                flash('New email cannot be the same as the old one!')
                console_log(session['email'] + ' tried to update their email but reused the old one', 'info')
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
            new_name = request.form['name']
            if new_name == session['name']:
                flash('New name cannot be the same as the old one!')
                console_log(session['email'] + ' tried to update their name but reused the old one', 'info')
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
            new_name = request.form['password']
            if new_name == session['password']:
                flash('New password cannot be the same as the old one!')
                console_log(session['email'] + ' tried to update their password but reused the old one', 'info')
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
    if request.method == 'POST':
        site_name = request.form['name']
        site_password = request.form['password']
        if not cursor.execute('SELECT 1 FROM sites WHERE name = ?', (site_name,)).fetchone():
            flash('Site does not exist!')
            print(console_log(f'{session["email"]} tried to join a nonexistent site', 'info'))
            conn.close()
            return redirect('/join_site')
        site_info = cursor.execute('SELECT id, password, owner FROM sites WHERE name = ?', (site_name,)).fetchone()
        site_id = site_info[0]
        if site_info[1] != site_password:
            flash('Incorrect password')
            print(console_log(f'{session["email"]} entered the wrong password to join {site_name}', 'info'))
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
            cursor.execute('INSERT INTO site_members (site_id, user_id) VALUES (?, ?)', (site_id, session['id']))
            conn.commit()
            flash(f'Successfully joined {site_name}!')
            console_log(f'{session["email"]} successfully joined {site_name}', 'success')
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
    if request.method == 'POST':
        site_name = request.form['name']
        site_password = request.form['password']
        site_members = request.form.getlist('site_members')
        if cursor.execute('SELECT 1 FROM sites WHERE name = ?', (site_name,)).fetchone():
            print(console_log(f'{session["email"]} tried to create the site {site_name}, already exists', 'info'))
            flash('Site exists!')
            conn.close()
            return redirect('/create_site')
        try:
            cursor.execute('INSERT INTO sites (name, owner) VALUES (?, ?)', (site_name, session['uid']))
            site_id = cursor.execute('SELECT id FROM sites WHERE name = ?', (site_name,)).fetchone()[0]
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

@app.route('/sites', methods = ["GET", "POST"])
def browse_sites():
    if 'email' not in session:
        print(console_log('User with no account tried to access browse sites endpoint.', 'warn'))
        return redirect('/')
    conn, cursor = init_conn()
    sites = cursor.execute('SELECT * FROM sites').fetchall()
    artefacts = cursor.execute('SELECT * FROM artefacts').fetchall()
    site_members = cursor.execute('SELECT * FROM site_members').fetchall()
    return render_template('browse_sites.html', sites=sites, artefacts=artefacts, site_members=site_members)
if __name__ == '__main__':
    print(console_log('Starting server', 'info'))
    init_db()
    app.run(debug=False)