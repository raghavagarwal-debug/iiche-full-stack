"""
Application settings loaded from environment variables.
Uses pydantic-settings for validation and type coercion.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration is loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./iiche_dev.db"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- URLs ---
    environment: str = "development"
    frontend_url: str = "http://localhost:5500"
    backend_url: str = "http://localhost:8000"

    # --- Session ---
    session_secret: str = "CHANGE_ME_TO_A_RANDOM_SECRET"
    session_expire_hours: int = 72

    # --- CSRF ---
    csrf_secret: str = "CHANGE_ME_TO_ANOTHER_RANDOM_SECRET"

    # Mock OAuth is opt-in and must never be enabled in a deployed environment.
    google_mock_login_enabled: bool = False

    # --- Google OAuth 2.0 ---
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # --- Email ---
    email_provider: str = "console"  # "console" | "sendgrid" | "resend"
    email_provider_api_key: str = ""
    resend_api: str = ""
    email_from_address: str = "onboarding@resend.dev"

    @property
    def effective_email_api_key(self) -> str:
        return self.email_provider_api_key or self.resend_api

    # --- OTP ---
    otp_expiry_seconds: int = 600
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 5

    # --- Rate Limiting ---
    rate_limit_login: str = "10/minute"
    rate_limit_password_reset: str = "5/minute"
    rate_limit_signup: str = "5/minute"
    rate_limit_recovery_email: str = "5/minute"  # Per-session limit for recovery email guesses

    # --- Reset Session ---
    reset_session_expiry_seconds: int = 1200  # 20 min total flow timeout
    recovery_email_max_attempts: int = 5  # Max wrong recovery email guesses per session

    # --- Redis Pool ---
    redis_max_connections: int = 50

    # --- Database Pool (per worker — keep low with multiple workers/replicas) ---
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # --- Request Limits ---
    max_request_body_bytes: int = 1_048_576  # 1 MB

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    @property
    def secure_cookies(self) -> bool:
        return self.backend_url.strip().lower().startswith("https://")

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.is_production:
            if self.session_secret.startswith("CHANGE_ME") or self.csrf_secret.startswith("CHANGE_ME"):
                raise ValueError("SESSION_SECRET and CSRF_SECRET must be changed in production")
            if self.google_mock_login_enabled:
                raise ValueError("GOOGLE_MOCK_LOGIN_ENABLED must be false in production")
            if self.email_provider.strip().lower() == "console":
                raise ValueError("EMAIL_PROVIDER=console is not allowed in production")
            if not self.backend_url.strip().lower().startswith("https://"):
                raise ValueError("BACKEND_URL must use HTTPS in production")
        return self

    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        if "sqlite" in self.database_url:
            return self.database_url.replace("sqlite+aiosqlite", "sqlite")
        return self.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")



settings = Settings()
