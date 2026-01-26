from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
import re
from app.db.database import get_db
from app.auth.models import User, OTPVerification, PasswordResetToken
from app.auth.schemas import (
    SignupRequest, VerifyOTPRequest, LoginRequest, 
    ForgotPasswordRequest, ResetPasswordRequest, ResendOTPRequest,
    TokenResponse, MessageResponse, SignupResponse, UserProfile, UpdateProfileRequest
)
from app.auth.utils import (
    hash_password, verify_password, generate_otp, generate_reset_token,
    create_jwt_token, decode_jwt_token, send_otp_email, send_password_reset_email
)
from app.core.config import settings
from app.sap.models import District, School

router = APIRouter()

def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")

def _apply_user_access_context(user: User, db: Session) -> User:
    """Attach role and district_id to the user object based on global settings."""
    if getattr(user, "role", None):
        if user.role == "admin":
            user.district_id = None
            user.school_id = None
        return user

    admin_emails = [email.strip().lower() for email in (settings.VPM_ADMIN_EMAILS or "").split(",") if email.strip()]
    if user.email.lower() in admin_emails:
        user.role = "admin"
        user.district_id = None
        user.school_id = None
        return user

    user.role = "user"
    user.district_id = None
    user.school_id = None
    return user

def _build_user_role_payload(user: User, db: Session) -> dict:
    role_value = getattr(user, "role", None) or "user"
    if role_value == "admin":
        role_type = "admin"
    elif role_value.startswith("school-"):
        role_type = "school-user"
    elif role_value.startswith("district-"):
        role_type = "district-user"
    else:
        role_type = "user"

    district_name = None
    school_name = None
    if getattr(user, "district_id", None):
        district = db.query(District).filter(District.id == user.district_id).first()
        district_name = district.name if district else None
    if getattr(user, "school_id", None):
        school = db.query(School).filter(School.id == user.school_id).first()
        school_name = school.name if school else None

    return {
        "role": role_type,
        "districtName": district_name,
        "schoolName": school_name
    }

