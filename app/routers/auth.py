from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import verify_password, create_access_token, get_password_hash
from ..core.email import generate_otp, send_otp_email
from ..core.config import settings, access_token_expires
from ..schemas.auth import LoginRequest, TokenResponse, RequestResetRequest, VerifyResetRequest
from ..models.user import User
from ..models.otp import OTPRecord

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "username": user.username}, access_token_expires())
    return TokenResponse(access_token=token)


@router.post("/request-reset")
async def request_reset(payload: RequestResetRequest, db: Session = Depends(get_db)):
    """Request password reset: validate passwords, send OTP to email."""
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Validate password strength (optional)
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Generate OTP and hash the pending password
    otp_code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    pending_hash = get_password_hash(payload.new_password)
    
    # Store OTP with pending password hash
    otp_record = OTPRecord(
        email=payload.email,
        otp_code=otp_code,
        pending_password_hash=pending_hash,
        expires_at=expires_at,
        used=False,
    )
    db.add(otp_record)
    db.commit()
    
    # Send OTP email
    await send_otp_email(payload.email, otp_code)
    
    return {"message": "OTP sent to email", "expires_in_minutes": settings.OTP_EXPIRE_MINUTES}


@router.post("/verify-reset")
def verify_reset(payload: VerifyResetRequest, db: Session = Depends(get_db)):
    """Verify OTP and apply new password."""
    otp_record = db.query(OTPRecord).filter(
        OTPRecord.email == payload.email,
        OTPRecord.otp_code == payload.otp_code,
        OTPRecord.used == False,
    ).order_by(OTPRecord.created_at.desc()).first()
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    if otp_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")
    
    # Find user and update password
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.password_hash = otp_record.pending_password_hash
    user.updated_at = datetime.utcnow()
    
    # Mark OTP as used
    otp_record.used = True
    
    db.commit()
    
    return {"message": "Password reset successful"}
