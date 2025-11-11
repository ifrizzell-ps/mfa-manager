from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import pyotp
import qrcode
import io
import base64

db = SQLAlchemy()

class MFAAccount(db.Model):
    """Model for storing MFA account information"""
    __tablename__ = 'mfa_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100), nullable=False, unique=True)
    secret = db.Column(db.String(100), nullable=False)
    issuer = db.Column(db.String(100), nullable=True, default='MFA Manager')

    hidden = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    def __init__(self, account_name, secret, issuer=None):
        self.account_name = account_name
        self.secret = secret
        if issuer:
            self.issuer = issuer
    
    def get_totp_code(self):
        """Generate current TOTP code"""
        totp = pyotp.TOTP(self.secret)
        return totp.now()
    
    def get_remaining_time(self):
        """Get remaining time in seconds for current TOTP code"""
        totp = pyotp.TOTP(self.secret)
        return 30 - (int(datetime.now().timestamp()) % 30)
    
    def get_qr_code_url(self):
        """Generate QR code URL for easy setup in authenticator apps"""
        return pyotp.totp.TOTP(self.secret).provisioning_uri(
            name=self.account_name,
            issuer_name=self.issuer
        )
    
    def generate_qr_code_image(self):
        """Generate QR code image as base64 string"""
        qr_url = self.get_qr_code_url()
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 string
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def __repr__(self):
        return f'<MFAAccount {self.account_name}>'
