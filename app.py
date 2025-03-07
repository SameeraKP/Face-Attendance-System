from flask import Flask, render_template, request, redirect, url_for, session, g, abort, jsonify
from flask_bootstrap import Bootstrap4
from flask_socketio import SocketIO, emit
import sqlite3
import cv2
import base64
import numpy as np
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = "secret"
bootstrap = Bootstrap4(app)
socketio = SocketIO(app)

# Database Path
DB_PATH = "database.db"

# Ensure database exists
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop the tables if they exist
    cursor.execute("DROP TABLE IF EXISTS attendance")
    cursor.execute("DROP TABLE IF EXISTS students")
    cursor.execute("DROP TABLE IF EXISTS admin")

    cursor.execute('''CREATE TABLE IF NOT EXISTS students (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT, roll_no TEXT, email TEXT, password TEXT, approved INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      student_id INTEGER, checkin TEXT, checkout TEXT,
                      FOREIGN KEY(student_id) REFERENCES students(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT, password TEXT)''')
    conn.commit()
    conn.close()

@app.before_request
def before_request():
    g.db = sqlite3.connect(DB_PATH)

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()

# Restrict access to specific IP addresses
ALLOWED_IPS = ["127.0.0.1", "192.168.1.100"]  # Replace with your desired IPs

@app.before_request
def restrict_ip():
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        abort(403)  # Return HTTP 403 Forbidden if the IP is not allowed

first_request = True

@app.before_request
def create_default_admin():
    global first_request
    if first_request:
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM admin WHERE username = ?", ('admin',))
        admin = cursor.fetchone()
        
        if not admin:
            cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", 
                           ('admin', 'password123'))  # Set default admin credentials
            g.db.commit()
        first_request = False

# Dashboard
@app.route('/')
def dashboard():
    user = session.get('user_id')
    if user:
        return render_template('dashboard.html', user=session)
    
    # Fetch attendance records
    cursor = g.db.cursor()
    cursor.execute('''SELECT attendance.checkin, attendance.checkout, students.name, students.roll_no
                      FROM attendance
                      INNER JOIN students ON attendance.student_id = students.id''')
    attendance_records = cursor.fetchall()
    return render_template('dashboard.html', user=None, attendance_records=attendance_records)

# Register User
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        email = request.form['email']
        password = request.form['password']
        cursor = g.db.cursor()
        cursor.execute("INSERT INTO students (name, roll_no, email, password) VALUES (?, ?, ?, ?)", 
                       (name, roll_no, email, password))
        g.db.commit()
        return redirect(url_for('admin'))  # Redirect to admin for approval
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM students WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()

        if user:
            if user[5] == 1:  # Check if approved
                session['user_id'] = user[0]
                session['name'] = user[1]
                return redirect(url_for('face_detection'))  # Redirect to face detection
            else:
                return "Waiting for admin approval."
        else:
            return "Invalid Credentials."

    return render_template('login.html')

# Admin Login
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM admin WHERE username = ? AND password = ?", (username, password))
        admin = cursor.fetchone()
        if admin:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid credentials."

    return render_template('admin_login.html')

# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' in session:
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM students WHERE approved = 0")
        pending_users = cursor.fetchall()
        return render_template('admin_dashboard.html', pending_users=pending_users)
    return redirect(url_for('admin'))

@app.route('/approve/<int:student_id>')
def approve_user(student_id):
    if 'admin' in session:
        cursor = g.db.cursor()
        cursor.execute("UPDATE students SET approved = 1 WHERE id = ?", (student_id,))
        g.db.commit()
        return redirect(url_for('admin_dashboard'))
    return "Unauthorized."

# Face Detection
@app.route('/face_detection')
def face_detection():
    if 'user_id' in session:
        return render_template('face_detection.html')
    return redirect(url_for('login'))

# Check-In Route
@app.route('/checkin')
def checkin():
    user_id = session.get('user_id')
    if user_id:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = g.db.cursor()
        cursor.execute("INSERT INTO attendance (student_id, checkin, checkout) VALUES (?, ?, NULL)", (user_id, timestamp))
        g.db.commit()
        return "Check-in successful!"
    return "User not logged in."

# Check-Out Route
@app.route('/checkout')
def checkout():
    user_id = session.get('user_id')
    if user_id:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = g.db.cursor()
        cursor.execute("UPDATE attendance SET checkout = ? WHERE student_id = ? AND checkout IS NULL", (timestamp, user_id))
        g.db.commit()
        return "Check-out successful!"
    return "User not logged in."

# Records Route
@app.route('/records')
def records():
    # Fetch attendance records
    cursor = g.db.cursor()
    cursor.execute('''SELECT attendance.checkin, attendance.checkout, students.name, students.roll_no
                      FROM attendance
                      INNER JOIN students ON attendance.student_id = students.id''')
    attendance_records = cursor.fetchall()
    return render_template('records.html', attendance_records=attendance_records)

@socketio.on('frame')
def handle_frame(frame):
    try:
        imgdata = base64.b64decode(frame.split(',')[1])
        img = cv2.imdecode(np.frombuffer(imgdata, np.uint8), cv2.IMREAD_COLOR)
        print("Image decoded successfully")

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        print("Face cascade loaded")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        print(f"Faces detected: {len(faces)}")

        face_detected = len(faces) > 0
        emit('face_detected', {'face_detected': face_detected})

    except Exception as e:
        print(f"Error processing frame: {e}")

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)
