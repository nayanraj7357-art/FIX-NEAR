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
import hmac
import secrets
import string
import random
import os
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime, timedelta

# Load .env file (local development only — on Render, env vars are set in Dashboard)
load_dotenv()

# Local MySQL Database Configuration
import mysql.connector

# ============================================
# APP CONFIG
# ============================================
app = Flask(__name__, template_folder='templates', static_folder='static')
SECRET_KEY = os.environ.get('SECRET_KEY')
IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production' or bool(os.environ.get('RENDER'))
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError('SECRET_KEY environment variable is required in production.')
    SECRET_KEY = 'fixnear_local_dev_key_change_in_production'
app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION or os.environ.get('SESSION_COOKIE_SECURE') == '1'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

@app.after_request
def add_security_headers(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'geolocation=(self), camera=(), microphone=()')
    return response

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
# Localhost → MySQL
# ============================================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'fixnear',
    'charset': 'utf8mb4',
    'autocommit': True
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def ensure_runtime_schema():
    try:
        db = get_db(); cur = db.cursor()
        cur.execute("SHOW COLUMNS FROM users LIKE 'last_login_at'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE users ADD COLUMN last_login_at DATETIME DEFAULT NULL")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(180) NOT NULL,
                message TEXT NOT NULL,
                type VARCHAR(40) DEFAULT 'general',
                related_booking_id INT DEFAULT NULL,
                is_read TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (related_booking_id) REFERENCES bookings(id) ON DELETE SET NULL
            ) ENGINE=InnoDB
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                booking_updates TINYINT(1) DEFAULT 1,
                assignment_updates TINYINT(1) DEFAULT 1,
                system_updates TINYINT(1) DEFAULT 1,
                email_notifications TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB
        """)

        cur.execute("""
            INSERT INTO notification_preferences (user_id)
            SELECT id FROM users
            WHERE id NOT IN (SELECT user_id FROM notification_preferences)
        """)
        db.close()
    except mysql.connector.Error as err:
        print("Schema bootstrap warning:", err)

ensure_runtime_schema()

# ============================================
# HELPERS
# ============================================
BOOKING_TIME_SLOTS = [
    '9:00 AM - 11:00 AM',
    '11:00 AM - 1:00 PM',
    '2:00 PM - 4:00 PM',
    '4:00 PM - 6:00 PM',
    '6:00 PM - 8:00 PM',
]
ACTIVE_BOOKING_STATUSES = ('pending', 'confirmed', 'in_progress')
CSRF_TOKEN_KEY = '_csrf_token'
CSRF_HEADER_NAME = 'X-CSRF-Token'
SAFE_HTTP_METHODS = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}

def is_logged_in(): return 'user_id' in session
def is_admin(): return is_logged_in() and session.get('user_role') == 'admin'
def is_technician(): return is_logged_in() and session.get('user_role') == 'technician'

def get_csrf_token():
    token = session.get(CSRF_TOKEN_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_TOKEN_KEY] = token
    return token

@app.context_processor
def inject_csrf_token():
    return {'csrf_token': get_csrf_token}

def is_valid_csrf_request():
    expected = session.get(CSRF_TOKEN_KEY)
    provided = request.headers.get(CSRF_HEADER_NAME) or request.form.get('csrf_token')
    return bool(expected and provided and hmac.compare_digest(provided, expected))

@app.before_request
def protect_from_csrf():
    if request.method in SAFE_HTTP_METHODS:
        return None
    if request.endpoint == 'static':
        return None
    if is_valid_csrf_request():
        return None

    message = 'Security check failed. Refresh the page and try again.'
    if request.path.startswith('/api/'):
        return jsonify(success=False, message=message), 400

    flash(message, 'error')
    return redirect(request.referrer or url_for('login'))

def ensure_notification_preferences(cur, user_id):
    cur.execute("INSERT IGNORE INTO notification_preferences (user_id) VALUES (%s)", (user_id,))

def get_notification_preferences(cur, user_id):
    ensure_notification_preferences(cur, user_id)
    cur.execute("""SELECT booking_updates, assignment_updates, system_updates, email_notifications
        FROM notification_preferences WHERE user_id=%s""", (user_id,))
    return cur.fetchone()

def should_send_notification(cur, user_id, preference_key):
    prefs = get_notification_preferences(cur, user_id)
    return bool(prefs and prefs.get(preference_key, 1))

def create_notification(cur, user_id, title, message, notification_type='general', related_booking_id=None):
    cur.execute("""INSERT INTO notifications (user_id, title, message, type, related_booking_id)
        VALUES (%s,%s,%s,%s,%s)""", (user_id, title, message, notification_type, related_booking_id))

def create_notification_if_enabled(cur, user_id, preference_key, title, message, notification_type='general', related_booking_id=None):
    if should_send_notification(cur, user_id, preference_key):
        create_notification(cur, user_id, title, message, notification_type, related_booking_id)

def create_role_notifications(cur, role, preference_key, title, message, notification_type='general', related_booking_id=None):
    cur.execute("SELECT id FROM users WHERE role=%s", (role,))
    for row in cur.fetchall():
        create_notification_if_enabled(cur, row['id'], preference_key, title, message, notification_type, related_booking_id)

def get_recent_notifications(cur, user_id, limit=8):
    cur.execute("""SELECT * FROM notifications WHERE user_id=%s
        ORDER BY created_at DESC, id DESC LIMIT %s""", (user_id, limit))
    return cur.fetchall()

def get_unread_notification_count(cur, user_id):
    cur.execute("SELECT COUNT(*) as c FROM notifications WHERE user_id=%s AND is_read=0", (user_id,))
    return cur.fetchone()['c']

def serialize_notification(notification):
    return {
        'id': notification['id'],
        'title': notification['title'],
        'message': notification['message'],
        'type': notification['type'],
        'is_read': notification['is_read'],
        'created_at': notification['created_at'].strftime('%d %b, %I:%M %p') if notification.get('created_at') else '',
    }

def booking_status_label(status):
    return status.replace('_', ' ').title()

def get_user():
    if is_logged_in():
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, name, email, phone, role, city, address, profile_image, created_at, last_login_at FROM users WHERE id=%s", (session['user_id'],))
        user = cur.fetchone()
        db.close()
        if user:
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']
            return user
        session.clear()
    return None

def get_user_booking_details(cur, user_id, booking_id):
    cur.execute("""SELECT b.*, s.name AS service_name, s.icon AS service_icon, s.description AS service_description,
        t.name AS technician_name, t.phone AS technician_phone, t.email AS technician_email, t.status AS technician_status
        FROM bookings b
        JOIN services s ON b.service_id=s.id
        LEFT JOIN technicians t ON b.technician_id=t.id
        WHERE b.id=%s AND b.user_id=%s""", (booking_id, user_id))
    booking = cur.fetchone()
    if not booking:
        return None

    cur.execute("""SELECT rating, comment, created_at
        FROM reviews WHERE booking_id=%s AND user_id=%s
        ORDER BY created_at DESC LIMIT 1""", (booking_id, user_id))
    booking['user_review'] = cur.fetchone()

    cur.execute("""SELECT title, message, type, created_at, is_read
        FROM notifications
        WHERE user_id=%s AND related_booking_id=%s
        ORDER BY created_at DESC, id DESC LIMIT 6""", (user_id, booking_id))
    booking['timeline_notifications'] = cur.fetchall()
    return booking

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

def send_otp_email(to_email, otp, subject="FixNear Verification Code"):
    mail_user = os.environ.get('MAIL_USERNAME')
    mail_pass = os.environ.get('MAIL_PASSWORD')
    if not mail_user or not mail_pass:
        print("WARNING: MAIL_USERNAME or MAIL_PASSWORD not configured. Expected OTP:", otp)
        return False
    msg = MIMEMultipart()
    msg['From'] = mail_user
    msg['To'] = to_email
    msg['Subject'] = subject
    body = f"""
    <html><body>
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 10px;">
        <h2 style="color: #3b82f6;">FixNear Verification</h2>
        <p>Your 6-digit OTP code is:</p>
        <div style="font-size: 24px; font-weight: bold; padding: 10px; background: #f1f5f9; text-align: center; letter-spacing: 2px;">{otp}</div>
        <p style="color: #64748b; font-size: 12px; margin-top: 20px;">If you didn't request this, you can safely ignore this email.</p>
    </div>
    </body></html>
    """
    msg.attach(MIMEText(body, 'html'))
    try:
        # Added timeout to prevent Gunicorn from terminating the worker
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
        server.login(mail_user, mail_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Failed to send email:", e)
        return False

def parse_booking_date(value):
    if isinstance(value, date):
        return value
    return datetime.strptime(value, '%Y-%m-%d').date()

def technician_status_label(status):
    if status == 'available':
        return 'Active'
    if status == 'offline':
        return 'Inactive'
    return 'Busy'

def lock_service_technicians(cur, service_id):
    cur.execute("SELECT id FROM technicians WHERE service_id=%s ORDER BY id FOR UPDATE", (service_id,))
    return [row['id'] for row in cur.fetchall()]

def get_service_technicians(cur, service_id, include_offline=True):
    query = """SELECT t.*, s.name AS service_name FROM technicians t
        JOIN services s ON t.service_id=s.id
        WHERE t.service_id=%s"""
    params = [service_id]
    if not include_offline:
        query += " AND t.status != 'offline'"
    query += """ ORDER BY CASE t.status
            WHEN 'available' THEN 1
            WHEN 'busy' THEN 2
            ELSE 3
        END, t.name"""
    cur.execute(query, tuple(params))
    return cur.fetchall()

def get_technician_conflicts(cur, tech_ids, booking_date, time_slot, exclude_booking_id=None):
    if not tech_ids:
        return {}

    placeholders = ','.join(['%s'] * len(tech_ids))
    query = f"""SELECT b.technician_id, b.id, b.status, u.name AS customer_name
        FROM bookings b
        JOIN users u ON b.user_id=u.id
        WHERE b.technician_id IN ({placeholders})
          AND b.booking_date=%s
          AND b.time_slot=%s
          AND b.status IN (%s,%s,%s)"""
    params = list(tech_ids) + [booking_date, time_slot] + list(ACTIVE_BOOKING_STATUSES)
    if exclude_booking_id is not None:
        query += " AND b.id != %s"
        params.append(exclude_booking_id)
    cur.execute(query, tuple(params))
    return {row['technician_id']: row for row in cur.fetchall()}

def find_next_available_slots(cur, service_id, booking_date, selected_slot=None, limit=3, exclude_booking_id=None):
    suggestions = []
    selected_idx = BOOKING_TIME_SLOTS.index(selected_slot) if selected_slot in BOOKING_TIME_SLOTS else -1

    for day_offset in range(0, 7):
        current_date = booking_date + timedelta(days=day_offset)
        slots = BOOKING_TIME_SLOTS[selected_idx + 1:] if day_offset == 0 and selected_idx >= 0 else BOOKING_TIME_SLOTS

        for slot in slots:
            slot_context = get_slot_assignment_context(
                cur,
                service_id,
                current_date,
                slot,
                exclude_booking_id=exclude_booking_id,
                include_suggestions=False,
            )
            if slot_context['available_count'] > 0:
                suggestions.append({
                    'date': current_date,
                    'time_slot': slot,
                    'available_count': slot_context['available_count'],
                })
                if len(suggestions) >= limit:
                    return suggestions
    return suggestions

def get_slot_assignment_context(cur, service_id, booking_date, time_slot, exclude_booking_id=None, include_suggestions=True):
    booking_date = parse_booking_date(booking_date)
    technicians = get_service_technicians(cur, service_id, include_offline=True)
    conflict_map = get_technician_conflicts(cur, [tech['id'] for tech in technicians], booking_date, time_slot, exclude_booking_id=exclude_booking_id)

    options = []
    available_technicians = []
    for tech in technicians:
        conflict = conflict_map.get(tech['id'])
        is_offline = tech['status'] == 'offline'
        is_assignable = (not is_offline) and conflict is None
        if is_assignable:
            available_technicians.append(tech)
        options.append({
            'id': tech['id'],
            'name': tech['name'],
            'status': tech['status'],
            'status_label': technician_status_label(tech['status']),
            'is_assignable': is_assignable,
            'is_offline': is_offline,
            'has_conflict': conflict is not None,
            'conflict': conflict,
        })

    next_slots = []
    if include_suggestions and not available_technicians:
        next_slots = find_next_available_slots(
            cur,
            service_id,
            booking_date,
            selected_slot=time_slot,
            exclude_booking_id=exclude_booking_id,
        )

    return {
        'booking_date': booking_date,
        'time_slot': time_slot,
        'options': options,
        'available_technicians': available_technicians,
        'available_count': len(available_technicians),
        'next_slots': next_slots,
    }

def format_slot_suggestion(slot):
    return f"{slot['date'].strftime('%d %b')} • {slot['time_slot']}"

def get_demo_payment_breakdown(total_amount):
    total_amount = round(float(total_amount or 0), 2)
    if total_amount <= 0:
        total_amount = 299.00
    taxable_amount = round(total_amount / 1.18, 2)
    service_charge = round(taxable_amount * 0.88, 2)
    visiting_charge = round(taxable_amount - service_charge, 2)
    gst = round(total_amount - taxable_amount, 2)
    return {
        'service_charge': service_charge,
        'visiting_charge': visiting_charge,
        'gst': gst,
        'total_amount': total_amount,
    }

# ============================================
# PUBLIC ROUTES
# ============================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/how-it-works')
def how_it_works_page():
    return render_template('how_it_works.html')

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
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        if not email or not password:
            flash('Email and password are required.', 'error')
            return redirect(url_for('login'))
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, name, email, password, role FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        if user and check_password(password, user['password']):
            cur.execute("UPDATE users SET last_login_at=NOW() WHERE id=%s", (user['id'],))
            db.close()
            session.permanent = True
            session['user_id'] = user['id']; session['user_name'] = user['name']
            session['user_email'] = user['email']; session['user_role'] = user['role']
            if user['role'] == 'admin': return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'technician': return redirect(url_for('technician_dashboard'))
            else: return redirect(url_for('user_dashboard'))
        else:
            db.close()
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip(); email = request.form.get('email','').strip().lower()
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
                db.close()
                otp = ''.join(random.choices(string.digits, k=6))
                session['reg_details'] = {'name': name, 'email': email, 'phone': phone, 'password': hash_password(password)}
                session['reg_otp'] = otp
                success = send_otp_email(email, otp, "Verify your FixNear Registration")
                if success:
                    flash('An OTP has been sent to your email. Please verify to complete registration.', 'info')
                else:
                    flash(f'TESTING MODE (Email Blocked by Render Free Tier): Your OTP is {otp}', 'info')
                return redirect(url_for('verify_otp'))
            db.close()
        for e in errors: flash(e, 'error')
        return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reg_details' not in session:
        return redirect(url_for('register'))
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        if otp == session.get('reg_otp'):
            details = session.pop('reg_details')
            session.pop('reg_otp', None)
            db = get_db(); cur = db.cursor()
            cur.execute("INSERT INTO users (name,email,phone,password) VALUES (%s,%s,%s,%s)", 
                        (details['name'], details['email'], details['phone'], details['password']))
            uid = cur.lastrowid
            cur.execute("INSERT IGNORE INTO notification_preferences (user_id) VALUES (%s)", (uid,))
            db.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP. Please check your email and try again.', 'error')
    return render_template('verify_otp.html')

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
    cur.execute("""SELECT b.*, s.name AS service_name, s.icon AS service_icon, t.name AS technician_name, t.status AS technician_status
        FROM bookings b JOIN services s ON b.service_id=s.id LEFT JOIN technicians t ON b.technician_id=t.id
        WHERE b.user_id=%s
        ORDER BY
            CASE
                WHEN b.booking_date IS NULL THEN 2
                WHEN b.booking_date >= CURDATE() THEN 0
                ELSE 1
            END,
            CASE b.status
                WHEN 'in_progress' THEN 1
                WHEN 'confirmed' THEN 2
                WHEN 'pending' THEN 3
                WHEN 'completed' THEN 4
                WHEN 'cancelled' THEN 5
                ELSE 6
            END,
            b.booking_date ASC,
            FIELD(b.time_slot, %s, %s, %s, %s, %s),
            b.created_at DESC""",
        (user['id'], *BOOKING_TIME_SLOTS))
    bookings = cur.fetchall()

    def booking_sort_key(booking):
        booking_date = booking.get('booking_date') or date.max
        try:
            slot_index = BOOKING_TIME_SLOTS.index(booking.get('time_slot'))
        except ValueError:
            slot_index = len(BOOKING_TIME_SLOTS)
        return (booking_date, slot_index, booking.get('id', 0))

    active_statuses = ('pending', 'confirmed', 'in_progress')
    active_booking_list = [booking for booking in bookings if booking.get('status') in active_statuses]
    active_booking_list.sort(key=booking_sort_key)

    next_booking = None
    today = date.today()
    upcoming_candidates = [
        booking for booking in active_booking_list
        if booking.get('booking_date') and booking['booking_date'] >= today
    ]
    if upcoming_candidates:
        next_booking = upcoming_candidates[0]
    elif active_booking_list:
        next_booking = active_booking_list[0]

    history_bookings = [booking for booking in bookings if booking.get('status') in ('completed', 'cancelled')]
    history_bookings.sort(key=lambda booking: (booking.get('booking_date') or date.min, booking.get('id', 0)), reverse=True)
    total_spent = sum(float(booking.get('total_price') or 0) for booking in bookings if booking.get('status') == 'completed')
    history_bookings = history_bookings[:4]

    service_history_map = {}
    technician_history_map = {}
    for booking in bookings:
        service_key = booking['service_id']
        service_bucket = service_history_map.setdefault(service_key, {
            'service_id': booking['service_id'],
            'service_name': booking['service_name'],
            'service_icon': booking['service_icon'],
            'total_bookings': 0,
            'completed_bookings': 0,
            'cancelled_bookings': 0,
            'completed_spend': 0.0,
            'last_booking_date': None,
        })
        service_bucket['total_bookings'] += 1
        if booking['status'] == 'completed':
            service_bucket['completed_bookings'] += 1
            service_bucket['completed_spend'] += float(booking.get('total_price') or 0)
        elif booking['status'] == 'cancelled':
            service_bucket['cancelled_bookings'] += 1
        booking_date = booking.get('booking_date')
        if booking_date and (service_bucket['last_booking_date'] is None or booking_date > service_bucket['last_booking_date']):
            service_bucket['last_booking_date'] = booking_date

        if booking.get('technician_name'):
            tech_key = booking.get('technician_id')
            tech_bucket = technician_history_map.setdefault(tech_key, {
                'technician_id': tech_key,
                'technician_name': booking['technician_name'],
                'total_visits': 0,
                'completed_visits': 0,
                'active_visits': 0,
                'services_seen': set(),
                'last_visit_date': None,
            })
            tech_bucket['total_visits'] += 1
            if booking['status'] == 'completed':
                tech_bucket['completed_visits'] += 1
            if booking['status'] in active_statuses:
                tech_bucket['active_visits'] += 1
            tech_bucket['services_seen'].add(booking['service_name'])
            if booking_date and (tech_bucket['last_visit_date'] is None or booking_date > tech_bucket['last_visit_date']):
                tech_bucket['last_visit_date'] = booking_date

    service_history_summary = sorted(
        service_history_map.values(),
        key=lambda item: (-item['total_bookings'], -(item['completed_spend']), item['service_name'])
    )[:4]
    technician_history_summary = sorted(
        technician_history_map.values(),
        key=lambda item: (-item['total_visits'], -item['completed_visits'], item['technician_name'])
    )[:4]
    repeat_service_count = sum(1 for item in service_history_map.values() if item['total_bookings'] > 1)
    technician_partner_count = len(technician_history_map)
    repeat_technician_count = sum(1 for item in technician_history_map.values() if item['total_visits'] > 1)
    for technician in technician_history_summary:
        technician['services_seen_count'] = len(technician['services_seen'])

    saved_locations = []
    seen_locations = set()

    def add_saved_location(label, address, city):
        address = (address or '').strip()
        city = (city or '').strip()
        if not address and not city:
            return
        key = (address.lower(), city.lower())
        if key in seen_locations:
            return
        seen_locations.add(key)
        saved_locations.append({'label': label, 'address': address, 'city': city})

    add_saved_location('Primary address', user.get('address'), user.get('city'))
    for booking in bookings:
        add_saved_location('Recent service address', booking.get('address'), booking.get('city'))
        if len(saved_locations) >= 3:
            break

    profile_completion_fields = (
        user.get('name'),
        user.get('email'),
        user.get('phone'),
        user.get('city'),
        user.get('address'),
        user.get('profile_image'),
    )
    profile_completion = round((sum(1 for value in profile_completion_fields if value) / len(profile_completion_fields)) * 100)
    member_since = user['created_at'].strftime('%b %Y') if user.get('created_at') else 'Recently joined'
    last_login_label = user['last_login_at'].strftime('%d %b, %I:%M %p') if user.get('last_login_at') else 'First login pending'

    notifications = get_recent_notifications(cur, user['id'], limit=6)
    unread_notifications = get_unread_notification_count(cur, user['id'])
    notification_preferences = get_notification_preferences(cur, user['id'])
    cur.execute("SELECT * FROM services WHERE status='active'"); services = cur.fetchall(); db.close()
    return render_template('dashboard.html', user=user, total_bookings=total, active_bookings=active,
                           completed_bookings=completed, bookings=bookings, services=services,
                           recent_notifications=notifications, unread_notifications=unread_notifications,
                           notification_preferences=notification_preferences, next_booking=next_booking,
                           active_booking_list=active_booking_list[:3], history_bookings=history_bookings,
                           saved_locations=saved_locations, total_spent=total_spent,
                           service_history_summary=service_history_summary,
                           technician_history_summary=technician_history_summary,
                           technician_partner_count=technician_partner_count,
                           repeat_service_count=repeat_service_count,
                           repeat_technician_count=repeat_technician_count,
                           profile_completion=profile_completion, member_since=member_since,
                           last_login_label=last_login_label)

@app.route('/booking/<int:booking_id>')
@login_required
def booking_details(booking_id):
    if is_admin(): return redirect(url_for('admin_dashboard'))
    if is_technician(): return redirect(url_for('technician_dashboard'))
    user = get_user(); db = get_db(); cur = db.cursor(dictionary=True)
    booking = get_user_booking_details(cur, user['id'], booking_id)
    if not booking:
        db.close()
        flash('Booking not found.', 'error')
        return redirect(url_for('user_dashboard'))

    notifications = get_recent_notifications(cur, user['id'], limit=6)
    unread_notifications = get_unread_notification_count(cur, user['id'])
    notification_preferences = get_notification_preferences(cur, user['id'])
    db.close()
    return render_template(
        'booking_details.html',
        user=user,
        booking=booking,
        recent_notifications=notifications,
        unread_notifications=unread_notifications,
        notification_preferences=notification_preferences,
        google_maps_api_key=os.getenv('GOOGLE_MAPS_API_KEY', '').strip(),
    )

@app.route('/payment/<int:booking_id>')
@login_required
def payment_page(booking_id):
    if is_admin(): return redirect(url_for('admin_dashboard'))
    if is_technician(): return redirect(url_for('technician_dashboard'))
    user = get_user(); db = get_db(); cur = db.cursor(dictionary=True)
    booking = get_user_booking_details(cur, user['id'], booking_id)
    if not booking:
        db.close()
        flash('Booking not found.', 'error')
        return redirect(url_for('user_dashboard'))

    notifications = get_recent_notifications(cur, user['id'], limit=6)
    unread_notifications = get_unread_notification_count(cur, user['id'])
    breakdown = get_demo_payment_breakdown(booking.get('total_price'))
    db.close()
    return render_template(
        'payment.html',
        user=user,
        booking=booking,
        payment_breakdown=breakdown,
        payment_success=request.args.get('status') == 'success',
        selected_method=request.args.get('method', 'upi'),
        recent_notifications=notifications,
        unread_notifications=unread_notifications,
    )

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
    cur.execute("""SELECT b.user_id, u.name AS user_name, b.technician_id, b.service_id, b.status, b.total_price, b.booking_date,
        s.name AS service_name, COALESCE(t.name, 'Unassigned') AS technician_name
        FROM bookings b
        JOIN users u ON b.user_id=u.id
        JOIN services s ON b.service_id=s.id
        LEFT JOIN technicians t ON b.technician_id=t.id
        ORDER BY b.created_at DESC""")
    history_rows = cur.fetchall()
    cur.execute("SELECT * FROM services ORDER BY id"); services = cur.fetchall()
    cur.execute("""SELECT t.*, s.name AS service_name FROM technicians t
        JOIN services s ON t.service_id=s.id
        ORDER BY t.service_id,
                 CASE t.status
                     WHEN 'available' THEN 1
                     WHEN 'busy' THEN 2
                     ELSE 3
                 END,
                 t.name"""); technicians = cur.fetchall()
    technicians_by_service = {}
    for tech in technicians:
        technicians_by_service.setdefault(tech['service_id'], []).append(tech)

    queued_bookings = 0
    ready_queue_count = 0
    full_queue_count = 0
    for booking in bookings:
        service_technicians = technicians_by_service.get(booking['service_id'], [])
        conflict_map = get_technician_conflicts(
            cur,
            [tech['id'] for tech in service_technicians],
            booking['booking_date'],
            booking['time_slot'],
            exclude_booking_id=booking['id'],
        )

        assignment_options = []
        selected_technician = None
        free_count = 0
        for tech in service_technicians:
            tech_conflict = conflict_map.get(tech['id'])
            is_current = booking['technician_id'] == tech['id']
            is_disabled = (tech['status'] == 'offline') or (tech_conflict is not None and not is_current)
            if not is_disabled:
                free_count += 1
            option = {
                'id': tech['id'],
                'name': tech['name'],
                'status': tech['status'],
                'status_label': technician_status_label(tech['status']),
                'disabled': is_disabled,
                'reason': 'Inactive technician' if tech['status'] == 'offline' else 'Already booked in this slot' if tech_conflict and not is_current else '',
                'conflict': tech_conflict,
            }
            assignment_options.append(option)
            if is_current:
                selected_technician = option

        booking['assignment_options'] = assignment_options
        booking['selected_technician'] = selected_technician
        booking['slot_available_count'] = free_count
        booking['is_queue_booking'] = booking['technician_id'] is None and booking['status'] == 'pending'
        booking['queue_state'] = 'ready' if free_count > 0 else 'full'
        booking['next_slot_suggestions'] = []
        if booking['is_queue_booking']:
            queued_bookings += 1
            if free_count > 0:
                ready_queue_count += 1
            else:
                full_queue_count += 1
                booking['next_slot_suggestions'] = find_next_available_slots(
                    cur,
                    booking['service_id'],
                    booking['booking_date'],
                    selected_slot=booking['time_slot'],
                    exclude_booking_id=booking['id'],
                )
    user_history_map = {}
    technician_history_map = {}
    for row in history_rows:
        user_bucket = user_history_map.setdefault(row['user_id'], {
            'total_bookings': 0,
            'completed_bookings': 0,
            'cancelled_bookings': 0,
            'total_spend': 0.0,
            'last_booking_date': None,
            'services': {},
            'technicians': {},
        })
        user_bucket['total_bookings'] += 1
        if row['status'] == 'completed':
            user_bucket['completed_bookings'] += 1
            user_bucket['total_spend'] += float(row.get('total_price') or 0)
        elif row['status'] == 'cancelled':
            user_bucket['cancelled_bookings'] += 1
        if row.get('booking_date') and (user_bucket['last_booking_date'] is None or row['booking_date'] > user_bucket['last_booking_date']):
            user_bucket['last_booking_date'] = row['booking_date']
        user_bucket['services'][row['service_name']] = user_bucket['services'].get(row['service_name'], 0) + 1
        if row.get('technician_id'):
            user_bucket['technicians'][row['technician_name']] = user_bucket['technicians'].get(row['technician_name'], 0) + 1

        if row.get('technician_id'):
            tech_bucket = technician_history_map.setdefault(row['technician_id'], {
                'total_jobs': 0,
                'completed_jobs': 0,
                'active_jobs': 0,
                'earnings': 0.0,
                'last_job_date': None,
                'customers': {},
                'customer_names': {},
            })
            tech_bucket['total_jobs'] += 1
            if row['status'] == 'completed':
                tech_bucket['completed_jobs'] += 1
                tech_bucket['earnings'] += float(row.get('total_price') or 0)
            if row['status'] in ACTIVE_BOOKING_STATUSES:
                tech_bucket['active_jobs'] += 1
            if row.get('booking_date') and (tech_bucket['last_job_date'] is None or row['booking_date'] > tech_bucket['last_job_date']):
                tech_bucket['last_job_date'] = row['booking_date']
            tech_bucket['customers'][row['user_id']] = tech_bucket['customers'].get(row['user_id'], 0) + 1
            tech_bucket['customer_names'][row['user_id']] = row['user_name']

    cur.execute("SELECT * FROM users WHERE role='user' ORDER BY created_at DESC"); users = cur.fetchall()
    for row in users:
        history = user_history_map.get(row['id'], {})
        services_map = history.get('services', {})
        technicians_map = history.get('technicians', {})
        row['history_total_bookings'] = history.get('total_bookings', 0)
        row['history_completed_bookings'] = history.get('completed_bookings', 0)
        row['history_cancelled_bookings'] = history.get('cancelled_bookings', 0)
        row['history_total_spend'] = history.get('total_spend', 0.0)
        row['history_last_booking_date'] = history.get('last_booking_date')
        row['history_top_service'] = max(services_map, key=services_map.get) if services_map else 'No bookings yet'
        row['history_top_service_count'] = services_map.get(row['history_top_service'], 0) if services_map else 0
        row['history_top_technician'] = max(technicians_map, key=technicians_map.get) if technicians_map else 'No technician linked yet'
        row['history_top_technician_count'] = technicians_map.get(row['history_top_technician'], 0) if technicians_map else 0
        row['history_repeat_customer'] = row['history_total_bookings'] > 1

    for tech in technicians:
        history = technician_history_map.get(tech['id'], {})
        customer_counts = history.get('customers', {})
        tech['history_total_jobs'] = history.get('total_jobs', 0)
        tech['history_completed_jobs'] = history.get('completed_jobs', 0)
        tech['history_active_jobs'] = history.get('active_jobs', 0)
        tech['history_earnings'] = history.get('earnings', 0.0)
        tech['history_last_job_date'] = history.get('last_job_date')
        tech['history_unique_customers'] = len(customer_counts)
        tech['history_top_customer_visits'] = max(customer_counts.values()) if customer_counts else 0
        if customer_counts:
            top_customer_id = max(customer_counts, key=customer_counts.get)
            tech['history_top_customer_name'] = history['customer_names'].get(top_customer_id, 'Customer record')
        else:
            tech['history_top_customer_name'] = 'No customer history yet'
    cur.execute("SELECT * FROM contact_messages ORDER BY created_at DESC"); contacts = cur.fetchall()
    cur.execute("""SELECT r.*, u.name AS user_name, s.name AS service_name, b.booking_date FROM reviews r
        JOIN users u ON r.user_id=u.id JOIN bookings b ON r.booking_id=b.id JOIN services s ON b.service_id=s.id
        ORDER BY r.created_at DESC"""); reviews = cur.fetchall()
    notification_preferences = get_notification_preferences(cur, user['id'])
    recent_notifications = get_recent_notifications(cur, user['id'], limit=8)
    unread_notifications = get_unread_notification_count(cur, user['id'])
    cur.execute("SELECT id, name FROM services WHERE status='active'"); services_list = cur.fetchall()
    db.close()
    return render_template('admin.html', user=user, total_users=total_users, total_bookings=total_bookings,
        total_technicians=total_technicians, total_revenue=total_revenue, pending_bookings=pending,
        unread_messages=unread, total_reviews=total_reviews, bookings=bookings, services=services,
        technicians=technicians, users=users, contacts=contacts, reviews=reviews, services_list=services_list,
        queued_bookings=queued_bookings, ready_queue_count=ready_queue_count, full_queue_count=full_queue_count,
        recent_notifications=recent_notifications, unread_notifications=unread_notifications,
        notification_preferences=notification_preferences)

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
    cur.execute("SELECT COALESCE(SUM(total_price),0) as c FROM bookings WHERE technician_id=%s AND status='completed' AND booking_date=CURDATE()", (tid,)); today_earnings = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(SUM(total_price),0) as c FROM bookings WHERE technician_id=%s AND status='completed' AND YEAR(booking_date)=YEAR(CURDATE()) AND MONTH(booking_date)=MONTH(CURDATE())", (tid,)); month_earnings = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM bookings WHERE technician_id=%s AND status='pending'", (tid,)); pending_jobs = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM bookings WHERE technician_id=%s AND status IN ('pending','confirmed')", (tid,)); request_jobs = cur.fetchone()['c']
    cur.execute("""SELECT b.*, s.name AS service_name, s.icon AS service_icon, u.name AS customer_name, u.phone AS customer_phone
        FROM bookings b JOIN services s ON b.service_id=s.id JOIN users u ON b.user_id=u.id WHERE b.technician_id=%s
        ORDER BY CASE b.status WHEN 'in_progress' THEN 1 WHEN 'confirmed' THEN 2 WHEN 'pending' THEN 3
        WHEN 'completed' THEN 4 WHEN 'cancelled' THEN 5 END, b.booking_date DESC""", (tid,)); all_bookings = cur.fetchall()
    cur.execute("""SELECT b.*, s.name AS service_name, s.icon AS service_icon, u.name AS customer_name, u.phone AS customer_phone
        FROM bookings b JOIN services s ON b.service_id=s.id JOIN users u ON b.user_id=u.id
        WHERE b.technician_id=%s AND b.status IN ('pending','confirmed','in_progress') ORDER BY b.booking_date ASC LIMIT 5""", (tid,)); active_list = cur.fetchall()
    cur.execute("""SELECT b.*, s.name AS service_name, s.icon AS service_icon, u.name AS customer_name, u.phone AS customer_phone
        FROM bookings b JOIN services s ON b.service_id=s.id JOIN users u ON b.user_id=u.id
        WHERE b.technician_id=%s AND b.status='completed' ORDER BY b.updated_at DESC LIMIT 6""", (tid,)); completed_list = cur.fetchall()
    cur.execute("""SELECT r.*, u.name AS customer_name FROM reviews r JOIN bookings b ON r.booking_id=b.id
        JOIN users u ON r.user_id=u.id WHERE b.technician_id=%s ORDER BY r.created_at DESC""", (tid,)); my_reviews = cur.fetchall()
    pending_bookings = [b for b in all_bookings if b['status'] == 'pending']
    confirmed_bookings = [b for b in all_bookings if b['status'] == 'confirmed']
    in_progress_bookings = [b for b in all_bookings if b['status'] == 'in_progress']
    cancelled_bookings = [b for b in all_bookings if b['status'] == 'cancelled']
    request_bookings = pending_bookings + confirmed_bookings
    is_active_toggle = tp['status'] != 'offline'
    if active_jobs > 0:
        display_status = 'working'
    elif is_active_toggle:
        display_status = 'active'
    else:
        display_status = 'inactive'
    today_jobs = [
        b for b in all_bookings
        if b.get('booking_date') and b['booking_date'] == date.today() and b['status'] in ('pending', 'confirmed', 'in_progress')
    ]
    customer_history_map = {}
    service_history_map = {}
    for booking in all_bookings:
        customer_key = booking['user_id']
        customer_bucket = customer_history_map.setdefault(customer_key, {
            'customer_name': booking['customer_name'],
            'customer_phone': booking['customer_phone'],
            'total_jobs': 0,
            'completed_jobs': 0,
            'active_jobs': 0,
            'last_service_date': None,
            'total_billed': 0.0,
        })
        customer_bucket['total_jobs'] += 1
        if booking['status'] == 'completed':
            customer_bucket['completed_jobs'] += 1
            customer_bucket['total_billed'] += float(booking.get('total_price') or 0)
        if booking['status'] in ('pending', 'confirmed', 'in_progress'):
            customer_bucket['active_jobs'] += 1
        if booking.get('booking_date') and (customer_bucket['last_service_date'] is None or booking['booking_date'] > customer_bucket['last_service_date']):
            customer_bucket['last_service_date'] = booking['booking_date']

        service_bucket = service_history_map.setdefault(booking['service_name'], {
            'service_name': booking['service_name'],
            'total_jobs': 0,
            'completed_jobs': 0,
        })
        service_bucket['total_jobs'] += 1
        if booking['status'] == 'completed':
            service_bucket['completed_jobs'] += 1

    customer_history = sorted(
        customer_history_map.values(),
        key=lambda item: (-item['total_jobs'], -item['completed_jobs'], item['customer_name'])
    )[:6]
    service_history = sorted(
        service_history_map.values(),
        key=lambda item: (-item['total_jobs'], -item['completed_jobs'], item['service_name'])
    )[:4]
    recent_notifications = get_recent_notifications(cur, user['id'], limit=6)
    unread_notifications = get_unread_notification_count(cur, user['id'])
    notification_preferences = get_notification_preferences(cur, user['id'])
    db.close()
    return render_template('technician_hub.html', user=user, tech_profile=tp, total_jobs=total_jobs,
        active_jobs=active_jobs, completed_jobs=completed_jobs, earnings=earnings, avg_rating=avg_rating,
        all_bookings=all_bookings, active_list=active_list, my_reviews=my_reviews, pending_jobs=pending_jobs,
        today_earnings=today_earnings, month_earnings=month_earnings, completed_list=completed_list,
        pending_bookings=pending_bookings, confirmed_bookings=confirmed_bookings,
        in_progress_bookings=in_progress_bookings, cancelled_bookings=cancelled_bookings,
        today_jobs=today_jobs, request_bookings=request_bookings, request_jobs=request_jobs,
        customer_history=customer_history, service_history=service_history,
        display_status=display_status, is_active_toggle=is_active_toggle,
        recent_notifications=recent_notifications, unread_notifications=unread_notifications,
        notification_preferences=notification_preferences)

# ============================================
# API ROUTES
# ============================================
@app.route('/api/slot_availability', methods=['POST'])
@login_required
def api_slot_availability():
    service_id = int(request.form.get('service_id', 0))
    booking_date_raw = request.form.get('booking_date', '').strip()
    time_slot = request.form.get('time_slot', '').strip()
    if not service_id or not booking_date_raw or time_slot not in BOOKING_TIME_SLOTS:
        return jsonify(success=False, message='Complete the service, date, and time slot to check availability.')

    try:
        booking_date = parse_booking_date(booking_date_raw)
    except ValueError:
        return jsonify(success=False, message='Invalid booking date selected.')
    if booking_date < date.today():
        return jsonify(success=False, message='Please choose today or a future date.')

    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT id FROM services WHERE id=%s AND status='active'", (service_id,))
    service = cur.fetchone()
    if not service:
        db.close()
        return jsonify(success=False, message='Invalid service selected.')

    exclude_booking_id = request.form.get('exclude_booking_id', '').strip()
    if exclude_booking_id:
        cur.execute("""SELECT id FROM bookings
            WHERE id=%s AND user_id=%s AND status IN ('pending','confirmed')""",
            (exclude_booking_id, session['user_id']))
        if not cur.fetchone():
            db.close()
            return jsonify(success=False, message='Booking not found for slot comparison.')
        exclude_booking_id = int(exclude_booking_id)
    else:
        exclude_booking_id = None

    slot_context = get_slot_assignment_context(cur, service_id, booking_date, time_slot, exclude_booking_id=exclude_booking_id)
    db.close()

    if slot_context['available_count'] > 0:
        return jsonify(
            success=True,
            state='available',
            available_count=slot_context['available_count'],
            message=f"{slot_context['available_count']} technician(s) can currently take this slot.",
            suggestions=[format_slot_suggestion(slot) for slot in slot_context['next_slots']],
        )

    return jsonify(
        success=True,
        state='queue',
        available_count=0,
        message="This slot is currently full, but you can still book it. We'll keep your request in priority queue and confirm as soon as capacity opens.",
        suggestions=[format_slot_suggestion(slot) for slot in slot_context['next_slots']],
    )

@app.route('/api/book_service', methods=['POST'])
@login_required
def api_book_service():
    sid = int(request.form.get('service_id', 0))
    booking_date_raw = request.form.get('booking_date', '').strip()
    time_slot = request.form.get('time_slot', '').strip()
    if not sid:
        return jsonify(success=False, message='Please choose a valid service.')
    if not booking_date_raw:
        return jsonify(success=False, message='Please choose your preferred booking date.')
    if time_slot not in BOOKING_TIME_SLOTS:
        return jsonify(success=False, message='Please choose a valid time slot.')
    try:
        booking_date = parse_booking_date(booking_date_raw)
    except ValueError:
        return jsonify(success=False, message='Invalid booking date selected.')
    if booking_date < date.today():
        return jsonify(success=False, message='Please choose today or a future date.')

    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM services WHERE id=%s AND status='active'", (sid,)); svc = cur.fetchone()
    if not svc:
        db.close()
        return jsonify(success=False, message='Invalid service.')
    # Handle file upload
    attachment_name = None
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename:
            if not allowed_file(file.filename):
                db.close()
                return jsonify(success=False, message='File type not allowed. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS))
            attachment_name = save_upload(file)
    try:
        db.start_transaction()
        lock_service_technicians(cur, sid)
        slot_context = get_slot_assignment_context(cur, sid, booking_date, time_slot, include_suggestions=True)
        assigned_technician = slot_context['available_technicians'][0] if slot_context['available_technicians'] else None
        booking_id = None
        try:
            cur.execute("""INSERT INTO bookings
                (user_id,service_id,technician_id,booking_date,time_slot,address,city,phone,total_price,notes,attachment)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (session['user_id'], sid, assigned_technician['id'] if assigned_technician else None, booking_date_raw, time_slot,
                 request.form['address'], request.form.get('city',''), request.form['phone'], svc['price'],
                  request.form.get('notes',''), attachment_name))
            booking_id = cur.lastrowid
        except Exception as insert_e:
            if 'attachment' in str(insert_e).lower():
                cur.execute("""INSERT INTO bookings
                    (user_id,service_id,technician_id,booking_date,time_slot,address,city,phone,total_price,notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (session['user_id'], sid, assigned_technician['id'] if assigned_technician else None, booking_date_raw, time_slot,
                     request.form['address'], request.form.get('city',''), request.form['phone'], svc['price'], request.form.get('notes','')))
                booking_id = cur.lastrowid
            else:
                raise insert_e

        if assigned_technician:
            create_notification_if_enabled(
                cur, session['user_id'], 'booking_updates',
                'Booking confirmed',
                f"Your {svc['name']} booking for {booking_date.strftime('%d %b')} at {time_slot} has been placed and assigned to {assigned_technician['name']}.",
                'booking_assigned', booking_id
            )
            create_notification_if_enabled(
                cur, assigned_technician['user_id'], 'assignment_updates',
                'New job assigned',
                f"You have been assigned a {svc['name']} booking on {booking_date.strftime('%d %b')} at {time_slot}.",
                'job_assigned', booking_id
            )
            create_role_notifications(
                cur, 'admin', 'booking_updates',
                'New booking assigned',
                f"{session['user_name']} booked {svc['name']} for {booking_date.strftime('%d %b')} at {time_slot}. Assigned to {assigned_technician['name']}.",
                'booking_created', booking_id
            )
        else:
            create_notification_if_enabled(
                cur, session['user_id'], 'booking_updates',
                'Booking queued',
                f"Your {svc['name']} booking for {booking_date.strftime('%d %b')} at {time_slot} is in the assignment queue because the slot is currently full.",
                'booking_queued', booking_id
            )
            create_role_notifications(
                cur, 'admin', 'booking_updates',
                'Queued booking needs assignment',
                f"{session['user_name']} requested {svc['name']} on {booking_date.strftime('%d %b')} at {time_slot}, but no technician was free for that slot.",
                'booking_queue', booking_id
            )

        db.commit()
        db.close()

        if assigned_technician:
            return jsonify(
                success=True,
                assigned=True,
                queued=False,
                booking_id=booking_id,
                payment_url=url_for('payment_page', booking_id=booking_id),
                message=f"Booking placed successfully. {assigned_technician['name']} is available for your selected slot." + (' File uploaded.' if attachment_name else '')
            )

        suggestions = [format_slot_suggestion(slot) for slot in slot_context['next_slots']]
        suggestion_text = f" Next available options: {', '.join(suggestions[:3])}." if suggestions else ''
        return jsonify(
            success=True,
            assigned=False,
            queued=True,
            booking_id=booking_id,
            payment_url=url_for('payment_page', booking_id=booking_id),
            message="Booking received for your preferred slot. All technicians are currently occupied for that exact time, so we have placed your request in the assignment queue." + suggestion_text + (' File uploaded.' if attachment_name else '')
        )
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify(success=False, message=f'Booking failed: {str(e)}')

@app.route('/api/cancel_booking', methods=['POST'])
@login_required
def api_cancel_booking():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""SELECT b.id, b.service_id, b.technician_id, b.booking_date, b.time_slot, s.name AS service_name
        FROM bookings b JOIN services s ON b.service_id=s.id
        WHERE b.id=%s AND b.user_id=%s AND b.status IN ('pending','confirmed')""",
        (request.form['booking_id'], session['user_id']))
    booking = cur.fetchone()
    if not booking:
        db.close()
        return jsonify(success=False, message='This booking can no longer be cancelled.')
    cur.execute("UPDATE bookings SET status='cancelled' WHERE id=%s", (booking['id'],))
    create_notification_if_enabled(
        cur, session['user_id'], 'booking_updates',
        'Booking cancelled',
        f"Your {booking['service_name']} booking for {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']} has been cancelled.",
        'booking_cancelled', booking['id']
    )
    create_role_notifications(
        cur, 'admin', 'booking_updates',
        'Customer cancelled a booking',
        f"{session['user_name']} cancelled their {booking['service_name']} booking scheduled for {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']}.",
        'booking_cancelled', booking['id']
    )
    if booking['technician_id']:
        cur.execute("SELECT user_id, name FROM technicians WHERE id=%s", (booking['technician_id'],))
        technician = cur.fetchone()
        if technician:
            create_notification_if_enabled(
                cur, technician['user_id'], 'assignment_updates',
                'Assigned job cancelled',
                f"{booking['service_name']} booking on {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']} has been cancelled by the customer.",
                'job_cancelled', booking['id']
            )
    db.close()
    return jsonify(success=True, message='Booking cancelled.')

