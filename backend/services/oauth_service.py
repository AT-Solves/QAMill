"""
OAuth Service - GitHub & Google integration
Social login with automatic user creation
"""
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from models.database import User
from config.settings import settings
from services.auth_service import AuthService
import httpx
import json
from datetime import datetime


class OAuthService:
    """OAuth service for GitHub and Google"""

    def __init__(self, db: Session):
        self.db = db
        self.auth_service = AuthService(db)

    # ── GitHub OAuth ──
    async def github_callback(self, code: str) -> Optional[Tuple[User, str, str]]:
        """Handle GitHub OAuth callback"""
        try:
            # Exchange code for access token
            token_response = await self._exchange_github_code(code)
            if not token_response:
                return None

            access_token = token_response.get("access_token")
            if not access_token:
                return None

            # Get user info from GitHub
            user_info = await self._get_github_user(access_token)
            if not user_info:
                return None

            # Find or create user
            user = await self._get_or_create_user(
                email=user_info.get("email"),
                name=user_info.get("name", user_info.get("login", "GitHub User")),
                avatar_url=user_info.get("avatar_url"),
                oauth_provider="github",
                oauth_id=str(user_info.get("id")),
            )

            if not user:
                return None

            # Generate JWT tokens
            jwt_access, jwt_refresh = self.auth_service.generate_tokens(user.id)
            return user, jwt_access, jwt_refresh

        except Exception as e:
            print(f"GitHub OAuth error: {e}")
            return None

    async def _exchange_github_code(self, code: str) -> Optional[Dict]:
        """Exchange GitHub auth code for access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": settings.oauth.github_client_id,
                        "client_secret": settings.oauth.github_client_secret,
                        "code": code,
                        "redirect_uri": settings.oauth.github_redirect_uri,
                    },
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error exchanging GitHub code: {e}")
        return None

    async def _get_github_user(self, access_token: str) -> Optional[Dict]:
        """Get GitHub user info"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error getting GitHub user: {e}")
        return None

    # ── Google OAuth ──
    async def google_callback(self, code: str) -> Optional[Tuple[User, str, str]]:
        """Handle Google OAuth callback"""
        try:
            # Exchange code for access token
            token_response = await self._exchange_google_code(code)
            if not token_response:
                return None

            access_token = token_response.get("access_token")
            if not access_token:
                return None

            # Get user info from Google
            user_info = await self._get_google_user(access_token)
            if not user_info:
                return None

            # Find or create user
            user = await self._get_or_create_user(
                email=user_info.get("email"),
                name=user_info.get("name", "Google User"),
                avatar_url=user_info.get("picture"),
                oauth_provider="google",
                oauth_id=user_info.get("sub"),
            )

            if not user:
                return None

            # Generate JWT tokens
            jwt_access, jwt_refresh = self.auth_service.generate_tokens(user.id)
            return user, jwt_access, jwt_refresh

        except Exception as e:
            print(f"Google OAuth error: {e}")
            return None

    async def _exchange_google_code(self, code: str) -> Optional[Dict]:
        """Exchange Google auth code for access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.oauth.google_client_id,
                        "client_secret": settings.oauth.google_client_secret,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": settings.oauth.google_redirect_uri,
                    },
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error exchanging Google code: {e}")
        return None

    async def _get_google_user(self, access_token: str) -> Optional[Dict]:
        """Get Google user info"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openidconnect.googleapis.com/v1/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error getting Google user: {e}")
        return None

    # ── User Management ──
    async def _get_or_create_user(
        self,
        email: str,
        name: str,
        avatar_url: Optional[str],
        oauth_provider: str,
        oauth_id: str,
    ) -> Optional[User]:
        """Get existing user or create new one"""
        try:
            # Try to find user by email
            user = self.db.query(User).filter(User.email == email).first()

            if user:
                # Update avatar if provided
                if avatar_url:
                    user.avatar_url = avatar_url
                user.updated_at = datetime.utcnow()
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                return user

            # Create new user
            # For OAuth users, use a placeholder password (never used)
            password_hash = self.auth_service.hash_password(
                f"oauth-{oauth_provider}-{oauth_id}"
            )

            new_user = User(
                email=email,
                password_hash=password_hash,
                name=name,
                avatar_url=avatar_url,
            )

            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)
            return new_user

        except Exception as e:
            print(f"Error creating/updating user: {e}")
            return None

    def get_github_login_url(self) -> str:
        """Get GitHub login URL"""
        return (
            f"https://github.com/login/oauth/authorize?"
            f"client_id={settings.oauth.github_client_id}&"
            f"redirect_uri={settings.oauth.github_redirect_uri}&"
            f"scope=user:email&"
            f"state=qamill"
        )

    def get_google_login_url(self) -> str:
        """Get Google login URL"""
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={settings.oauth.google_client_id}&"
            f"redirect_uri={settings.oauth.google_redirect_uri}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"state=qamill"
        )
