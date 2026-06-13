
CREATE TABLE resources (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    name    TEXT NOT NULL,
    url     TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL UNIQUE,
    email       TEXT NOT NULL UNIQUE,
    password    TEXT NOT NULL,
    profile_pic TEXT
);

CREATE TABLE tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    title       TEXT NOT NULL,
    description TEXT,
    completed   INTEGER DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    due_at      DATETIME,
    reminded    INTEGER DEFAULT 0,
    browser_reminded INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