@app.route('/api/reschedule_booking', methods=['POST'])
@login_required
def api_reschedule_booking():
    booking_id = request.form.get('booking_id', '').strip()
    booking_date_raw = request.form.get('booking_date', '').strip()
    time_slot = request.form.get('time_slot', '').strip()
    if not booking_id:
        return jsonify(success=False, message='Booking id is required.')
    if not booking_date_raw:
        return jsonify(success=False, message='Please choose your new booking date.')
    if time_slot not in BOOKING_TIME_SLOTS:
        return jsonify(success=False, message='Please choose a valid time slot.')

    try:
        booking_date = parse_booking_date(booking_date_raw)
    except ValueError:
        return jsonify(success=False, message='Invalid booking date selected.')
    if booking_date < date.today():
        return jsonify(success=False, message='Please choose today or a future date.')

    db = get_db(); cur = db.cursor(dictionary=True)
    try:
        db.start_transaction()
        cur.execute("""SELECT b.*, s.name AS service_name
            FROM bookings b
            JOIN services s ON b.service_id=s.id
            WHERE b.id=%s AND b.user_id=%s AND b.status IN ('pending','confirmed')
            FOR UPDATE""", (booking_id, session['user_id']))
        booking = cur.fetchone()
        if not booking:
            db.rollback(); db.close()
            return jsonify(success=False, message='This booking cannot be rescheduled anymore.')

        if booking['booking_date'] == booking_date and booking['time_slot'] == time_slot:
            db.rollback(); db.close()
            return jsonify(success=False, message='Please choose a different date or time slot to reschedule.')

        old_technician = None
        if booking['technician_id']:
            cur.execute("SELECT id, user_id, name FROM technicians WHERE id=%s", (booking['technician_id'],))
            old_technician = cur.fetchone()

        lock_service_technicians(cur, booking['service_id'])
        slot_context = get_slot_assignment_context(
            cur, booking['service_id'], booking_date, time_slot,
            exclude_booking_id=booking['id'], include_suggestions=True
        )

        assigned_technician = None
        if slot_context['available_technicians']:
            if booking['technician_id']:
                assigned_technician = next(
                    (tech for tech in slot_context['available_technicians'] if tech['id'] == booking['technician_id']),
                    None
                )
            if not assigned_technician:
                assigned_technician = slot_context['available_technicians'][0]

        new_status = booking['status']
        if booking['status'] == 'confirmed' and not assigned_technician:
            new_status = 'pending'

        cur.execute("""UPDATE bookings
            SET booking_date=%s, time_slot=%s, technician_id=%s, status=%s
            WHERE id=%s""",
            (booking_date_raw, time_slot, assigned_technician['id'] if assigned_technician else None, new_status, booking['id']))

        user_message = (
            f"Your {booking['service_name']} booking was moved to {booking_date.strftime('%d %b')} at {time_slot}."
        )
        if assigned_technician:
            user_message += f" Technician assigned: {assigned_technician['name']}."
        else:
            user_message += " The booking is now waiting in the assignment queue for that slot."

        create_notification_if_enabled(
            cur, session['user_id'], 'booking_updates',
            'Booking rescheduled',
            user_message,
            'booking_rescheduled', booking['id']
        )
        create_role_notifications(
            cur, 'admin', 'booking_updates',
            'Customer rescheduled a booking',
            f"{session['user_name']} moved their {booking['service_name']} booking to {booking_date.strftime('%d %b')} at {time_slot}.",
            'booking_rescheduled', booking['id']
        )

        if old_technician and (not assigned_technician or assigned_technician['id'] != old_technician['id']):
            create_notification_if_enabled(
                cur, old_technician['user_id'], 'assignment_updates',
                'Job schedule changed',
                f"{booking['service_name']} booking originally linked to you has been rescheduled by the customer to {booking_date.strftime('%d %b')} at {time_slot}.",
                'job_rescheduled', booking['id']
            )

        if assigned_technician:
            target_user_id = assigned_technician['user_id']
            title = 'Job rescheduled' if old_technician and assigned_technician['id'] == old_technician['id'] else 'New slot assigned'
            message = (
                f"{booking['service_name']} booking is scheduled for {booking_date.strftime('%d %b')} at {time_slot}."
            )
            create_notification_if_enabled(
                cur, target_user_id, 'assignment_updates',
                title,
                message,
                'job_rescheduled', booking['id']
            )

        db.commit()
        db.close()

        suggestions = [format_slot_suggestion(slot) for slot in slot_context['next_slots']]
        if assigned_technician:
            return jsonify(
                success=True,
                queued=False,
                message=f"Booking rescheduled to {booking_date.strftime('%d %b')} at {time_slot}. {assigned_technician['name']} is currently available for that slot."
            )
        suggestion_text = f" Next available options: {', '.join(suggestions[:3])}." if suggestions else ''
        return jsonify(
            success=True,
            queued=True,
            message=f"Booking rescheduled to {booking_date.strftime('%d %b')} at {time_slot}. No technician is free there right now, so it has been moved into the assignment queue.{suggestion_text}"
        )
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify(success=False, message=f'Reschedule failed: {str(e)}')

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

