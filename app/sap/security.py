"""
Security utilities for public intake endpoints
- Rate limiting
- CAPTCHA validation
- IP tracking
"""

from fastapi import Request, HTTPException
from typing import Optional
import os
from app.core.config import settings

# Optional httpx for CAPTCHA validation
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    print("WARNING: httpx not installed. CAPTCHA validation will be skipped. Install with: pip install httpx")


async def validate_captcha(captcha_token: Optional[str] = None) -> bool:
    """
    Validate CAPTCHA token with Google reCAPTCHA or hCaptcha
    
    Returns True if valid or if CAPTCHA is disabled
    Raises HTTPException if validation fails
    """
    if not captcha_token:
        # In development, allow without CAPTCHA if DEBUG=True
        if settings.DEBUG:
            return True
        # In production, require CAPTCHA
        raise HTTPException(
            status_code=400,
            detail="CAPTCHA validation required"
        )
    
    # Get CAPTCHA secret from environment
    captcha_secret = os.getenv("CAPTCHA_SECRET_KEY")
    captcha_service = os.getenv("CAPTCHA_SERVICE", "recaptcha")  # recaptcha or hcaptcha
    
    if not captcha_secret:
        # If no secret configured, skip validation in development
        if settings.DEBUG:
            print("WARNING: CAPTCHA_SECRET_KEY not set, skipping validation")
            return True
        raise HTTPException(
            status_code=500,
            detail="CAPTCHA configuration error"
        )
    
    if not HTTPX_AVAILABLE:
        if settings.DEBUG:
            print("WARNING: httpx not available, skipping CAPTCHA validation in DEBUG mode")
            return True
        raise HTTPException(
            status_code=500,
            detail="CAPTCHA validation service unavailable"
        )
    
    try:
        if captcha_service == "recaptcha":
            # Google reCAPTCHA v3
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.google.com/recaptcha/api/siteverify",
                    data={
                        "secret": captcha_secret,
                        "response": captcha_token
                    },
                    timeout=5.0
                )
                result = response.json()
                
                if not result.get("success"):
                    raise HTTPException(
                        status_code=400,
                        detail="CAPTCHA validation failed"
                    )
                
                # Optional: Check score for reCAPTCHA v3 (threshold: 0.5)
                score = result.get("score", 1.0)
                if score < 0.5:
                    raise HTTPException(
                        status_code=400,
                        detail="CAPTCHA verification failed"
                    )
        
        elif captcha_service == "hcaptcha":
            # hCaptcha
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://hcaptcha.com/siteverify",
                    data={
                        "secret": captcha_secret,
                        "response": captcha_token
                    },
                    timeout=5.0
                )
                result = response.json()
                
                if not result.get("success"):
                    raise HTTPException(
                        status_code=400,
                        detail="CAPTCHA validation failed"
                    )
        
        return True
        
    except httpx.TimeoutException:
        # If CAPTCHA service is down, allow in development, block in production
        if settings.DEBUG:
            print("WARNING: CAPTCHA service timeout, allowing in DEBUG mode")
            return True
        raise HTTPException(
            status_code=503,
            detail="CAPTCHA service unavailable"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"CAPTCHA validation error: {e}")
        if settings.DEBUG:
            return True
        raise HTTPException(
            status_code=500,
            detail="CAPTCHA validation error"
        )


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for forwarded IP (behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Try to use slowapi's get_remote_address if available
    try:
        from slowapi.util import get_remote_address
        return get_remote_address(request)
    except ImportError:
        # Fallback: get IP from request client
        if request.client:
            return request.client.host
        return "unknown"


def check_duplicate_submission(
    db,
    student_first_name: str,
    student_last_name: str,
    date_of_birth: str,
    parent_email: str,
    within_minutes: int = 5
) -> bool:
    """
    Check if a similar submission was made recently
    Returns True if duplicate found
    """
    from datetime import datetime, timedelta, timezone
    from app.sap.models import IntakeQueue
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)
    
    # Query recent intake queue records (plain text now)
    recent_intakes = db.query(IntakeQueue).filter(
        IntakeQueue.created_at >= cutoff_time
    ).all()
    
    for intake in recent_intakes:
        # Compare plain text fields
        stored_first = getattr(intake, 'student_first_name', None) or ""
        stored_last = getattr(intake, 'student_last_name', None) or ""
        stored_dob = getattr(intake, 'date_of_birth', None)
        stored_email = getattr(intake, 'parent_email', None) or ""
        
        # Format date for comparison
        stored_dob_str = stored_dob.strftime("%Y-%m-%d") if stored_dob else None
        
        if (stored_first.lower() == student_first_name.lower() and
            stored_last.lower() == student_last_name.lower() and
            stored_dob_str == date_of_birth and
            stored_email.lower() == parent_email.lower()):
            return True
    
    return False

