import os

import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, g
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
load_dotenv()
import requests

# configure application
app = Flask(__name__)
# secret key for sessions
app.secret_key = os.environ.get("SECRET_KEY")

#email configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME")
mail = Mail(app)

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

@app.route("/profile")
@login_required
def profile():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?",(session["user_id"],)).fetchone()
    task_count = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (session["user_id"],)).fetchone()[0]
    completed_count = db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 1", (session["user_id"],)).fetchone()[0]
    return render_template("profile.html", user=user, task_count=task_count, completed_count=completed_count)


@app.route("/upload_profile_pic", methods=["POST"])
@login_required
def upload_profile_pic():
    if "profile_pic" not in request.files:
        return redirect("/profile")
    
    file = request.files["profile_pic"]
    if file.filename == "":
        return redirect("/profile")
    

    #Save file with user_id as filename to avoid conflicts
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "gif", "webp"]:
        return redirect("/profile")
    
    filename = f"profile_{session['user_id']}.{ext}"
    file.save(os.path.join("static/uploads", filename))
    
    db = get_db()
    db.execute("UPDATE users SET profile_pic = ? WHERE id = ?", (filename, session["user_id"]))
    db.commit()
    return redirect("/profile")

# fetch motivational quote from API
def fetch_quote():
    try:
        response = requests.get("https://zenquotes.io/api/random", timeout=5)
        data = response.json()
        return f'"{data[0]["q"]}" - {data[0]["a"]}'
    except Exception as e:
        print("Fetch Quote Failed", e)
        return '"If u dont do it now, you will do it never."'
        
def check_and_send_reminders():
    with app.app_context():
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        now = datetime.now().strftime("%Y-%m-%dT%H:%M")
        due_tasks = conn.execute("""
            SELECT tasks.id, tasks.title, tasks.description, tasks.due_at,
                   users.email, users.username
            FROM tasks
            JOIN users ON tasks.user_id= users.id
            WHERE tasks.reminded = 0
              AND tasks.due_at IS NOT NULL
              AND tasks.due_at <= ?
              AND tasks.completed = 0
        """,(now,)).fetchall()

        for task in due_tasks:
            quote = fetch_quote()
            try:
                msg = Message(
                    subject=f"⏰ Reminder: {task['title']}",
                    sender=os.environ.get("MAIL_USERNAME"),
                    recipients=[task["email"]]
                )
                msg.body = f"""Hi {task['username']},

This is a reminder for your task: {task['title']}
{f"Description: {task['description']}" if task['description'] else ""}

Today's motivation:
{quote}

Believe it. Dattebayo! 💪
"""
               
                mail.send(msg)
            except Exception as e:
                print(f"failed to send email for task {task['id']}: {e}")

            conn.execute("UPDATE tasks SET reminded = 1 WHERE id = ?", (task["id"],))
            conn.commit()
        
        conn.close()


# Start scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_reminders, "interval", minutes=1)
scheduler.start()        

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

        if not username or not email or not password:
            return render_template("register.html", error="All fields are required ")

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
    due_at = request.form.get("due_at")

    db = get_db()
    db.execute("INSERT INTO tasks (user_id, title, description, due_at) VALUES (?, ?, ?, ?)",
               (session["user_id"], title, description, due_at))
    db.commit()
    return redirect("/")

@app.route("/set_reminder/<int:task_id>", methods=["POST"])
@login_required
def set_reminder(task_id):
    due_at = request.form.get("due_at")
    db = get_db()
    db.execute("UPDATE tasks SET due_at = ?, reminded = 0 WHERE id = ? AND user_id = ?", (due_at, task_id, session["user_id"]))
    db.commit()
    return redirect("/")

@app.route("/check_reminders")
@login_required
def check_reminders():
    db = get_db()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    due = db.execute("""
        SELECT id, title FROM tasks
        WHERE user_id = ? AND browser_reminded = 0 AND due_at IS NOT NULL
        AND due_at <= ?
        AND completed = 0
    """, (session["user_id"], now)).fetchall()

    results = []
    for task in due:
        quote = fetch_quote()
        results.append({"id": task["id"], "title": task["title"], "quote": quote })
        db.execute("UPDATE tasks SET browser_reminded = 1 WHERE id = ?", (task["id"],))
    db.commit()

    return jsonify(results)

@app.route("/delete_task/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, session["user_id"]))
    db.commit()
    return redirect("/")

@app.route("/complete_task/<int:task_id>",methods=["POST"])
@login_required
def complete_task(task_id):
    db = get_db()
    db.execute("UPDATE tasks SET completed = 1 WHERE id = ? AND user_id = ?", (task_id, session["user_id"]))
    db.commit()
    return redirect("/")

@app.route("/incomplete_task/<int:task_id>", methods=["POST"])
@login_required
def incomplete_task(task_id):
    db = get_db()
    db.execute("UPDATE tasks SET completed = 0 WHERE id = ? AND user_id = ?", (task_id, session["user_id"]))
    db.commit()
    return redirect("/")



@app.route("/history")
@login_required
def history():
    db = get_db()
    completed_tasks = db.execute("SELECT * FROM tasks WHERE user_id = ? AND completed = 1 ORDER BY created_at DESC", (session["user_id"],)).fetchall()
    return render_template("history.html", tasks=completed_tasks)

@app.route("/clear_history", methods=["POST"])
@login_required
def clear_history():
    db = get_db()
    db.execute("DELETE FROM tasks WHERE user_id = ? AND completed = 1", (session["user_id"],))
    db.commit()
    return redirect("/history")

@app.route("/logout")
def logout():
    # Clear the user session to log out the user.
    session.clear()
    # Redirect the user to the login page.
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)