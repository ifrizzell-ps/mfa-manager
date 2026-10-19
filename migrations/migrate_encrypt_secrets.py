from models import db, MFAAccount
from flask import current_app
from cryptography.fernet import Fernet
import sqlalchemy as sa

def migrate():
    """Migrate all plain text secrets to encrypted secrets"""
    key = current_app.config.get('ENCRYPTION_KEY')
    if not key:
        print("⏭️  Skipping encryption migration: ENCRYPTION_KEY not set.")
        return

    try:
        f = Fernet(key.encode())
    except Exception as e:
        print(f"❌ Error: Invalid ENCRYPTION_KEY format: {str(e)}")
        return

    # Use raw SQL to fetch current secrets to avoid the model's automatic decryption logic
    # which might fail or be confusing during migration
    connection = db.engine.connect()
    accounts = connection.execute(sa.text("SELECT id, secret FROM mfa_accounts")).fetchall()
    
    updated_count = 0
    for account_id, raw_secret in accounts:
        # Check if it's already encrypted
        is_encrypted = False
        try:
            f.decrypt(raw_secret.encode())
            is_encrypted = True
        except Exception:
            # Not encrypted or encrypted with a different key
            pass
            
        if not is_encrypted:
            # Encrypt the plain text secret
            encrypted_secret = f.encrypt(raw_secret.encode()).decode()
            
            # Update the record using raw SQL to be safe
            connection.execute(
                sa.text("UPDATE mfa_accounts SET secret = :secret WHERE id = :id"),
                {"secret": encrypted_secret, "id": account_id}
            )
            updated_count += 1
    
    connection.commit()
    connection.close()
    
    if updated_count > 0:
        print(f"✅ Successfully encrypted {updated_count} MFA secrets.")
    else:
        print("ℹ️  No secrets needed encryption.")

if __name__ == "__main__":
    from app import app
    with app.app_context():
        migrate()
