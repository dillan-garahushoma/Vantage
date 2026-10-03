from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import secrets
from app.database import get_db
from app.models import Session as SessionModel, User

router = APIRouter()

# schema for refreshing a session
class SessionCreate(BaseModel):
    user_id: int
    expires_in_minutes: Optional[int] = 30

class SessionRefresh(BaseModel):
    refresh_token: str

# schema for refreshing a session
@router.post("/api/sessions")
def create_session(session_date: SessionCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == session_date.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # generate refresh token
    refresh_token = secrets.token_urlsafe(64)
    expires_at = datetime.now() + timedelta(minutes=session_date.expires_in_minutes)

    new_session = SessionModel(
        user_id = session_date.user_id,
        refresh_token = refresh_token,
        expires_at = expires_at
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {
        "message": "Session created successfully",
        "session_id": new_session.session_id,
        "refresh_token": refresh_token,
        "expires_at": expires_at
    }

@router.post("/api/sessions/refresh")
def refresh_session(refresh_data: SessionRefresh, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.refresh_token == refresh_data.refresh_token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Invalid refresh token")

    if session.expires_at < datetime.now():
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=404, detail="Refresh token expired")

    # generate new refresh token
    new_refresh_token = secrets.token_urlsafe(64)
    new_expires_at = datetime.now() + timedelta(minutes=30)

    session.refresh_token = new_refresh_token
    session.expires_at = new_expires_at
    db.commit()
    db.refresh(session)

    return {
        "message": "Session refreshed sucessfully",
        "refresh_token": new_refresh_token,
        "expires_at": new_expires_at
    }

@router.delete("/api/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return {"message": "Session deleted sucessfully"}

@router.get("/api/sessions/user/{user_id}")
def get_user_sessions(user_id: int, db: Session = Depends(get_db)):
    sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.expires_at > datetime.now()
    ).all()
    return {"count": len(sessions), "sessions": sessions}