@app.route('/api/admin/toggle_service_status', methods=['POST'])
@admin_required
def api_toggle_service_status():
    service_id = request.form.get('id')
    new_status = request.form.get('status', 'inactive')
    if new_status not in ('active', 'inactive'):
        return jsonify(success=False, message='Invalid status.')
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE services SET status=%s WHERE id=%s", (new_status, service_id))
    db.close()
    return jsonify(success=True, message='Service status updated.')

@app.route('/api/admin/add_technician', methods=['POST'])
@admin_required
def api_add_technician():
    db = get_db(); cur = db.cursor(dictionary=True)
    email = request.form['email'].strip().lower()
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    if cur.fetchone(): db.close(); return jsonify(success=False, message='Email already registered.')
    hashed = hash_password(request.form['password'])
    cur.execute("INSERT INTO users (name,email,phone,password,role) VALUES (%s,%s,%s,%s,'technician')",
                (request.form['name'], email, request.form['phone'], hashed))
    uid = cur.lastrowid
    cur.execute("INSERT IGNORE INTO notification_preferences (user_id) VALUES (%s)", (uid,))
    cur.execute("INSERT INTO technicians (user_id,name,phone,email,service_id,experience_years,status) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (uid, request.form['name'], request.form['phone'], email, request.form['service_id'],
                 request.form.get('experience_years',0), 'offline')); db.close()
    return jsonify(success=True, message=f'Technician added! Login: {email}')

