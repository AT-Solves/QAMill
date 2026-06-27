"""
Authentication routes - Register, Login, Refresh, Logout
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from schemas_auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    RefreshRequest,
    RefreshResponse,
    ChangePasswordRequest,
    UserProfile,
    ErrorResponse,
)
from services.auth_service import AuthService
from database import SessionLocal
from config.settings import settings

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """Get current user from JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")

        auth_service = AuthService(db)
        user = auth_service.get_user_from_token(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return user
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")


# ── Registration & Login ──
@router.post("/register", response_model=RegisterResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user"""
    auth_service = AuthService(db)

    result = auth_service.register_user(
        email=request.email,
        password=request.password,
        name=request.name,
    )

    if not result:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    user, access_token, refresh_token = result
    access_token_expire = settings.auth.access_token_expire_minutes * 60

    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login user with email and password"""
    auth_service = AuthService(db)

    result = auth_service.login_user(
        email=request.email,
        password=request.password,
    )

    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    user, access_token, refresh_token = result
    access_token_expire = settings.auth.access_token_expire_minutes * 60

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=access_token_expire,
    )


# ── Token Management ──
@router.post("/refresh", response_model=RefreshResponse)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    auth_service = AuthService(db)

    access_token = auth_service.refresh_access_token(request.refresh_token)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )

    access_token_expire = settings.auth.access_token_expire_minutes * 60

    return RefreshResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=access_token_expire,
    )


@router.post("/logout")
def logout(current_user=Depends(get_current_user)):
    """Logout user (token invalidation handled client-side)"""
    return {"message": "Logged out successfully"}


# ── User Profile ──
@router.get("/me", response_model=UserProfile)
def get_current_user_profile(current_user=Depends(get_current_user)):
    """Get current user profile"""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
    )


# ── Password Management ──
@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change user password"""
    auth_service = AuthService(db)

    if not auth_service.change_password(
        current_user.id,
        request.old_password,
        request.new_password,
    ):
        raise HTTPException(
            status_code=400,
            detail="Old password is incorrect",
        )

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(
    email: str,
    db: Session = Depends(get_db),
):
    """Request password reset"""
    from models.database import User

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if email exists
        return {"message": "If email exists, reset link will be sent"}

    auth_service = AuthService(db)
    reset_token = auth_service.reset_password_token(user.id)

    # TODO: Send reset token via email
    # For now, return token (in production, send via email)

    return {
        "message": "Password reset link sent to email",
        "reset_token": reset_token,  # Remove in production
    }


@router.post("/reset-password")
def reset_password(
    reset_token: str,
    new_password: str,
    db: Session = Depends(get_db),
):
    """Reset password using reset token"""
    auth_service = AuthService(db)

    if not auth_service.reset_password(reset_token, new_password):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token",
        )

    return {"message": "Password reset successfully"}