@router.post("/signup", response_model=SignupResponse)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user and send OTP for verification"""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        # If user exists but is not verified, resend OTP
        if not existing_user.is_verified:
            # Generate and store new OTP
            otp = generate_otp()
            expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
            
            # Delete any existing OTPs for this email
            db.query(OTPVerification).filter(OTPVerification.email == request.email).delete()
            
            otp_record = OTPVerification(
                email=request.email,
                otp=otp,
                expires_at=expiry
            )
            db.add(otp_record)
            db.commit()
            
            # Send OTP email (gracefully handle failures)
            try:
                send_otp_email(request.email, otp)
            except Exception as e:
                # Log the error but don't fail the request
                print(f"Failed to send OTP email: {e}")
            
            # In development mode, return the OTP for testing
            if settings.DEBUG:
                return {
                    "message": "OTP resent to your email for verification", 
                    "username": request.email, 
                    "full_name": existing_user.full_name,
                    "otp": otp
                }
            
            return {
                "message": "OTP resent to your email for verification", 
                "username": request.email, 
                "full_name": existing_user.full_name
            }
        else:
            # User is already verified
            return {"message": "Email already registered", "username": request.email, "full_name": existing_user.full_name}
    
    # Create new user
    hashed_pwd = hash_password(request.password)
    new_user = User(
        full_name=request.full_name,
        email=request.email,
        password_hash=hashed_pwd,
        is_verified=False
    )
    db.add(new_user)
    db.commit()
    
    # Generate and store OTP
    otp = generate_otp()
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    
    # Delete any existing OTPs for this email
    db.query(OTPVerification).filter(OTPVerification.email == request.email).delete()
    
    otp_record = OTPVerification(
        email=request.email,
        otp=otp,
        expires_at=expiry
    )
    db.add(otp_record)
    db.commit()
    
    # Send OTP email (gracefully handle failures)
    try:
        send_otp_email(request.email, otp)
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Failed to send OTP email: {e}")
        # In development, you might want to return the OTP for testing
        # In production, you'd want to log this and handle it appropriately
    
    # In development mode, return the OTP for testing
    if settings.DEBUG:
        return {
            "message": "OTP sent to your email for verification", 
            "username": request.email, 
            "full_name": request.full_name,
            "otp": otp
        }
    
    return {"message": "OTP sent to your email for verification", "username": request.email, "full_name": request.full_name}

@router.post("/verify-otp")
def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify email OTP and activate user account"""
    
    # Find OTP record
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.email == request.email,
        OTPVerification.otp == request.otp
    ).first()
    
    if not otp_record:
        return {"message": "Invalid OTP"}
    
    # Check expiry
    if datetime.now(timezone.utc) > otp_record.expires_at:
        db.delete(otp_record)
        db.commit()
        return {"message": "OTP has expired"}
    
    # Verify user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        return {"message": "User not found"}
    
    user.is_verified = True
    db.delete(otp_record)
    db.commit()
    
    # Generate JWT token
    token = create_jwt_token(user.id, user.email)
    user = _apply_user_access_context(user, db)
    
    role_payload = _build_user_role_payload(user, db)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.email,
        "full_name": user.full_name,
        **role_payload
    }

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    
    try:
        # Find user
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            return {"message": "Invalid credentials"}
        
        # Check if verified
        if not user.is_verified:
            return {"message": "Email not verified. Please verify your email first."}
        
        # Verify password
        if not verify_password(request.password, user.password_hash):
            return {"message": "Invalid credentials"}
        
        # Generate JWT token
        token = create_jwt_token(user.id, user.email)
        user = _apply_user_access_context(user, db)
        
        role_payload = _build_user_role_payload(user, db)
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user.email,
            "full_name": user.full_name,
            **role_payload
        }
    except Exception as e:
        # Log the error for debugging
        print(f"Login error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return error message in development, generic message in production
        if settings.DEBUG:
            return {"message": f"Internal server error: {str(e)}"}
        return {"message": "Internal server error. Please try again later."}

@router.post("/resend-otp", response_model=SignupResponse)
def resend_otp(request: ResendOTPRequest, db: Session = Depends(get_db)):
    """Resend OTP to user's email"""
    
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        return {"message": "Email not registered", "username": request.email, "full_name": ""}
    
    # Check if user is already verified
    if user.is_verified:
        return {"message": "Email already verified", "username": request.email, "full_name": user.full_name}
    
    # Generate and store new OTP
    otp = generate_otp()
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    
    # Delete any existing OTPs for this email
    db.query(OTPVerification).filter(OTPVerification.email == request.email).delete()
    
    otp_record = OTPVerification(
        email=request.email,
        otp=otp,
        expires_at=expiry
    )
    db.add(otp_record)
    db.commit()
    
    # Send OTP email (gracefully handle failures)
    try:
        send_otp_email(request.email, otp)
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Failed to send OTP email: {e}")
    
    # In development mode, return the OTP for testing
    if settings.DEBUG:
        return {
            "message": "OTP resent to your email for verification", 
            "username": request.email, 
            "full_name": user.full_name,
            "otp": otp
        }
    
    return {
        "message": "OTP resent to your email for verification", 
        "username": request.email, 
        "full_name": user.full_name
    }

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset link to user's email"""
    
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "Password reset link sent to your email"}
    
    # Generate reset token
    token = generate_reset_token()
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_TOKEN_EXPIRY_MINUTES)
    
    # Delete any existing tokens for this email
    db.query(PasswordResetToken).filter(
        PasswordResetToken.email == request.email
    ).delete()
    
    reset_token = PasswordResetToken(
        email=request.email,
        token=token,
        expires_at=expiry,
        used=False
    )
    db.add(reset_token)
    db.commit()
    
    # Send reset email (gracefully handle failures)
    try:
        send_password_reset_email(request.email, token)
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Failed to send password reset email: {e}")
        # In development, you might want to return the token for testing
        # In production, you'd want to log this and handle it appropriately
    
    # In development mode, return the token for testing
    if settings.DEBUG:
        return {
            "message": "Password reset link sent to your email", 
            "reset_token": token,
            "reset_link": f"{settings.FRONTEND_URL_8081}/reset-password?token={token}"
        }
    
    return {"message": "Password reset link sent to your email"}

@router.post("/reset-password", response_model=MessageResponse)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset user password using reset token"""
    
    # Find reset token
    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token,
        PasswordResetToken.used == False
    ).first()
    
    if not token_record:
        return {"message": "Invalid or expired reset token"}
    
    # Check expiry
    if datetime.now(timezone.utc) > token_record.expires_at:
        db.delete(token_record)
        db.commit()
        return {"message": "Reset token has expired"}
    
    # Find user
    user = db.query(User).filter(User.email == token_record.email).first()
    if not user:
        return {"message": "User not found"}
    
    # Update password
    user.password_hash = hash_password(request.new_password)
    token_record.used = True
    db.commit()
    
    return {"message": "Password reset successfully. Please log in again."}

def get_user_from_token(authorization: str, db: Session):
    """Helper function to extract and validate user from JWT token"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    token = authorization.split(" ")[1]
    payload = decode_jwt_token(token)
    user_id = payload.get("user_id")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return _apply_user_access_context(user, db)

@router.get("/user/profile", response_model=UserProfile)
def get_profile(authorization: str = Header(...), db: Session = Depends(get_db)):
    """Get current user profile (protected route)"""
    user = get_user_from_token(authorization, db)
    return user

@router.patch("/user/profile", response_model=UserProfile)
def update_profile(
    request: UpdateProfileRequest, 
    authorization: str = Header(...), 
    db: Session = Depends(get_db)
):
    """Update current user profile (protected route)"""
    user = get_user_from_token(authorization, db)
    
    # Update fields if provided
    if request.full_name is not None:
        user.full_name = request.full_name
    
    db.commit()
    db.refresh(user)
    
    return user