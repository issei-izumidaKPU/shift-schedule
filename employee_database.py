import sqlite3

def create_connection():
    conn = sqlite3.connect('employees.db')
    return conn

def create_table():
    conn = create_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
                 id INTEGER PRIMARY KEY,
                 name TEXT NOT NULL,
                 email TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def insert_employee(name, email):
    conn = create_connection()
    c = conn.cursor()
    c.execute("INSERT INTO employees (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    conn.close()

def get_employee_email(name):
    conn = create_connection()
    c = conn.cursor()
    c.execute("SELECT email FROM employees WHERE name=?", (name,))
    email = c.fetchone()
    conn.close()
    return email[0] if email else None

# 初回実行時にテーブルを作成
create_table()

# テストデータを追加（必要に応じて）
insert_employee('泉田', 'pandamanhaoji@gmail.com')
insert_employee('田中', 'tanaka@example.com')