@app.route('/api/admin/update_technician', methods=['POST'])
@admin_required
def api_update_technician():
    db = get_db(); cur = db.cursor(dictionary=True)
    tech_id = request.form['id']
    cur.execute("SELECT user_id FROM technicians WHERE id=%s", (tech_id,))
    tech = cur.fetchone()
    if not tech:
        db.close(); return jsonify(success=False, message='Technician not found!')
        
    cur.execute("UPDATE technicians SET name=%s,phone=%s,email=%s,service_id=%s,experience_years=%s WHERE id=%s",
                (request.form['name'], request.form['phone'], request.form.get('email',''), request.form['service_id'],
                 request.form.get('experience_years',0), tech_id))
                 
    cur.execute("UPDATE users SET name=%s, email=%s, phone=%s WHERE id=%s",
                (request.form['name'], request.form.get('email',''), request.form['phone'], tech['user_id']))
                
    new_pw = request.form.get('password', '').strip()
    if new_pw:
        hashed = hash_password(new_pw)
        cur.execute("UPDATE users SET password=%s WHERE id=%s", (hashed, tech['user_id']))
        
    db.close()
    return jsonify(success=True, message='Technician updated successfully!')

@app.route('/api/admin/delete_technician', methods=['POST'])
@admin_required
def api_delete_technician():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT user_id FROM technicians WHERE id=%s", (request.form['id'],)); tech = cur.fetchone()
    if tech:
        cur.execute("DELETE FROM technicians WHERE id=%s", (request.form['id'],))
        cur.execute("DELETE FROM users WHERE id=%s", (tech['user_id'],))
    db.close(); return jsonify(success=True, message='Technician deleted!')

