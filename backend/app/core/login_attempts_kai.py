from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models import LoginAttempt

router = APIRouter()

class LoginAttemptCreate(BaseModel):
    email: str
    ip_address: Optional[str] = None
    success: bool

@router.post("/api/login_attempts")
def log_login_attempt(attempt: LoginAttemptCreate, db: Session = Depends(get_db)):
    """Log a login attempt for security monitoring."""
    new_attempt = LoginAttempt(
        email=attempt.email,
        ip_address=attempt.ip_address,
        success=attempt.success
    )
    db.add(new_attempt)
    db.commit()
    db.refresh(new_attempt)
    return {"message": "Login attempt logged", "attempt": new_attempt}

@router.get("/api/login-attempts")
def get_all_login_attempts(db: Session = Depends(get_db)):
    """Fetch all login attempts (admin only)."""
    attempts = db.query(LoginAttempt).order_by(LoginAttempt.attempted_at.desc()).all()
    return {"count": len(attempts), "attempts": attempts}

@router.get("/api/login-attempts/email/{email}")
def get_login_attempts_by_email(email: str, db: Session = Depends(get_db)):
    """Fetch login attempts for a specific email address."""
    attempts = db.query(LoginAttempt).filter(LoginAttempt.email == email).all()
    return {"count": len(attempts), "attempts": attempts}

@router.get("/api/login-attempts/failed")
def get_failed_attempts(db: Session = Depends(get_db)):
    """Fetch all failed login attempts."""
    attempts = db.query(LoginAttempt).filter(LoginAttempt.success == False).all()
    return {"count": len(attempts), "attempts": attempts}

@router.get("/api/login-attempts/check-rate-limit")
def check_rate_limit(email: str, minutes: int = 15, max_attempts: int = 5, db: Session = Depends(get_db)):
    """Check if an email has exceeded the rate limit."""
    time_threshold = datetime.now() - timedelta(minutes=minutes)
    
    recent_attempts = db.query(LoginAttempt).filter(
        LoginAttempt.email == email,
        LoginAttempt.attempted_at > time_threshold,
        LoginAttempt.success == False
    ).count()
    
    is_blocked = recent_attempts >= max_attempts
    
    return {
        "email": email,
        "recent_failed_attempts": recent_attempts,
        "max_allowed": max_attempts,
        "is_blocked": is_blocked,
        "message": "Account is temporarily locked" if is_blocked else "Account is active"
    }

@router.delete("/api/login-attempts/email/{email}")
def clear_login_attempts(email: str, db: Session = Depends(get_db)):
    """Clear login attempts for a specific email (after successful login)."""
    deleted = db.query(LoginAttempt).filter(LoginAttempt.email == email).delete()
    db.commit()
    return {"message": f"Cleared {deleted} login attempts for {email}"}
