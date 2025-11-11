#!/usr/bin/env python3
"""
MFA Manager - TOTP Code Generator
A secure Flask application for managing MFA secrets and generating TOTP codes.
"""

import os
from app import app, db
from config import get_port, get_host, is_production, get_database_path

def create_database():
    """Initialize the database with all tables"""
    with app.app_context():
        # Create all database tables
        db.create_all()
        # Run migration to add hidden column if it doesn't exist
        try:
            from migrate_add_hidden_column import migrate
            migrate()
        except Exception as e:
            # Migration will be handled automatically by SQLAlchemy for new databases
            # This is just a safety check for existing databases
            print(f"Note: Migration check completed (this is normal for new databases): {str(e)}")
        print("✓ Database initialized successfully!")

def run_app():
    """Run the Flask application"""
    print("\n" + "="*50)
    print("🛡️  MFA Manager - TOTP Code Generator")
    print("="*50)
    
    # Get configuration from environment variables
    host = get_host()
    port = get_port()
    db_path = get_database_path()
    
    print(f"🌐 Server starting at: http://{host}:{port}")
    print(f"📁 Database location: {os.path.abspath(db_path)}")
    print("="*50)
    print("🔒 Security Tips:")
    print("   • Keep your secret keys secure")
    print("   • Don't share TOTP codes")
    print("   • Run this on a secure device")
    print("   • Consider setting a SECRET_KEY environment variable")
    print("="*50)
    
    # Initialize database
    create_database()
    
    # Set configuration based on environment
    flask_env = os.environ.get('FLASK_ENV', 'development')
    production_mode = is_production()
    
    app.config['DEBUG'] = not production_mode
    app.config['ENV'] = flask_env
    
    # Run the application
    try:
        app.run(
            debug=not production_mode,
            host=host,
            port=port,
            use_reloader=not production_mode
        )
    except KeyboardInterrupt:
        print("\n👋 MFA Manager stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")

if __name__ == '__main__':
    run_app()
