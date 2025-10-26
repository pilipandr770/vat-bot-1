"""
Quick start script for Counterparty Verification System
"""
import os
import sys

def check_database():
    """Check if database is initialized."""
    db_path = 'counterparty_verification.db'
    if not os.path.exists(db_path):
        print("⚠️  Database not found. Initializing...")
        from application import create_app
        from crm.models import db
        
        app = create_app()
        with app.app_context():
            db.create_all()
            print("✅ Database initialized successfully!")
    else:
        print("✅ Database found.")

def check_dependencies():
    """Check if required packages are installed."""
    required = ['flask', 'sqlalchemy', 'requests']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed.")
    return True

def main():
    """Main startup routine."""
    print("=" * 50)
    print("🚀 Counterparty Verification System")
    print("=" * 50)
    print()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check database
    check_database()
    
    print()
    print("🌐 Starting Flask development server...")
    print("📍 URL: http://127.0.0.1:5000")
    print("⌨️  Press CTRL+C to stop")
    print()
    
    # Start Flask app
    from app import create_app
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5000)

if __name__ == '__main__':
    main()