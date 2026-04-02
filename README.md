# 🔧 FixNear — Local Service Provider Platform

FixNear ek web-based platform hai jo users ko unke nearby local service providers (plumbers, electricians, carpenters, etc.) se connect karta hai.

---

## 📌 Features

- User & Service Provider Registration/Login
- Service booking system
- Admin dashboard for management
- Secure authentication with bcrypt
- MySQL database integration

---

## 🛠️ Tech Stack

| Layer    | Technology          |
|----------|---------------------|
| Backend  | Python (Flask)      |
| Frontend | HTML, CSS, Bootstrap|
| Database | MySQL               |
| Auth     | bcrypt              |

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL Server
- pip

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/fix-near.git
   cd fix-near
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the database**
   - Create a MySQL database named `fixnear`
   - Run the setup script:
   ```bash
   python setup_db.py
   ```

4. **Run the application**
   ```bash
   python app.py
   ```
   Or double-click `start_fixnear.bat` (Windows)

5. **Open in browser**
   ```
   http://localhost:5000
   ```

---

## 📁 Project Structure

```
FIX NEAR/
├── app.py              # Main Flask application
├── setup_db.py         # Database setup script
├── requirements.txt    # Python dependencies
├── start_fixnear.bat   # Windows startup script
├── static/             # CSS, JS, Images
└── templates/          # HTML templates (Jinja2)
```

---

## 👨‍💻 Developer

Made with ❤️ as a BCA Final Year Project

---

## 📄 License

This project is for educational purposes only.
