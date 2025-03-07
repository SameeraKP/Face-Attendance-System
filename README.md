# Face-Attendance-System

This is a **Face Attendance System** that allows users to mark attendance by detecting their face.  
It works by verifying a user's face and IP address, ensuring that only authorized users within the organization can access it.

## Features
- User authentication with **name, roll number, and email ID**.
- Face detection for **5 seconds** to verify identity.
- IP-based access restriction (only authorized organization IPs allowed).

## Installation
### Prerequisites
- Python 3.13.1
- Flask
- OpenCV
- Other dependencies (install via `requirements.txt`)

Usage

Register as a new user (requires admin approval).
Login with registered credentials.
Face detection starts automatically (must be within the allowed IP range).
Upon success, attendance is recorded in the database.

Technologies Used:

Flask (Backend)
OpenCV (Face Detection)
HTML/CSS/JavaScript (Frontend)
Future Enhancements

Mobile App Integration.
Real-time notifications for unauthorized access attempts.
Improved UI/UX for a seamless experience.
