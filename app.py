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