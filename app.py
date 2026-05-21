import os

import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, g
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
load_dotenv()
import requests

# configure application
app = Flask(__name__)

# secret key for sessions
app.secret_key = os.environ.get("SECRET_KEY")

#configure sqlite3
DATABASE = "productivity.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory =sqlite3.Row # access columns by name
    return g.db

@app.teardown_appcontext        # runs automatically after  every request.
def close_db(error):            # catch any error that occurs during request handling
    db = g.pop("db", None)      # remove the db connection from g, if it exists
    if db is not None:          # if a db connection was established, then only close.
        db.close()              # close the db connection.

# login required decorator
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# home page route
@app.route("/")
@login_required
def index():
    db = get_db() #get database connection
    tasks = db.execute("SELECT * FROM tasks WHERE user_id = ?", 
                      (session["user_id"],)).fetchall()
    return render_template("index.html", tasks=tasks) 

# route for user registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Insert the new user into the database
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                       (username, email, hashed_password))
            db.commit()
            return redirect("/login")
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username or email already exists")

    return render_template("register.html")

# route for user login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect("/")
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route("/add_task", methods=["POST"])
@login_required
def add_task():
    title = request.form.get("title")
    description = request.form.get("description")

    db = get_db()
    db.execute("INSERT INTO tasks (user_id, title, description) VALUES (?, ?, ?)",
               (session["user_id"], title, description))
    db.commit()
    return redirect("/")

# route for user logout
@app.route("/logout")
def logout():
    # Clear the user session to log out the user.
    session.clear()
    # Redirect the user to the login page.
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)