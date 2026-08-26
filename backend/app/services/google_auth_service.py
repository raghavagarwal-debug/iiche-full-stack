"""
Google OAuth 2.0 service — Section 4.6.
Handles the authorization URL generation, callback verification, and account linking.
"""

import secrets
from urllib.parse import urlencode
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.core.config import settings
from app.core.security import generate_session_token, get_session_expiry, hash_session_token
from app.models.session import Session
from app.models.user import User

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleAuthService:

    @staticmethod
    def get_authorization_url(state: str) -> str:
        """
        Build the Google OAuth authorization URL.
        The state parameter is stored in Redis to prevent CSRF.
        """
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "state": state,
            "prompt": "select_account",
        }
        query = urlencode(params)
        return f"{GOOGLE_AUTH_URL}?{query}"

    @staticmethod
    async def handle_callback(
        db: AsyncSession, code: str
    ) -> tuple[User, str]:
        """
        Exchange the authorization code for user info, create/link the user, return (user, session_token).
        Per Section 4.6: verify server-side, link by verified email, never create duplicates.
        """
        # Exchange code for tokens
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
                if token_response.status_code != 200:
                    raise ValueError("Failed to exchange authorization code")

                tokens = token_response.json()
                access_token = tokens.get("access_token")
                if not access_token:
                    raise ValueError("No access token received")

                # Get user info
                userinfo_response = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if userinfo_response.status_code != 200:
                    raise ValueError("Failed to get user info from Google")

                userinfo = userinfo_response.json()
        except (httpx.HTTPError, ValueError) as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError("Google authentication is temporarily unavailable") from exc

        google_sub = userinfo.get("sub")
        email = userinfo.get("email", "").strip().lower()
        email_verified = userinfo.get("email_verified", False)
        full_name = userinfo.get("name", "")
        picture = userinfo.get("picture")

        if not google_sub or not email or not email_verified:
            raise ValueError("Incomplete Google profile")

        # Try to find existing user by Google subject ID
        result = await db.execute(
            select(User).where(User.google_subject_id == google_sub)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Try to find by email (account linking)
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()

            if user:
                # Link Google to existing account
                user.google_subject_id = google_sub
                if picture and not user.profile_image_url:
                    user.profile_image_url = picture
                if email_verified:
                    user.is_email_verified = True
            else:
                # Create new user from Google profile
                user = User(
                    full_name=full_name,
                    email=email,
                    google_subject_id=google_sub,
                    profile_image_url=picture,
                    is_active=True,
                    is_email_verified=email_verified,
                    role="user",
                )
                db.add(user)
                await db.flush()

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)

        # Create session
        token = generate_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=get_session_expiry(),
        )
        db.add(session)
        await db.commit()
        await db.refresh(user)

        return user, token

    @staticmethod
    def generate_state() -> str:
        """Generate a random state parameter for CSRF protection in OAuth flow."""
        return secrets.token_urlsafe(32)

    @staticmethod
    async def handle_mock_login(
        db: AsyncSession, email: str = "google.user@bitmesra.ac.in", name: str = "Google User"
    ) -> tuple[User, str]:
        """
        Mock Google login for development when Google Client ID is not configured.
        Creates or retrieves a user account linked to Google OAuth.
        """
        google_sub = f"mock_google_{abs(hash(email))}"
        email_clean = email.strip().lower()

        result = await db.execute(
            select(User).where(User.email == email_clean)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                full_name=name,
                email=email_clean,
                google_subject_id=google_sub,
                profile_image_url="https://lh3.googleusercontent.com/a/default-user",
                is_active=True,
                is_email_verified=True,
                role="user",
            )
            db.add(user)
            await db.flush()
        else:
            if not user.google_subject_id:
                user.google_subject_id = google_sub
            user.is_email_verified = True
            await db.flush()

        user.last_login_at = datetime.now(timezone.utc)

        token = generate_session_token()
        session = Session(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=get_session_expiry(),
        )
        db.add(session)
        await db.commit()
        await db.refresh(user)

        return user, token
