#define the imports
from flask import Flask, render_template, request, redirect, url_for, session, flash
import time
import secrets
import sqlite3


#initialize the app and secret key
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


#initialize the database
def init_db():
    #create the datasbase, or connect if it exists
    conn = sqlite3.connect('database.db')
    #open a cursor to perform db operations
    cursor = conn.cursor()
    #create the tables
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

#this func exists to connect to the database and open a cursor 
def connect_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    return conn, cursor
    

#define the what happens when the users hits the / route (main page)
@app.route('/', methods = ["GET", "POST"])
def home():
    return render_template('home.html')

#same for signup 
@app.route('/signup', methods = ["GET", "POST"])
def signup():
    #if the user is sending data (post req) 
    if request.method == "POST" and "signup" in request.form:
        #connect to the db with the function i made earlier
        conn, cursor = connect_db()
        #define the variables from the form
        provided_username = request.form['provided_username']
        provided_email = request.form['provided_email']
        provided_password = request.form['provided_password']
        #check if the email already exists (so theres not duplicate accounts)
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
            row = cursor.execute("SELECT password FROM users WHERE email = ?", (provided_email,)).fetchone()
            db_pass = row[-1]
            if provided_password == row[-1]:
                session['email'] = provided_email
                session['username'] = provided_username
                flash('loginsucessful')
                return redirect('/')

        else:
            pass
    return render_template('login.html')




if __name__ == "__main__":
    init_db()
    app.run(debug=True)