"""
============================================
FixNear — Database Setup Script
Replaces setup.php for the Python/Flask version
============================================
"""

import mysql.connector
import bcrypt
import os

DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASS = ''

def hash_password(pw):
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def main():
    print("=" * 50)
    print("  FixNear — Database Setup")
    print("=" * 50)

    # Read the SQL file
    sql_path = os.path.join(os.path.dirname(__file__), 'database', 'fixnear.sql')
    if not os.path.exists(sql_path):
        print(f"ERROR: SQL file not found at {sql_path}")
        return

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Connect without specifying a database (we'll create it)
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
    cur = conn.cursor()

    # Execute the SQL file (statement by statement)
    print("[1/3] Executing database schema...")
    statements = sql_content.split(';')
    for stmt in statements:
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--'):
            try:
                cur.execute(stmt)
                conn.commit()
            except mysql.connector.Error as e:
                # Skip harmless errors
                if e.errno not in (1065,):  # empty query
                    print(f"  Warning: {e.msg}")

    cur.close()
    conn.close()

    # Now re-hash the seed passwords with Python bcrypt
    print("[2/3] Re-hashing seed passwords for Python bcrypt compatibility...")
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database='fixnear')
    cur = conn.cursor(dictionary=True)

    # Map of seed emails to their plain-text passwords
    seed_passwords = {
        'admin@fixnear.com': 'admin123',
        'rajesh@fixnear.com': 'tech123',
        'amit@fixnear.com': 'tech123',
        'sunil@fixnear.com': 'tech123',
        'vikram@fixnear.com': 'tech123',
        'rakesh@fixnear.com': 'tech123',
        'deepak@fixnear.com': 'tech123',
        'manoj@fixnear.com': 'tech123',
        'arun@fixnear.com': 'tech123',
        'sanjay@fixnear.com': 'tech123',
        'kiran@fixnear.com': 'tech123',
    }

    for email, plain_pw in seed_passwords.items():
        hashed = hash_password(plain_pw)
        cur.execute("UPDATE users SET password=%s WHERE email=%s", (hashed, email))
        conn.commit()
        print(f"  [OK] {email}")

    cur.close()
    conn.close()

    print("[3/3] Done!")
    print()
    print("  Admin login:  admin@fixnear.com / admin123")
    print("  Tech login:   rajesh@fixnear.com / tech123")
    print()
    print("  Run the app:  python app.py")
    print("  Open:         http://localhost:5000")
    print("=" * 50)

if __name__ == '__main__':
    main()
