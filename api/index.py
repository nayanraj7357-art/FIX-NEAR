"""
FixNear — Vercel Serverless Entry Point
BCA Final Year Project Demo
"""

from flask import Flask, render_template, redirect, url_for, session, flash, request, jsonify
import os

# Absolute path fix for Vercel
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.secret_key = 'fixnear_demo_2026'

def demo_flash():
    flash('⚠️ This is a live demo. Database features require local setup. Download the full project from GitHub!', 'info')

# ── Public Pages ──────────────────────────────────────────────
@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception:
        return """
        <html>
        <head><title>FixNear - Home Services</title></head>
        <body style='font-family:sans-serif;text-align:center;padding:50px;background:#0f0f1a;color:white;'>
            <h1 style='color:#6c63ff;'>🔧 FixNear</h1>
            <h2>Online Home Service Booking Platform</h2>
            <p>BCA Final Year Project — Demo Mode</p>
            <p style='color:#aaa;'>Full functionality available when running locally with MySQL.</p>
            <a href='/login' style='background:#6c63ff;color:white;padding:12px 30px;border-radius:8px;text-decoration:none;margin:10px;display:inline-block;'>Login</a>
            <a href='/register' style='background:#333;color:white;padding:12px 30px;border-radius:8px;text-decoration:none;margin:10px;display:inline-block;'>Register</a>
        </body>
        </html>
        """

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('✅ Message received! (Demo Mode — not stored in DB)', 'success')
        return redirect(url_for('contact'))
    try:
        return render_template('contact.html')
    except Exception:
        return "<h2 style='text-align:center;padding:50px;'>Contact page — Demo Mode active. <a href='/'>Go Home</a></h2>"

# ── Auth Routes (Demo) ────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        demo_flash()
        return redirect(url_for('login'))
    try:
        return render_template('login.html')
    except Exception:
        return """
        <html>
        <head><title>FixNear - Login</title></head>
        <body style='font-family:sans-serif;text-align:center;padding:50px;background:#0f0f1a;color:white;'>
            <h2 style='color:#6c63ff;'>🔐 Login — Demo Mode</h2>
            <p style='color:#f0a500;'>⚠️ Database not available in demo. Run locally for full access.</p>
            <a href='/' style='color:#6c63ff;'>← Back to Home</a>
        </body>
        </html>
        """

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        demo_flash()
        return redirect(url_for('register'))
    try:
        return render_template('register.html')
    except Exception:
        return "<h2 style='text-align:center;padding:50px;color:#333;'>Register — Demo Mode. <a href='/'>Go Home</a></h2>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/forgot_password')
def forgot_password():
    try:
        return render_template('forgot_password.html')
    except Exception:
        return "<h2 style='text-align:center;padding:50px;'>Forgot Password — Demo Mode. <a href='/login'>Go to Login</a></h2>"

@app.route('/reset_password', methods=['POST'])
def reset_password():
    demo_flash()
    return redirect(url_for('forgot_password'))

# ── Protected Routes (Demo Redirect) ─────────────────────────
@app.route('/dashboard')
def user_dashboard():
    demo_flash()
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    demo_flash()
    return redirect(url_for('login'))

@app.route('/technician')
def technician_dashboard():
    demo_flash()
    return redirect(url_for('login'))

@app.route('/book')
def book_service():
    demo_flash()
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    demo_flash()
    return redirect(url_for('login'))

# ── API Routes (Demo Responses) ───────────────────────────────
@app.route('/api/<path:subpath>', methods=['GET', 'POST'])
def api_demo(subpath):
    return jsonify(success=False, message='Demo mode: Database not available. Run locally for full functionality.')

# ── Vercel WSGI Handler ───────────────────────────────────────
application = app
