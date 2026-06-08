import requests
import sqlite3

from functools import wraps
from flask import session, redirect, g, abort

DATABASE = "productivity.db"

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error):
    db = g.pop("db", None)    
    if db is not None:
        db.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def get_motivational_quote():
    try:
        response = requests.get("https://api.quotable.io/random")
        if response.status_code == 200:
            data = response.json()
            return f"{data['content']} - {data['author']}"
        else:
            return "Stay motivated and keep pushing forward!"
    except Exception as e:
        print(f"Error fetching quote: {e}")
        return "Stay motivated and keep pushing forward!"

    def get_tasks_for_user(user_id):
        db = get_db()
        tasks = db.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,)).fetchall()

        if not tasks:
            abort(404, description="No tasks found for this user")
        return tasks
    
    def validate_task(title, description):
        if not title or not description:
            return False, "Title and description are required."
        if len(title) > 100:
            return False, "Title must be less than 100 characters."
        if len(description) > 500:
            return False, "Description must be less than 500 characters."
        return True, ""

    def get_task_by_id(task_id, user_id):
        db = get_db()
        task = db.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).fetchone()
        if task is None:
            abort(404, description = "Task not found")
        return task