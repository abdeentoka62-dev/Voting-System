import subprocess
import sys
import os

def install_deps():
    print("📦 Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r",
                           "backend/requirements.txt", "-q"])

def generate_images():
    if not os.path.exists("frontend/static/images/default-candidate.jpg"):
        print("🖼️  Generating default candidate images...")
        subprocess.call([sys.executable, "generate_default_image.py"])

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    install_deps()
    generate_images()
    print("\n🚀 Starting server at: http://127.0.0.1:5000")
    print("📋 Admin credentials: National ID = admin | Password = Admin@2026\n")
    
    # Change to backend directory and run app
    sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))
    os.chdir("backend")
    
    # Import Flask app and initialize database
    from app import app, db
    
    # Create database tables and seed data
    with app.app_context():
        print("📊 Initializing database...")
        db.create_all()
        
        # Import and run seed_data
        from app import seed_data
        seed_data()
        print("✅ Database ready!\n")
    
    # Run the Flask app (disable reloader to avoid path issues)
    app.run(debug=True, port=5000, use_reloader=False)
