from flask import Flask, render_template, request, redirect, url_for, session, flash
import time
import secrets
import sqlite3

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   email TEXT UNIQUE NOT NULL,
                   username TEXT NOT NULL,
                   password TEXT NOT NULL)""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS sites(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   owner_id INTEGER NOT NULL,
                   FOREIGN KEY (owner_id) REFERENCES users(id))""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS site_members(
                   site_id INTEGER NOT NULL,
                   user_id INTEGER NOT NULL,
                   PRIMARY KEY (site_id, user_id),
                   FOREIGN KEY (site_id) REFERENCES sites(id),
                   FOREIGN KEY (user_id) REFERENCES users(id))""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS artefacts(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT UNIQUE,
                   amount INTEGER,
                   weight FLOAT)
    """)

def connect_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    return conn, cursor
    


@app.route('/', methods = ["GET", "POST"])
def home():
    return render_template('home.html')

@app.route('/signup', methods = ["GET", "POST"])
def signup():
    if request.method == "POST" and "signup" in request.form:
        conn, cursor = connect_db()
        provided_username = request.form['provided_username']
        provided_email = request.form['provided_email']
        provided_password = request.form['provided_password']
        row_exists = cursor.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (provided_email,)).fetchone()
        if row_exists:
            flash("Account Exists")
            return redirect('/signup')
        else:
            cursor.execute("""INSERT INTO users(email, username, password) VALUES(?, ?, ?)""", (provided_email, provided_username, provided_password))
            conn.commit()
            conn.close()
            flash("Signup successful!")
            return redirect('/signup')
    return render_template('signup.html')

@app.route('/login', methods = ["GET", "POST"])
def login():
    if request.method == "POST" and "login" in request.form:
        conn, cursor = connect_db()
        provided_username = request.form['username']
        provided_email = request.form['email']
        provided_password = request.form['password']
        row_exists = cursor.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (provided_email,)).fetchone()
        if row_exists:
            flash("Account Exists")
            return redirect('/signup')
        else:
            




if __name__ == "__main__":
    init_db()
    app.run()