from datetime import datetime, timedelta, timezone
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, OTPVerification
from ..security import hash_password, verify_password, create_access_token
from ..dependencies import get_current_user
from ..email_service import send_otp_email, smtp_enabled

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


def generate_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)


def create_otp(db: Session, email: str) -> str:
    email = email.lower().strip()

    db.query(OTPVerification).filter(
        OTPVerification.email == email
    ).delete(synchronize_session=False)

    otp = generate_otp()

    row = OTPVerification(
        email=email,
        otp=otp,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )

    db.add(row)
    db.commit()

    return otp


def get_valid_otp(db: Session, email: str, otp: str):
    email = email.lower().strip()

    row = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.email == email,
            OTPVerification.otp == otp.strip(),
        )
        .order_by(OTPVerification.created_at.desc())
        .first()
    )

    if not row:
        return None

    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        db.delete(row)
        db.commit()
        return None

    return row


@router.post("/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    name = data.name.strip()
    email = data.email.lower().strip()

    if not name:
        raise HTTPException(422, "Name is required")

    if len(data.password) < 6:
        raise HTTPException(
            422,
            "Password must contain at least 6 characters",
        )

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if user and user.is_verified:
        raise HTTPException(
            400,
            "Email is already registered",
        )

    password_hash = hash_password(data.password)

    if user:
        user.name = name
        user.password_hash = password_hash
        user.is_verified = False
    else:
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            is_verified=False,
        )
        db.add(user)

    db.commit()

    otp = create_otp(db, email)

    try:
        send_otp_email(email, otp, "register")
    except Exception as error:
        print("OTP email delivery failed:", str(error))
        raise HTTPException(
            status_code=503,
            detail="We could not send the verification email. Please try again in a moment.",
        )

    development_mode = not smtp_enabled()
    return {
        "message": "Verification code sent to your email." if not development_mode else "Development mode: the OTP is printed in the backend terminal.",
        "email": email,
        "development_mode": development_mode,
    }


@router.post("/verify-otp")
def verify_otp(
    data: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    email = data.email.lower().strip()

    otp_row = get_valid_otp(db, email, data.otp)

    if not otp_row:
        raise HTTPException(
            400,
            "Invalid or expired OTP",
        )

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            404,
            "User registration not found",
        )

    user.is_verified = True

    db.delete(otp_row)
    db.commit()
    db.refresh(user)

    return {
        "message": "Account verified successfully",
        "verified": True,
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
        },
    }


@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    email = data.email.lower().strip()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
        )

    if not user.is_verified:
        raise HTTPException(
            403,
            "Please verify your email first",
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
        },
    }


@router.get("/me")
def me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
    }


@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    email = data.email.lower().strip()

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if user:
        otp = create_otp(db, email)

        try:
            send_otp_email(email, otp, "reset")
        except Exception as error:
            print("Password reset OTP email delivery failed:", str(error))
            # Keep the response generic so account existence is not disclosed.


    return {
        "message": "If this email is registered, an OTP has been sent.",
        "development_mode": not smtp_enabled(),
    }


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    if len(data.new_password) < 6:
        raise HTTPException(
            422,
            "Password must contain at least 6 characters",
        )

    email = data.email.lower().strip()

    otp_row = get_valid_otp(db, email, data.otp)

    if not otp_row:
        raise HTTPException(
            400,
            "Invalid or expired OTP",
        )

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            404,
            "User not found",
        )

    user.password_hash = hash_password(data.new_password)

    db.delete(otp_row)
    db.commit()

    return {
        "message": "Password reset successfully",
    }
