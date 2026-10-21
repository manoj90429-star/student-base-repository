STUDENTHUB - NEW STUDENT DATABASE PROJECT

FEATURES
Student registration/login, dashboard, profile, photo/document upload,
public service requests and request tracking.
Admin login, dashboard, student database search/view, request status management,
admin notes and contact messages.

ADMIN LOGIN
Username: admin
Password: admin123

WINDOWS RUN
1. Extract ZIP.
2. Open Command Prompt in the project folder.
3. python -m venv venv
4. venv\Scripts\activate
5. pip install -r requirements.txt
6. python app.py
7. Open http://127.0.0.1:5000

The SQLite database is created automatically on first run.
For real deployment, change the secret key/password and add production security.
