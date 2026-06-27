"""
Authentication Service - JWT, password hashing, OAuth integration
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from models.database import User
from config.settings import settings
import jwt
import secrets
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service with JWT and password management"""

    def __init__(self, db: Session):
        self.db = db
        self.jwt_secret = settings.auth.jwt_secret
        self.jwt_algorithm = settings.auth.jwt_algorithm
        self.access_token_expire = settings.auth.access_token_expire_minutes
        self.refresh_token_expire = settings.auth.refresh_token_expire_days

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def generate_tokens(self, user_id: str) -> Tuple[str, str]:
        """Generate access and refresh tokens"""
        # Access token (short-lived)
        access_payload = {
            "sub": user_id,
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=self.access_token_expire),
            "iat": datetime.utcnow(),
        }
        access_token = jwt.encode(
            access_payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm,
        )

        # Refresh token (long-lived)
        refresh_payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=self.refresh_token_expire),
            "iat": datetime.utcnow(),
        }
        refresh_token = jwt.encode(
            refresh_payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm,
        )

        return access_token, refresh_token

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None  # Token expired
        except jwt.InvalidTokenError:
            return None  # Invalid token

    def register_user(
        self,
        email: str,
        password: str,
        name: str,
    ) -> Optional[Tuple[User, str, str]]:
        """Register new user"""
        # Check if user exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            return None

        # Hash password
        password_hash = self.hash_password(password)

        # Create user
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Generate tokens
        access_token, refresh_token = self.generate_tokens(user.id)

        return user, access_token, refresh_token

    def login_user(
        self,
        email: str,
        password: str,
    ) -> Optional[Tuple[User, str, str]]:
        """Login user with email and password"""
        # Find user
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None

        # Verify password
        if not self.verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        self.db.add(user)
        self.db.commit()

        # Generate tokens
        access_token, refresh_token = self.generate_tokens(user.id)

        return user, access_token, refresh_token

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Generate new access token from refresh token"""
        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        access_token, _ = self.generate_tokens(user_id)
        return access_token

    def get_user_from_token(self, token: str) -> Optional[User]:
        """Get user from access token"""
        payload = self.verify_token(token)
        if not payload or payload.get("type") != "access":
            return None

        user_id = payload.get("sub")
        user = self.db.query(User).filter(User.id == user_id).first()
        return user

    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> bool:
        """Change user password"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Verify old password
        if not self.verify_password(old_password, user.password_hash):
            return False

        # Update password
        user.password_hash = self.hash_password(new_password)
        self.db.add(user)
        self.db.commit()
        return True

    def reset_password_token(self, user_id: str) -> str:
        """Generate password reset token"""
        payload = {
            "sub": user_id,
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm,
        )
        return token

    def verify_reset_token(self, token: str) -> Optional[str]:
        """Verify password reset token and return user_id"""
        payload = self.verify_token(token)
        if not payload or payload.get("type") != "password_reset":
            return None
        return payload.get("sub")

    def reset_password(self, reset_token: str, new_password: str) -> bool:
        """Reset password using reset token"""
        user_id = self.verify_reset_token(reset_token)
        if not user_id:
            return False

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        user.password_hash = self.hash_password(new_password)
        self.db.add(user)
        self.db.commit()
        return True
