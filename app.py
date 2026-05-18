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


@app.route("/")
def index():
    db = get_db() #get database connection
    tasks = db.execute("SELECT * FROM tasks WHERE user_id = ?", 
                      (session["user_id"],)).fetchall()
    return render_template("index.html", tasks=tasks) 
