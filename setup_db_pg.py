"""
============================================
FixNear — PostgreSQL Database Setup Script
For Neon.tech / Render deployment
============================================
Usage: DATABASE_URL="postgresql://..." python setup_db_pg.py
"""

import os
import sys
import bcrypt

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set!")
    print("Usage: DATABASE_URL=\"postgresql://user:pass@host/dbname\" python setup_db_pg.py")
    sys.exit(1)

import psycopg2

def hash_password(pw):
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def main():
    print("=" * 50)
    print("  FixNear — PostgreSQL Database Setup")
    print("=" * 50)

    # Read the PostgreSQL SQL file
    sql_path = os.path.join(os.path.dirname(__file__), 'database', 'fixnear_pg.sql')
    if not os.path.exists(sql_path):
        print(f"ERROR: SQL file not found at {sql_path}")
        return

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Connect to PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Execute the SQL file
    print("[1/3] Creating tables and inserting seed data...")
    try:
        cur.execute(sql_content)
        print("  [OK] Schema created successfully!")
    except Exception as e:
        print(f"  Warning: {e}")

    cur.close()

    # Re-hash passwords with Python bcrypt
    print("[2/3] Setting passwords for seed accounts...")
    cur = conn.cursor()

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
        print(f"  [OK] {email}")

    cur.close()
    conn.close()

    print("[3/3] Done!")
    print()
    print("  Admin login:  admin@fixnear.com / admin123")
    print("  Tech login:   rajesh@fixnear.com / tech123")
    print()
    print("  Your app is ready to deploy on Render!")
    print("=" * 50)

if __name__ == '__main__':
    main()
