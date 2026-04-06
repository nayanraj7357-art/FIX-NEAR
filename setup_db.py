"""
============================================
FixNear — Database Setup Script (MySQL)
Replaces setup.php for the Python/Flask version
============================================
Passwords are generated randomly at runtime.
NO passwords are stored in this file.
============================================
"""

import mysql.connector
import bcrypt
import os
import secrets
import string

DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASS = ''

def hash_password(pw):
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def generate_password(length=10):
    """Generate a random secure password."""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

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

    # Generate random passwords for seed accounts
    print("[2/3] Setting secure random passwords for seed accounts...")
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, database='fixnear')
    cur = conn.cursor(dictionary=True)

    admin_password = os.environ.get('ADMIN_PASSWORD') or generate_password(12)
    tech_password = os.environ.get('TECH_PASSWORD') or generate_password(10)

    seed_emails = {
        'admin@fixnear.com': admin_password,
        'rajesh@fixnear.com': tech_password,
        'amit@fixnear.com': tech_password,
        'sunil@fixnear.com': tech_password,
        'vikram@fixnear.com': tech_password,
        'rakesh@fixnear.com': tech_password,
        'deepak@fixnear.com': tech_password,
        'manoj@fixnear.com': tech_password,
        'arun@fixnear.com': tech_password,
        'sanjay@fixnear.com': tech_password,
        'kiran@fixnear.com': tech_password,
    }

    for email, plain_pw in seed_emails.items():
        hashed = hash_password(plain_pw)
        cur.execute("UPDATE users SET password=%s WHERE email=%s", (hashed, email))
        conn.commit()
        print(f"  [OK] {email}")

    cur.close()
    conn.close()

    print("[3/3] Done!")
    print()
    print("=" * 50)
    print("  SAVE THESE CREDENTIALS (generated randomly):")
    print("=" * 50)
    print(f"  Admin login:  admin@fixnear.com / {admin_password}")
    print(f"  Tech login:   rajesh@fixnear.com / {tech_password}")
    print()
    print("  ⚠️  These passwords are NOT stored in code.")
    print("  ⚠️  Save them now — you won't see them again!")
    print()
    print("  Run the app:  python app.py")
    print("  Open:         http://localhost:5000")
    print("=" * 50)

if __name__ == '__main__':
    main()
