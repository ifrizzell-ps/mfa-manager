"""
Migration script to add 'hidden' column to mfa_accounts table.
This script adds a 'hidden' boolean column with default value False to existing databases.
"""
import sqlite3
import os
from config import get_database_path

def migrate():
    """Add hidden column to mfa_accounts table if it doesn't exist"""
    database_path = get_database_path()
    
    if not os.path.exists(database_path):
        print(f"Database file not found at {database_path}")
        print("The hidden column will be created automatically when the app starts.")
        return
    
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(mfa_accounts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'hidden' in columns:
            print("Column 'hidden' already exists in mfa_accounts table.")
            conn.close()
            return
        
        # Add the hidden column with default value False
        # Note: SQLite doesn't support NOT NULL in ALTER TABLE ADD COLUMN in older versions
        # So we add it as nullable first, then set default values, then make it NOT NULL if possible
        print("Adding 'hidden' column to mfa_accounts table...")
        try:
            # Try to add with NOT NULL and DEFAULT (works in SQLite 3.1.3+)
            cursor.execute("ALTER TABLE mfa_accounts ADD COLUMN hidden BOOLEAN NOT NULL DEFAULT 0")
            conn.commit()
            print("Migration completed successfully!")
        except sqlite3.OperationalError as e:
            # If that fails, try adding as nullable with default
            if "NOT NULL" in str(e) or "DEFAULT" in str(e):
                print("Attempting alternative migration method...")
                cursor.execute("ALTER TABLE mfa_accounts ADD COLUMN hidden BOOLEAN DEFAULT 0")
                # Update all existing rows to have hidden = 0 (False)
                cursor.execute("UPDATE mfa_accounts SET hidden = 0 WHERE hidden IS NULL")
                conn.commit()
                print("Migration completed successfully (using alternative method)!")
            else:
                raise
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

