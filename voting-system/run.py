import os
import sys

# Make backend importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

sys.path.insert(0, BACKEND_DIR)

from app import app, db, seed_data

# Initialize database
with app.app_context():
    db.create_all()
    seed_data()

# This is what Gunicorn will load
application = app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)