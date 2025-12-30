import smtplib
import random
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, status
from app.core.config import settings

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    # Truncate password to 72 bytes to avoid bcrypt limitation
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Use bcrypt directly
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    # Truncate password to 72 bytes to match hash_password behavior
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Use bcrypt directly
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def generate_reset_token() -> str:
    """Generate a unique reset token"""
    return str(uuid.uuid4())

def create_jwt_token(user_id: int, email: str) -> str:
    """Create a JWT access token"""
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expiry
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token

def decode_jwt_token(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

def send_email(to_email: str, subject: str, body: str):
    """Send an email using SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
        )

def send_otp_email(email: str, otp: str):
    """Send OTP verification email"""
    subject = "Your Verification Code"
    body = f"""
    <html>
        <body>
            <h2>Email Verification</h2>
            <p>Your verification code is: <strong>{otp}</strong></p>
            <p>This code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.</p>
            <p>If you did not request this code, please ignore this email.</p>
        </body>
    </html>
    """
    send_email(email, subject, body)

def send_password_reset_email(email: str, token: str):
    """Send password reset email"""
    reset_link = f"{settings.FRONTEND_URL_8081}/reset-password?token={token}"
    subject = "Password Reset Request"
    body = f"""
    <html>
        <body>
            <h2>Password Reset</h2>
            <p>You requested to reset your password.</p>
            <p>Click the link below to reset your password:</p>
            <p><a href="{reset_link}">Reset Password</a></p>
            <p>This link will expire in {settings.RESET_TOKEN_EXPIRY_MINUTES} minutes.</p>
            <p>If you did not request this reset, please ignore this email.</p>
        </body>
    </html>
    """
    send_email(email, subject, body)