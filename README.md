# CampusFix AI

A hackathon-ready Flask + SQLite prototype for smart campus complaint management.

## Features
- Student complaint submission
- Automatic category detection
- Priority detection
- Department assignment
- Similar complaint detection
- Admin dashboard
- Live statistics
- Complaint status updates
- Demo data loader

## Run on Windows

1. Install Python 3.10+.
2. Open this folder in VS Code.
3. Open Terminal.
4. Run:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

5. Open:
http://127.0.0.1:5000

## Demo
Click "Load demo complaints" or open:
http://127.0.0.1:5000/seed

Then open:
http://127.0.0.1:5000/admin

## Important
This prototype uses lightweight rule-based NLP so it works without paid AI APIs or internet. For a stronger hackathon version, replace `classify()` with an LLM/NLP service and add authentication, real-time notifications, and better semantic duplicate detection.