@app.route('/api/admin/toggle_technician_status', methods=['POST'])
@admin_required
def api_toggle_technician_status():
    return jsonify(
        success=False,
        message='Technician availability can only be changed from the technician panel.'
    )

@app.route('/api/admin/update_booking', methods=['POST'])
@admin_required
def api_update_booking():
    new_status = request.form['status']
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""SELECT b.id, b.status, b.user_id, b.technician_id, b.booking_date, b.time_slot,
        s.name AS service_name FROM bookings b
        JOIN services s ON b.service_id=s.id WHERE b.id=%s""", (request.form['booking_id'],))
    booking = cur.fetchone()
    if not booking:
        db.close()
        return jsonify(success=False, message='Booking not found.')
    cur.execute("UPDATE bookings SET status=%s WHERE id=%s", (new_status, request.form['booking_id']))
    if booking['status'] != new_status:
        status_text = booking_status_label(new_status)
        create_notification_if_enabled(
            cur, booking['user_id'], 'booking_updates',
            f'Booking {status_text}',
            f"Your {booking['service_name']} booking for {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']} is now {status_text.lower()}.",
            'booking_status', booking['id']
        )
        if booking['technician_id']:
            cur.execute("SELECT user_id FROM technicians WHERE id=%s", (booking['technician_id'],))
            technician = cur.fetchone()
            if technician:
                create_notification_if_enabled(
                    cur, technician['user_id'], 'assignment_updates',
                    f'Booking {status_text}',
                    f"{booking['service_name']} booking for {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']} is now {status_text.lower()} by admin.",
                    'booking_status', booking['id']
                )
    db.close()
    return jsonify(success=True, message='Booking updated!')

@app.route('/api/admin/assign_technician', methods=['POST'])
@admin_required
def api_assign_technician():
    db = get_db(); cur = db.cursor(dictionary=True)
    booking_id = request.form['booking_id']
    tech_id = request.form.get('technician_id')
    new_tech_id = int(tech_id) if tech_id else None
    try:
        db.start_transaction()
        cur.execute("""SELECT b.id, b.user_id, b.service_id, b.booking_date, b.time_slot, b.technician_id, b.status,
            s.name AS service_name FROM bookings b
            JOIN services s ON b.service_id=s.id
            WHERE b.id=%s FOR UPDATE""", (booking_id,))
        booking = cur.fetchone()
        if not booking:
            db.rollback(); db.close()
            return jsonify(success=False, message='Booking not found.')

        old_technician_user_id = None
        old_technician_name = None
        if booking['technician_id']:
            cur.execute("SELECT user_id, name FROM technicians WHERE id=%s", (booking['technician_id'],))
            old_technician = cur.fetchone()
            if old_technician:
                old_technician_user_id = old_technician['user_id']
                old_technician_name = old_technician['name']

        if new_tech_id is not None:
            cur.execute("SELECT id, user_id, name, status, service_id FROM technicians WHERE id=%s FOR UPDATE", (new_tech_id,))
            technician = cur.fetchone()
            if not technician:
                db.rollback(); db.close()
                return jsonify(success=False, message='Selected technician was not found.')
            if technician['service_id'] != booking['service_id']:
                db.rollback(); db.close()
                return jsonify(success=False, message='This technician does not match the booked service.')
            if technician['status'] == 'offline':
                db.rollback(); db.close()
                return jsonify(success=False, message='This technician is inactive right now. Please choose another technician.')

            conflict_map = get_technician_conflicts(
                cur,
                [new_tech_id],
                booking['booking_date'],
                booking['time_slot'],
                exclude_booking_id=booking['id'],
            )
            conflict = conflict_map.get(new_tech_id)
            if conflict:
                db.rollback(); db.close()
                return jsonify(
                    success=False,
                    message=f"{technician['name']} is already booked in this slot for {conflict['customer_name']}. Please choose another technician."
                )

        new_status = booking['status']
        if new_tech_id is None and booking['status'] not in ('completed', 'cancelled'):
            new_status = 'pending'
        elif new_tech_id is not None and booking['status'] not in ('completed', 'cancelled'):
            if booking['technician_id'] != new_tech_id and booking['status'] != 'pending':
                # Re-assigned work should come back into the technician request queue.
                new_status = 'pending'

        cur.execute("UPDATE bookings SET technician_id=%s, status=%s WHERE id=%s", (new_tech_id, new_status, booking_id))
        if new_tech_id is None:
            create_notification_if_enabled(
                cur, booking['user_id'], 'assignment_updates',
                'Technician removed from booking',
                f"Your {booking['service_name']} booking for {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']} is back in the assignment queue.",
                'assignment_removed', booking['id']
            )
            if old_technician_user_id:
                create_notification_if_enabled(
                    cur, old_technician_user_id, 'assignment_updates',
                    'Job removed',
                    f"You are no longer assigned to the {booking['service_name']} booking on {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']}.",
                    'assignment_removed', booking['id']
                )
        else:
            if old_technician_user_id and old_technician_user_id != technician['user_id']:
                create_notification_if_enabled(
                    cur, old_technician_user_id, 'assignment_updates',
                    'Job reassigned',
                    f"The {booking['service_name']} booking on {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']} has been reassigned away from you.",
                    'job_reassigned', booking['id']
                )
            create_notification_if_enabled(
                cur, booking['user_id'], 'assignment_updates',
                'Technician assigned',
                f"{technician['name']} is now assigned to your {booking['service_name']} booking for {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']}.",
                'booking_assigned', booking['id']
            )
            create_notification_if_enabled(
                cur, technician['user_id'], 'assignment_updates',
                'New job assigned',
                f"You have been assigned a {booking['service_name']} booking on {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']}.",
                'job_assigned', booking['id']
            )
        db.commit()
        db.close()
        if new_tech_id is None:
            return jsonify(success=True, message='Technician removed. Booking is now back in the assignment queue.')
        return jsonify(success=True, message='Technician assigned successfully!')
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify(success=False, message=f'Could not update technician assignment: {str(e)}')

@app.route('/api/admin/mark_contact_read', methods=['POST'])
@admin_required
def api_mark_contact_read():
    db = get_db(); cur = db.cursor(); cur.execute("UPDATE contact_messages SET is_read=1 WHERE id=%s", (request.form['id'],)); db.close()
    return jsonify(success=True, message='Marked as read.')

@app.route('/api/technician/update_job', methods=['POST'])
@technician_required
def api_update_job():
    booking_id = request.form.get('booking_id')
    new_status = request.form.get('status', '').strip()
    allowed_statuses = {'confirmed', 'in_progress', 'completed', 'cancelled'}
    if not booking_id or new_status not in allowed_statuses:
        return jsonify(success=False, message='Invalid booking action.')

    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT id FROM technicians WHERE user_id=%s", (session['user_id'],))
    tech = cur.fetchone()
    if not tech:
        db.close()
        return jsonify(success=False, message='Technician profile not found.')

    cur.execute("""SELECT b.id, b.status, b.user_id, b.booking_date, b.time_slot, s.name AS service_name
        FROM bookings b JOIN services s ON b.service_id=s.id
        WHERE b.id=%s AND b.technician_id=%s""", (booking_id, tech['id']))
    booking = cur.fetchone()
    if not booking:
        db.close()
        return jsonify(success=False, message='Booking not found for this technician.')

    current_status = booking['status']
    transitions = {
        'pending': {'confirmed', 'cancelled'},
        'confirmed': {'in_progress', 'cancelled'},
        'in_progress': {'completed'},
        'completed': set(),
        'cancelled': set(),
    }
    if new_status not in transitions.get(current_status, set()):
        db.close()
        return jsonify(success=False, message=f'Cannot move a {current_status} job to {new_status}.')

    cur.execute("UPDATE bookings SET status=%s WHERE id=%s", (new_status, booking_id))
    status_text = booking_status_label(new_status)
    create_notification_if_enabled(
        cur, booking['user_id'], 'assignment_updates',
        f'Booking {status_text}',
        f"Your {booking['service_name']} booking for {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']} is now {status_text.lower()}.",
        'booking_status', booking['id']
    )
    create_role_notifications(
        cur, 'admin', 'assignment_updates',
        f'Technician moved booking to {status_text}',
        f"{session['user_name']} marked the {booking['service_name']} booking on {booking['booking_date'].strftime('%d %b')} at {booking['time_slot']} as {status_text.lower()}.",
        'booking_status', booking['id']
    )
    db.close()
    return jsonify(success=True, message='Job updated successfully.')

@app.route('/api/technician/update_availability', methods=['POST'])
@technician_required
def api_update_availability():
    new_status = request.form.get('status', '').strip()
    status_map = {
        'active': 'available',
        'inactive': 'offline',
        'available': 'available',
        'offline': 'offline',
    }
    if new_status not in status_map:
        return jsonify(success=False, message='Invalid availability status.')

    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("UPDATE technicians SET status=%s WHERE user_id=%s", (status_map[new_status], session['user_id']))
    create_role_notifications(
        cur, 'admin', 'system_updates',
        'Technician availability updated',
        f"{session['user_name']} switched availability to {technician_status_label(status_map[new_status]).lower()}.",
        'technician_status'
    )
    db.close()
    return jsonify(success=True, message='Status updated successfully.')

@app.route('/api/update_profile', methods=['POST'])
@login_required
def api_update_profile():
    db = get_db(); cur = db.cursor(dictionary=True)
    email = request.form.get('email', session['user_email']).strip().lower()
    name = request.form['name'].strip()
    phone = request.form['phone'].strip()
    city = request.form.get('city', '').strip()
    address = request.form.get('address', '').strip()
    try:
        cur.execute("UPDATE users SET name=%s, email=%s, phone=%s, city=%s, address=%s WHERE id=%s",
                    (name, email, phone, city, address, session['user_id']))
        cur.execute("SELECT role FROM users WHERE id=%s", (session['user_id'],))
        user_row = cur.fetchone()
        if user_row and user_row['role'] == 'technician':
            cur.execute("UPDATE technicians SET name=%s, email=%s, phone=%s WHERE user_id=%s",
                        (name, email, phone, session['user_id']))
        session['user_name'] = name
        session['user_email'] = email
        db.close()
        return jsonify(success=True, message='Profile updated!')
    except mysql.connector.Error as err:
        db.close()
        # Handle email exists duplicate entry
        if err.errno == 1062:
            return jsonify(success=False, message='That email address is already in use by another account.')
        return jsonify(success=False, message=str(err))

@app.route('/api/upload_profile_image', methods=['POST'])
@login_required
def api_upload_profile_image():
    if 'profile_image' not in request.files:
        return jsonify(success=False, message='No file part')
    file = request.files['profile_image']
    if file.filename == '':
        return jsonify(success=False, message='No selected file')
    
    filename = save_upload(file)
    if filename:
        db = get_db(); cur = db.cursor()
        cur.execute("UPDATE users SET profile_image=%s WHERE id=%s", (filename, session['user_id']))
        db.close()
        return jsonify(success=True, message='Profile photo updated successfully!', filename=filename)
    return jsonify(success=False, message='Invalid file type or upload failed')

@app.route('/api/change_password', methods=['POST'])
@login_required
def api_change_password():
    current_pw = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm_pw = request.form.get('confirm_password', '')
    if not current_pw or not new_pw:
        return jsonify(success=False, message='All fields are required.')
    if len(new_pw) < 6:
        return jsonify(success=False, message='New password must be at least 6 characters.')
    if new_pw != confirm_pw:
        return jsonify(success=False, message='New passwords do not match.')
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT password FROM users WHERE id=%s", (session['user_id'],)); u = cur.fetchone()
    if not check_password(current_pw, u['password']):
        db.close(); return jsonify(success=False, message='Wrong current password.')
    cur.execute("UPDATE users SET password=%s WHERE id=%s", (hash_password(new_pw), session['user_id'])); db.close()
    return jsonify(success=True, message='Password changed successfully!')

@app.route('/api/notifications/mark_read', methods=['POST'])
@login_required
def api_mark_notification_read():
    notification_id = request.form.get('notification_id')
    mark_all = request.form.get('mark_all') == '1'
    db = get_db(); cur = db.cursor()
    if mark_all:
        cur.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s AND is_read=0", (session['user_id'],))
    else:
        cur.execute("UPDATE notifications SET is_read=1 WHERE id=%s AND user_id=%s", (notification_id, session['user_id']))
    db.close()
    return jsonify(success=True, message='Notifications updated.')

@app.route('/api/notifications/preferences', methods=['POST'])
@login_required
def api_update_notification_preferences():
    db = get_db(); cur = db.cursor(dictionary=True)
    ensure_notification_preferences(cur, session['user_id'])
    cur.execute("""UPDATE notification_preferences
        SET booking_updates=%s, assignment_updates=%s, system_updates=%s, email_notifications=%s
        WHERE user_id=%s""", (
            1 if request.form.get('booking_updates') == 'on' else 0,
            1 if request.form.get('assignment_updates') == 'on' else 0,
            1 if request.form.get('system_updates') == 'on' else 0,
            1 if request.form.get('email_notifications') == 'on' else 0,
            session['user_id'],
        ))
    db.close()
    return jsonify(success=True, message='Notification preferences updated.')

@app.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['POST'])
def reset_password():
    email = request.form.get('email', '').strip().lower()
    if not email:
        flash('Please enter your email.', 'error')
        return redirect(url_for('forgot_password'))
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT id FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    db.close()
    if not user:
        flash('No account found with that email.', 'error')
        return redirect(url_for('forgot_password'))
    
    otp = ''.join(random.choices(string.digits, k=6))
    session['reset_email'] = email
    session['reset_otp'] = otp
    success = send_otp_email(email, otp, "FixNear Password Reset Verification")
    if success:
        flash('A 6-digit OTP has been sent to your email. Enter it below.', 'info')
    else:
        flash(f'TESTING MODE (Email Blocked by Render Free Tier): Your OTP is {otp}', 'info')
    return redirect(url_for('verify_reset_otp'))

@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if 'reset_email' not in session:
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        if otp == session.get('reset_otp'):
            session['reset_verified'] = True
            return redirect(url_for('set_new_password'))
        flash('Invalid OTP. Please try again.', 'error')
    return render_template('verify_reset_otp.html')

@app.route('/set_new_password', methods=['GET', 'POST'])
def set_new_password():
    if not session.get('reset_verified'):
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        new_pw = request.form.get('new_password')
        confirm_pw = request.form.get('confirm_password')
        email = session.pop('reset_email', None)
        session.pop('reset_otp', None)
        session.pop('reset_verified', None)
        
        if not email or len(new_pw) < 6 or new_pw != confirm_pw:
            flash('Error trying to set password. Try again.', 'error')
            return redirect(url_for('forgot_password'))
            
        db = get_db(); cur = db.cursor()
        cur.execute("UPDATE users SET password=%s WHERE email=%s", (hash_password(new_pw), email))
        db.close()
        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('set_new_password.html')

@app.route('/book')
@login_required
def book_service():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM services WHERE status='active'"); services = cur.fetchall(); db.close()
    return render_template(
        'book.html',
        services=services,
        selected_service_id=request.args.get('service_id', ''),
        user=get_user(),
        google_maps_api_key=os.getenv('GOOGLE_MAPS_API_KEY', '').strip(),
    )

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
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', port=int(os.environ.get('PORT', 5000)))
