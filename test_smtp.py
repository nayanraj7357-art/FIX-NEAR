import os
import smtplib
from dotenv import load_dotenv

load_dotenv('d:\\FIX NEAR\\.env')
mail_user = os.environ.get('MAIL_USERNAME')
mail_pass = os.environ.get('MAIL_PASSWORD')

try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(mail_user, mail_pass)
    print("LOGIN SUCCESSFUL!")
    server.quit()
except Exception as e:
    print("LOGIN FAILED:", e)
