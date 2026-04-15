import sqlite3
import time

DB_NAME = "data.db"


def get_conn():
    return sqlite3.connect(DB_NAME)


# ================= INIT =================
def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        chat_id INTEGER,
        key TEXT,
        value TEXT,
        PRIMARY KEY (chat_id, key)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        chat_id INTEGER PRIMARY KEY,
        title TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS members (
        chat_id INTEGER,
        user_id INTEGER,
        username TEXT,
        full_name TEXT,
        PRIMARY KEY (chat_id, user_id)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        user_id INTEGER,
        username TEXT,
        display_name TEXT,
        target_name TEXT,
        kind TEXT,
        raw_amount REAL,
        unit_amount REAL,
        rate_used REAL,
        fee_used REAL,
        note TEXT,
        original_text TEXT,
        created_at INTEGER,
        undone INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS access_users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        granted_by INTEGER,
        granted_at INTEGER,
        expires_at INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS rental_orders (
        order_code TEXT PRIMARY KEY,
        user_id INTEGER,
        username TEXT,
        full_name TEXT,
        category_key TEXT,
        category_title TEXT,
        plan_key TEXT,
        plan_label TEXT,
        amount REAL,
        status TEXT,
        created_at INTEGER,
        paid_at INTEGER,
        expires_at INTEGER,
        note TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS trial_code (
        id INTEGER PRIMARY KEY,
        code TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS trial_users (
        user_id INTEGER PRIMARY KEY
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS wallet_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        address TEXT,
        result TEXT,
        created_at INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS expiry_notice (
        user_id INTEGER,
        notice_key TEXT,
        PRIMARY KEY (user_id, notice_key)
   )
   """)

    conn.commit()
    conn.close()


# ================= SETTINGS =================
def get_setting(chat_id, key, default=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE chat_id=? AND key=?", (chat_id, key))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(chat_id, key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO settings VALUES (?, ?, ?)
    ON CONFLICT(chat_id, key) DO UPDATE SET value=excluded.value
    """, (chat_id, key, str(value)))
    conn.commit()
    conn.close()


# ================= ADMIN =================
def add_admin(user_id, role="admin"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO admins VALUES (?, ?)", (user_id, role))
    conn.commit()
    conn.close()


def remove_admin(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def get_admin(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT role FROM admins WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_all_admins():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, role FROM admins")
    rows = c.fetchall()
    conn.close()
    return rows


# ================= GROUP =================
def save_group(chat_id, title):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO groups VALUES (?, ?)", (chat_id, title))
    conn.commit()
    conn.close()


def get_groups():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT chat_id, title FROM groups")
    rows = c.fetchall()
    conn.close()
    return rows


def save_member(chat_id, user_id, username, full_name):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT OR REPLACE INTO members VALUES (?, ?, ?, ?)
    """, (chat_id, user_id, username, full_name))
    conn.commit()
    conn.close()


# ================= OPERATOR =================
def is_operator(chat_id, user_id=None, username=None):
    return True


# ================= TRANSACTIONS =================
def add_transaction(chat_id, user_id, username, display_name,
                    target_name, kind, raw_amount, unit_amount,
                    rate_used, fee_used, note, original_text):
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    INSERT INTO transactions (
        chat_id, user_id, username, display_name,
        target_name, kind, raw_amount, unit_amount,
        rate_used, fee_used, note, original_text, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        chat_id, user_id, username, display_name,
        target_name, kind, raw_amount, unit_amount,
        rate_used, fee_used, note, original_text,
        int(time.time())
    ))

    conn.commit()
    conn.close()


def get_last_transaction(chat_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    SELECT * FROM transactions
    WHERE chat_id=? AND undone=0
    ORDER BY id DESC LIMIT 1
    """, (chat_id,))
    row = c.fetchone()
    conn.close()
    return row


def undo_transaction(tx_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE transactions SET undone=1 WHERE id=?", (tx_id,))
    conn.commit()
    conn.close()


def get_transactions(chat_id, start_ts=None, end_ts=None, user_id=None):
    conn = get_conn()
    c = conn.cursor()

    query = "SELECT * FROM transactions WHERE chat_id=? AND undone=0"
    params = [chat_id]

    if start_ts:
        query += " AND created_at>=?"
        params.append(start_ts)

    if end_ts:
        query += " AND created_at<=?"
        params.append(end_ts)

    if user_id:
        query += " AND user_id=?"
        params.append(user_id)

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


# ================= TRIAL =================
def set_trial_code(code):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM trial_code")
    c.execute("INSERT INTO trial_code VALUES (1, ?)", (code,))
    conn.commit()
    conn.close()


def get_trial_code():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT code FROM trial_code LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""


def has_claimed_free_trial(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM trial_users WHERE user_id=?", (user_id,))
    exists = c.fetchone()
    conn.close()
    return bool(exists)


def mark_claimed_free_trial(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO trial_users VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


# ================= ACCESS =================
def add_access_user(user_id, username, granted_by=None, expires_at=None):
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    INSERT OR REPLACE INTO access_users
    VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        granted_by,
        int(time.time()),
        expires_at
    ))

    conn.commit()
    conn.close()


def has_access_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM access_users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row)


def get_access_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM access_users")
    rows = c.fetchall()
    conn.close()
    return rows


def get_access_user_by_id(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM access_users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


# ================= RENT =================
def create_rental_order(order_code, user_id, username, full_name,
                        category_key, category_title,
                        plan_key, plan_label, amount):
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
    INSERT INTO rental_orders
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_code, user_id, username, full_name,
        category_key, category_title,
        plan_key, plan_label, amount,
        "pending", int(time.time()), None, None, None
    ))

    conn.commit()
    conn.close()


def get_rental_order(order_code):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM rental_orders WHERE order_code=?", (order_code,))
    row = c.fetchone()
    conn.close()
    return row


def get_pending_rental_orders():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM rental_orders WHERE status='pending'")
    rows = c.fetchall()
    conn.close()
    return rows


def get_rental_orders_by_status(status):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM rental_orders WHERE status=?", (status,))
    rows = c.fetchall()
    conn.close()
    return rows


def mark_rental_order_paid(order_code, expires_at=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    UPDATE rental_orders
    SET status='paid', paid_at=?, expires_at=?
    WHERE order_code=?
    """, (int(time.time()), expires_at, order_code))
    conn.commit()
    conn.close()


def mark_rental_order_rejected(order_code):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE rental_orders SET status='rejected' WHERE order_code=?", (order_code,))
    conn.commit()
    conn.close()


# ================= WALLET =================
def add_wallet_check(address, result):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO wallet_checks (address, result, created_at)
    VALUES (?, ?, ?)
    """, (address, result, int(time.time())))
    conn.commit()
    conn.close()


def get_wallet_checks_page(page=1, page_size=10):
    offset = (page - 1) * page_size
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    SELECT * FROM wallet_checks
    ORDER BY id DESC
    LIMIT ? OFFSET ?
    """, (page_size, offset))
    rows = c.fetchall()
    conn.close()
    return rows


def count_wallet_checks():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM wallet_checks")
    count = c.fetchone()[0]
    conn.close()
    return count

def has_expiry_notice(user_id, key):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT 1 FROM expiry_notice WHERE user_id=? AND notice_key=?",
        (user_id, key)
    )
    row = c.fetchone()
    conn.close()
    return bool(row)


def add_expiry_notice(user_id, key):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO expiry_notice VALUES (?, ?)",
        (user_id, key)
    )
    conn.commit()
    conn.close()
    
# ================= BUTTON CONFIG =================
def get_all_button_configs():
    return []
    
def is_operator(chat_id, user_id=None, username=None):
    return True
