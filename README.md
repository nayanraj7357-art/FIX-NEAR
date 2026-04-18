# FixNear - Local Service Provider Platform

FixNear is a Flask-based web application that connects users with nearby local service providers such as plumbers, electricians, carpenters, and technicians. It includes booking, OTP verification, admin management, technician workflow, and service tracking features.

---

## Features

- User registration and login
- Email OTP verification and password reset
- Service booking with image/file attachments
- Booking detail and payment pages
- User dashboard and profile management
- Technician hub for job requests and status updates
- Admin dashboard for users, services, bookings, and technicians
- Contact form and message management
- Secure password hashing with bcrypt
- Local MySQL database integration
- Optional Google Maps API support for booking location tools

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Templates | Jinja2 |
| Database | MySQL |
| Authentication | bcrypt, Flask sessions |
| Environment | python-dotenv |

---

## Requirements

- Python 3.8+
- MySQL Server
- pip
- Git

---

## Local Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/nayanraj7357-art/FIX-NEAR.git
   cd "FIX NEAR"
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Create the environment file**

   ```bash
   copy .env.example .env
   ```

   Fill the required values in `.env`. Keep the real `.env` file private and never commit it to GitHub.

4. **Set up the database**

   Create a MySQL database named `fixnear`, then run:

   ```bash
   python setup_db.py
   ```

   You can also import the schema from:

   ```text
   database/fixnear.sql
   ```

5. **Run the application**

   ```bash
   python app.py
   ```

   On Windows, you can also run:

   ```bash
   start_fixnear.bat
   ```

6. **Open the app**

   ```text
   http://localhost:5000
   ```

---

## Environment Variables

Use `.env.example` as the public template and keep real values inside `.env`.

```env
SECRET_KEY=change-this-to-a-random-secret-key
DATABASE_URL=
MAIL_USERNAME=
MAIL_PASSWORD=
GOOGLE_MAPS_API_KEY=
ADMIN_PASSWORD=
TECH_PASSWORD=
```

Notes:

- `SECRET_KEY` is required for Flask sessions.
- `MAIL_USERNAME` and `MAIL_PASSWORD` are used for OTP emails.
- `GOOGLE_MAPS_API_KEY` is optional and used for booking location tools.
- `ADMIN_PASSWORD` and `TECH_PASSWORD` are used by the setup script for demo/setup accounts.

---

## Project Structure

```text
FIX NEAR/
├── app.py                    # Main Flask application
├── setup_db.py               # Local database setup script
├── requirements.txt          # Python dependencies
├── start_fixnear.bat         # Windows app starter
├── test_smtp.py              # SMTP/OTP email test helper
├── .env.example              # Environment variable template
├── database/
│   ├── fixnear.sql           # MySQL schema
│   └── fixnear_pg.sql        # PostgreSQL schema/reference
├── static/
│   ├── css/style.css         # Main stylesheet
│   ├── js/script.js          # Frontend JavaScript
│   └── uploads/              # Project images and UI assets
└── templates/                # Flask/Jinja2 HTML pages
```

Local/private/generated files such as `.env`, `output/`, `reset_all.py`, `tempCodeRunnerFile.*`, `.vscode/`, and `__pycache__/` are ignored and should not be committed.

---

## Important Notes

- This repository is currently documented for local Flask + MySQL development.
- The actual `.env` file is ignored for security.
- If Gmail OTP stops working, generate a new Gmail App Password and update `MAIL_PASSWORD` in `.env`.
- If Google Maps features do not load, add a valid browser API key to `GOOGLE_MAPS_API_KEY`.

---

## Developer

Made as a BCA Final Year Project.

---

## License

This project is for educational purposes only.
