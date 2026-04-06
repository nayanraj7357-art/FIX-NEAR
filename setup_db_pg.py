"""
============================================
FixNear — PostgreSQL Database Setup Script
For Neon.tech / Render deployment
============================================
Usage: DATABASE_URL="postgresql://..." python setup_db_pg.py

Passwords are generated randomly at runtime.
NO passwords are stored in this file.
============================================
"""

import os
import sys
import bcrypt
import secrets
import string

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set!")
    print('Usage: DATABASE_URL="postgresql://user:pass@host/dbname" python setup_db_pg.py')
    sys.exit(1)

import psycopg2

def hash_password(pw):
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def generate_password(length=10):
    """Generate a random secure password."""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

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

    # Generate random passwords for seed accounts
    print("[2/3] Setting secure random passwords for seed accounts...")
    cur = conn.cursor()

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
    print("  Your app is ready to deploy on Render!")
    print("=" * 50)

if __name__ == '__main__':
    main()
