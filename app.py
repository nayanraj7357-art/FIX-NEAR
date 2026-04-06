"""
============================================
FixNear — Python Flask Backend
Online Home Service Booking Platform
============================================
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from dotenv import load_dotenv
import bcrypt
import string
import random
import os
import uuid

# Load .env file (local development only — on Render, env vars are set in Dashboard)
load_dotenv()

# Auto-detect database: PostgreSQL (Render) or MySQL (localhost)
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras
    DB_TYPE = 'pg'
else:
    import mysql.connector
    DB_TYPE = 'mysql'

# ============================================
# APP CONFIG
# ============================================
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'fixnear_local_dev_key_change_in_production')

# ============================================
# FILE UPLOAD CONFIG
# ============================================
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file):
    """Save an uploaded file with a unique name. Returns the filename or None."""
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)
        return unique_name
    return None

# ============================================
# DATABASE CONFIG
# Localhost → MySQL | Render → PostgreSQL (auto-detect)
# ============================================
if DB_TYPE == 'mysql':
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'fixnear',
        'charset': 'utf8mb4',
        'autocommit': True
    }

class PgConnectionWrapper:
    """Wraps psycopg2 connection so db.cursor(dictionary=True) works like MySQL."""
    def __init__(self, conn):
        self._conn = conn
    def cursor(self, dictionary=False, **kw):
        if dictionary:
            return self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return self._conn.cursor(**kw)
    def close(self):
        self._conn.close()
    def __getattr__(self, name):
        return getattr(self._conn, name)

def get_db():
    if DB_TYPE == 'pg':
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return PgConnectionWrapper(conn)
    return mysql.connector.connect(**DB_CONFIG)

# ============================================
# HELPERS
# ============================================
def is_logged_in(): return 'user_id' in session
def is_admin(): return is_logged_in() and session.get('user_role') == 'admin'
def is_technician(): return is_logged_in() and session.get('user_role') == 'technician'
def get_user():
    if is_logged_in():
        return {'id': session['user_id'], 'name': session['user_name'], 'email': session['user_email'], 'role': session['user_role']}
    return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in(): return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_admin(): return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def technician_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_technician(): return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def hash_password(pw):
    return bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(pw, hashed):
    # PHP bcrypt uses $2y$, PostgreSQL pgcrypto uses $2a$; Python bcrypt expects $2b$
    if hashed.startswith('$2y$') or hashed.startswith('$2a$'):
        hashed = '$2b$' + hashed[4:]
    return bcrypt.checkpw(pw.encode('utf-8'), hashed.encode('utf-8'))

# ============================================
# PUBLIC ROUTES
# ============================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        db = get_db(); cur = db.cursor()
        cur.execute("INSERT INTO contact_messages (name, email, subject, message) VALUES (%s,%s,%s,%s)",
                    (request.form['name'], request.form['email'], request.form.get('subject',''), request.form['message']))
        db.close(); flash('Message sent successfully!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

# ============================================
# AUTH ROUTES
# ============================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        if not email or not password:
            flash('Email and password are required.', 'error')
            return redirect(url_for('login'))
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, name, email, password, role FROM users WHERE email=%s", (email,))
        user = cur.fetchone(); db.close()
        if user and check_password(password, user['password']):
            session['user_id'] = user['id']; session['user_name'] = user['name']
            session['user_email'] = user['email']; session['user_role'] = user['role']
            if user['role'] == 'admin': return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'technician': return redirect(url_for('technician_dashboard'))
            else: return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip(); email = request.form.get('email','').strip()
        phone = request.form.get('phone','').strip(); password = request.form.get('password','')
        confirm = request.form.get('confirm_password','')
        errors = []
        if not name: errors.append('Full name is required.')
        if not email: errors.append('Email is required.')
        if not phone: errors.append('Phone number is required.')
        if len(password) < 6: errors.append('Password must be at least 6 characters.')
        if password != confirm: errors.append('Passwords do not match.')
        if not errors:
            db = get_db(); cur = db.cursor()
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone(): errors.append('Email already registered.')
            else:
                hashed = hash_password(password)
                cur.execute("INSERT INTO users (name,email,phone,password) VALUES (%s,%s,%s,%s)", (name,email,phone,hashed))
                db.close(); flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            db.close()
        for e in errors: flash(e, 'error')
        return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

# ============================================
# USER DASHBOARD
# ============================================
@app.route('/dashboard')
@login_required
def user_dashboard():
    if is_admin(): return redirect(url_for('admin_dashboard'))
    if is_technician(): return redirect(url_for('technician_dashboard'))
    user = get_user(); db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) as c FROM bookings WHERE user_id=%s", (user['id'],)); total = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM bookings WHERE user_id=%s AND status IN ('pending','confirmed','in_progress')", (user['id'],)); active = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM bookings WHERE user_id=%s AND status='completed'", (user['id'],)); completed = cur.fetchone()['c']
    cur.execute("""SELECT b.*, s.name AS service_name, s.icon AS service_icon, t.name AS technician_name
        FROM bookings b JOIN services s ON b.service_id=s.id LEFT JOIN technicians t ON b.technician_id=t.id
        WHERE b.user_id=%s ORDER BY b.created_at DESC LIMIT 10""", (user['id'],))
    bookings = cur.fetchall()
    cur.execute("SELECT * FROM services WHERE status='active'"); services = cur.fetchall(); db.close()
    return render_template('dashboard.html', user=user, total_bookings=total, active_bookings=active,
                           completed_bookings=completed, bookings=bookings, services=services)

# ============================================
# ADMIN DASHBOARD
# ============================================
@app.route('/admin')
@admin_required
def admin_dashboard():
    user = get_user(); db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) as c FROM users WHERE role='user'"); total_users = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM bookings"); total_bookings = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM technicians"); total_technicians = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(SUM(total_price),0) as c FROM bookings WHERE status='completed'"); total_revenue = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM bookings WHERE status='pending'"); pending = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM contact_messages WHERE is_read=0"); unread = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM reviews"); total_reviews = cur.fetchone()['c']
    cur.execute("""SELECT b.*, s.name AS service_name, s.icon AS service_icon, t.name AS technician_name,
        u.name AS user_name, u.phone AS user_phone FROM bookings b JOIN services s ON b.service_id=s.id
        JOIN users u ON b.user_id=u.id LEFT JOIN technicians t ON b.technician_id=t.id ORDER BY b.created_at DESC LIMIT 50""")
    bookings = cur.fetchall()
    cur.execute("SELECT * FROM services ORDER BY id"); services = cur.fetchall()
    cur.execute("SELECT t.*, s.name AS service_name FROM technicians t JOIN services s ON t.service_id=s.id ORDER BY t.id"); technicians = cur.fetchall()
    cur.execute("SELECT * FROM users ORDER BY created_at DESC"); users = cur.fetchall()
    cur.execute("SELECT * FROM contact_messages ORDER BY created_at DESC"); contacts = cur.fetchall()
    cur.execute("""SELECT r.*, u.name AS user_name, s.name AS service_name, b.booking_date FROM reviews r
        JOIN users u ON r.user_id=u.id JOIN bookings b ON r.booking_id=b.id JOIN services s ON b.service_id=s.id
        ORDER BY r.created_at DESC"""); reviews = cur.fetchall()
    cur.execute("SELECT id, name FROM services WHERE status='active'"); services_list = cur.fetchall(); db.close()
    return render_template('admin.html', user=user, total_users=total_users, total_bookings=total_bookings,
        total_technicians=total_technicians, total_revenue=total_revenue, pending_bookings=pending,
        unread_messages=unread, total_reviews=total_reviews, bookings=bookings, services=services,
        technicians=technicians, users=users, contacts=contacts, reviews=reviews, services_list=services_list)

# ============================================
# TECHNICIAN DASHBOARD
# ============================================
@app.route('/technician')
@technician_required
def technician_dashboard():
    user = get_user(); db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT t.*, s.name AS service_name, s.icon AS service_icon FROM technicians t JOIN services s ON t.service_id=s.id WHERE t.user_id=%s", (user['id'],))
    tp = cur.fetchone()
    if not tp: db.close(); return "Technician profile not found."
    tid = tp['id']
    cur.execute("SELECT COUNT(*) as c FROM bookings WHERE technician_id=%s", (tid,)); total_jobs = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM bookings WHERE technician_id=%s AND status IN ('confirmed','in_progress')", (tid,)); active_jobs = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM bookings WHERE technician_id=%s AND status='completed'", (tid,)); completed_jobs = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(SUM(total_price),0) as c FROM bookings WHERE technician_id=%s AND status='completed'", (tid,)); earnings = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(AVG(r.rating),0) as avg_r FROM reviews r JOIN bookings b ON r.booking_id=b.id WHERE b.technician_id=%s", (tid,)); avg_rating = cur.fetchone()['avg_r']
    cur.execute("""SELECT b.*, s.name AS service_name, s.icon AS service_icon, u.name AS customer_name, u.phone AS customer_phone
        FROM bookings b JOIN services s ON b.service_id=s.id JOIN users u ON b.user_id=u.id WHERE b.technician_id=%s
        ORDER BY CASE b.status WHEN 'in_progress' THEN 1 WHEN 'confirmed' THEN 2 WHEN 'pending' THEN 3
        WHEN 'completed' THEN 4 WHEN 'cancelled' THEN 5 END, b.booking_date DESC""", (tid,)); all_bookings = cur.fetchall()
    cur.execute("""SELECT b.*, s.name AS service_name, s.icon AS service_icon, u.name AS customer_name, u.phone AS customer_phone
        FROM bookings b JOIN services s ON b.service_id=s.id JOIN users u ON b.user_id=u.id
        WHERE b.technician_id=%s AND b.status IN ('pending','confirmed','in_progress') ORDER BY b.booking_date ASC LIMIT 5""", (tid,)); active_list = cur.fetchall()
    cur.execute("""SELECT r.*, u.name AS customer_name FROM reviews r JOIN bookings b ON r.booking_id=b.id
        JOIN users u ON r.user_id=u.id WHERE b.technician_id=%s ORDER BY r.created_at DESC""", (tid,)); my_reviews = cur.fetchall()
    db.close()
    return render_template('technician.html', user=user, tech_profile=tp, total_jobs=total_jobs,
        active_jobs=active_jobs, completed_jobs=completed_jobs, earnings=earnings, avg_rating=avg_rating,
        all_bookings=all_bookings, active_list=active_list, my_reviews=my_reviews)

# ============================================
# API ROUTES
# ============================================
@app.route('/api/book_service', methods=['POST'])
@login_required
def api_book_service():
    db = get_db(); cur = db.cursor(dictionary=True)
    sid = int(request.form.get('service_id', 0))
    cur.execute("SELECT * FROM services WHERE id=%s AND status='active'", (sid,)); svc = cur.fetchone()
    if not svc: db.close(); return jsonify(success=False, message='Invalid service.')
    # Handle file upload
    attachment_name = None
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename:
            if not allowed_file(file.filename):
                db.close()
                return jsonify(success=False, message='File type not allowed. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS))
            attachment_name = save_upload(file)
    cur.execute("INSERT INTO bookings (user_id,service_id,booking_date,time_slot,address,city,phone,total_price,notes,attachment) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (session['user_id'], sid, request.form['booking_date'], request.form['time_slot'], request.form['address'],
         request.form.get('city',''), request.form['phone'], svc['price'], request.form.get('notes',''), attachment_name))
    db.close(); return jsonify(success=True, message='Booking placed successfully!' + (' File uploaded.' if attachment_name else ''))

@app.route('/api/cancel_booking', methods=['POST'])
@login_required
def api_cancel_booking():
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE bookings SET status='cancelled' WHERE id=%s AND user_id=%s AND status IN ('pending','confirmed')",
                (request.form['booking_id'], session['user_id'])); db.close()
    return jsonify(success=True, message='Booking cancelled.')

@app.route('/api/submit_review', methods=['POST'])
@login_required
def api_submit_review():
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO reviews (user_id,booking_id,rating,comment) VALUES (%s,%s,%s,%s)",
                (session['user_id'], request.form['booking_id'], request.form['rating'], request.form.get('comment',''))); db.close()
    return jsonify(success=True, message='Review submitted!')

@app.route('/api/admin/add_service', methods=['POST'])
@admin_required
def api_add_service():
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO services (name,icon,description,price,status) VALUES (%s,%s,%s,%s,%s)",
                (request.form['name'], request.form['icon'], request.form.get('description',''), request.form['price'], request.form.get('status','active'))); db.close()
    return jsonify(success=True, message='Service added!')

@app.route('/api/admin/update_service', methods=['POST'])
@admin_required
def api_update_service():
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE services SET name=%s,icon=%s,description=%s,price=%s,status=%s WHERE id=%s",
                (request.form['name'], request.form['icon'], request.form.get('description',''), request.form['price'], request.form.get('status','active'), request.form['id'])); db.close()
    return jsonify(success=True, message='Service updated!')

@app.route('/api/admin/delete_service', methods=['POST'])
@admin_required
def api_delete_service():
    db = get_db(); cur = db.cursor(); cur.execute("DELETE FROM services WHERE id=%s", (request.form['id'],)); db.close()
    return jsonify(success=True, message='Service deleted!')

@app.route('/api/admin/add_technician', methods=['POST'])
@admin_required
def api_add_technician():
    db = get_db(); cur = db.cursor(dictionary=True)
    email = request.form['email'].strip()
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    if cur.fetchone(): db.close(); return jsonify(success=False, message='Email already registered.')
    hashed = hash_password(request.form['password'])
    if DB_TYPE == 'pg':
        cur.execute("INSERT INTO users (name,email,phone,password,role) VALUES (%s,%s,%s,%s,'technician') RETURNING id",
                    (request.form['name'], email, request.form['phone'], hashed))
        uid = cur.fetchone()['id']
    else:
        cur.execute("INSERT INTO users (name,email,phone,password,role) VALUES (%s,%s,%s,%s,'technician')",
                    (request.form['name'], email, request.form['phone'], hashed))
        uid = cur.lastrowid
    cur.execute("INSERT INTO technicians (user_id,name,phone,email,service_id,experience_years,status) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (uid, request.form['name'], request.form['phone'], email, request.form['service_id'],
                 request.form.get('experience_years',0), request.form.get('status','available'))); db.close()
    return jsonify(success=True, message=f'Technician added! Login: {email}')

@app.route('/api/admin/update_technician', methods=['POST'])
@admin_required
def api_update_technician():
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE technicians SET name=%s,phone=%s,email=%s,service_id=%s,experience_years=%s,status=%s WHERE id=%s",
                (request.form['name'], request.form['phone'], request.form.get('email',''), request.form['service_id'],
                 request.form.get('experience_years',0), request.form.get('status','available'), request.form['id'])); db.close()
    return jsonify(success=True, message='Technician updated!')

@app.route('/api/admin/delete_technician', methods=['POST'])
@admin_required
def api_delete_technician():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT user_id FROM technicians WHERE id=%s", (request.form['id'],)); tech = cur.fetchone()
    if tech:
        cur.execute("DELETE FROM technicians WHERE id=%s", (request.form['id'],))
        cur.execute("DELETE FROM users WHERE id=%s", (tech['user_id'],))
    db.close(); return jsonify(success=True, message='Technician deleted!')

@app.route('/api/admin/update_booking', methods=['POST'])
@admin_required
def api_update_booking():
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE bookings SET status=%s WHERE id=%s", (request.form['status'], request.form['booking_id'])); db.close()
    return jsonify(success=True, message='Booking updated!')

@app.route('/api/admin/mark_contact_read', methods=['POST'])
@admin_required
def api_mark_contact_read():
    db = get_db(); cur = db.cursor(); cur.execute("UPDATE contact_messages SET is_read=1 WHERE id=%s", (request.form['id'],)); db.close()
    return jsonify(success=True, message='Marked as read.')

@app.route('/api/technician/update_job', methods=['POST'])
@technician_required
def api_update_job():
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE bookings SET status=%s WHERE id=%s", (request.form['status'], request.form['booking_id'])); db.close()
    return jsonify(success=True, message='Job updated!')

@app.route('/api/update_profile', methods=['POST'])
@login_required
def api_update_profile():
    db = get_db(); cur = db.cursor()
    cur.execute("UPDATE users SET name=%s, phone=%s WHERE id=%s", (request.form['name'], request.form['phone'], session['user_id']))
    session['user_name'] = request.form['name']; db.close()
    return jsonify(success=True, message='Profile updated!')

@app.route('/api/change_password', methods=['POST'])
@login_required
def api_change_password():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT password FROM users WHERE id=%s", (session['user_id'],)); u = cur.fetchone()
    if not check_password(request.form['current_password'], u['password']): db.close(); return jsonify(success=False, message='Wrong current password.')
    cur.execute("UPDATE users SET password=%s WHERE id=%s", (hash_password(request.form['new_password']), session['user_id'])); db.close()
    return jsonify(success=True, message='Password changed!')

@app.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['POST'])
def reset_password():
    email = request.form.get('email', '').strip()
    if not email:
        flash('Please enter your email.', 'error')
        return redirect(url_for('forgot_password'))
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    if not user:
        flash('No account found with that email.', 'error')
        db.close(); return redirect(url_for('forgot_password'))
    # Generate random 8-char password
    new_pw = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    hashed = hash_password(new_pw)
    cur.execute("UPDATE users SET password=%s WHERE id=%s", (hashed, user['id']))
    db.close()
    flash(f'Your new password is: {new_pw}  — Please login and change it immediately.', 'info')
    return redirect(url_for('forgot_password'))

@app.route('/book')
@login_required
def book_service():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM services WHERE status='active'"); services = cur.fetchall(); db.close()
    return render_template('book.html', services=services, selected_service_id=request.args.get('service_id',''), user=get_user())

@app.route('/profile')
@login_required
def profile():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, name, email, phone, role FROM users WHERE id=%s", (session['user_id'],))
    user_data = cur.fetchone(); db.close()
    return render_template('profile.html', user=get_user(), user_data=user_data)

# ============================================
# RUN
# ============================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
