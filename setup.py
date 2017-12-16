''' Setup database tables for snap.py. Running setup repeatedly always clears the database. '''

import sqlite3

# create new db
db_con = sqlite3.connect('forum.db')
with db_con:
    db = db_con.cursor()
    db.execute("DROP TABLE IF EXISTS Posts")
    db.execute("CREATE TABLE IF NOT EXISTS Posts("
               "PostID INTEGER PRIMARY KEY"
               ", ThreadID INTEGER NOT NULL"
               ", UserName CHARACTER"
               ", Time DATETIME"
               ", Content TEXT"
               ", PostURL VARCHAR"
               ", BaseURL VARCHAR"
               ", FOREIGN KEY (ThreadID) REFERENCES Threads(ThreadID)"
               ")"
               )

    db.execute("DROP TABLE IF EXISTS Threads")
    db.execute("CREATE TABLE IF NOT EXISTS Threads("
               "ThreadID INTEGER PRIMARY KEY"
               ", UserName CHARACTER"
               ", Time DATETIME"
               ", Title VARCHAR"
               ", ThreadURL VARCHAR"
               ", BaseURL VARCHAR"
               ")"
               )