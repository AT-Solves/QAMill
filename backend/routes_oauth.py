"""
OAuth routes - GitHub and Google login
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from schemas_auth import LoginResponse
from services.oauth_service import OAuthService
from database import SessionLocal
from config.settings import settings

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── OAuth Redirect URLs ──
@router.get("/github/login")
def github_login():
    """Redirect to GitHub login"""
    oauth_service = OAuthService(SessionLocal())
    return {"redirect_url": oauth_service.get_github_login_url()}


@router.get("/google/login")
def google_login():
    """Redirect to Google login"""
    oauth_service = OAuthService(SessionLocal())
    return {"redirect_url": oauth_service.get_google_login_url()}


# ── OAuth Callbacks ──
@router.post("/github/callback", response_model=LoginResponse)
async def github_callback(
    code: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle GitHub OAuth callback"""
    oauth_service = OAuthService(db)

    result = await oauth_service.github_callback(code)
    if not result:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed",
        )

    user, access_token, refresh_token = result
    access_token_expire = settings.auth.access_token_expire_minutes * 60

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=access_token_expire,
    )


@router.post("/google/callback", response_model=LoginResponse)
async def google_callback(
    code: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Google OAuth callback"""
    oauth_service = OAuthService(db)

    result = await oauth_service.google_callback(code)
    if not result:
        raise HTTPException(
            status_code=401,
            detail="Google authentication failed",
        )

    user, access_token, refresh_token = result
    access_token_expire = settings.auth.access_token_expire_minutes * 60

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=access_token_expire,
    )


# ── OAuth Status ──
@router.get("/status")
def oauth_status():
    """Check OAuth provider status"""
    github_configured = bool(
        settings.oauth.github_client_id
        and settings.oauth.github_client_secret
    )
    google_configured = bool(
        settings.oauth.google_client_id
        and settings.oauth.google_client_secret
    )

    return {
        "github_configured": github_configured,
        "google_configured": google_configured,
        "github_client_id": settings.oauth.github_client_id[:10] + "..."
        if github_configured
        else "Not configured",
        "google_client_id": settings.oauth.google_client_id[:10] + "..."
        if google_configured
        else "Not configured",
    }
