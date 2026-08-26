"""
Email service — pluggable email sending.
In dev mode, OTPs are logged to console. In production, use a real transactional provider.
Per Section 13: never log OTP values in production.
"""

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailSender(ABC):
    @abstractmethod
    async def send_otp_email(self, to_email: str, otp: str) -> None:
        pass


class ConsoleEmailSender(EmailSender):
    """Development email sender — prints OTP to console."""

    async def send_otp_email(self, to_email: str, otp: str) -> None:
        banner = (
            f"\n============================================================\n"
            f"  [DEV] Password Reset OTP Email to: {to_email}\n"
            f"  [DEV] Your 6-Digit OTP is: {otp}\n"
            f"  [DEV] Valid for {settings.otp_expiry_seconds // 60} minutes\n"
            f"============================================================\n"
        )
        logger.info(banner)
        print(banner, flush=True)


class SendGridEmailSender(EmailSender):
    """SendGrid transactional email sender."""

    async def send_otp_email(self, to_email: str, otp: str) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {settings.email_provider_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": settings.email_from_address, "name": "IIChE BIT Mesra"},
                    "subject": "Your Password Reset OTP — IIChE",
                    "content": [
                        {
                            "type": "text/html",
                            "value": _build_otp_html(otp),
                        }
                    ],
                },
            )
            if response.status_code >= 400:
                logger.error(f"SendGrid error: {response.status_code} — {response.text}")
                raise RuntimeError("Failed to send OTP email")


class ResendEmailSender(EmailSender):
    """Resend transactional email sender."""

    async def send_otp_email(self, to_email: str, otp: str) -> None:
        api_key = settings.effective_email_api_key
        if not api_key:
            if settings.is_production:
                raise RuntimeError("Email delivery is not configured")
            logger.warning("Resend API key missing. Falling back to Console logging.")
            console = ConsoleEmailSender()
            await console.send_otp_email(to_email, otp)
            return

        from_address = settings.email_from_address or "onboarding@resend.dev"

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": f"IIChE BIT Mesra <{from_address}>",
                        "to": [to_email],
                        "subject": "Your Password Reset OTP — IIChE",
                        "html": _build_otp_html(otp),
                    },
                )
                if response.status_code >= 400:
                    if settings.is_production:
                        raise RuntimeError("Failed to send OTP email")
                    logger.warning(
                        f"Resend error ({response.status_code}): {response.text}. "
                        f"Falling back to console OTP logging."
                    )
                    console = ConsoleEmailSender()
                    await console.send_otp_email(to_email, otp)
                    return

                logger.info(f"OTP email sent via Resend to {to_email}")
        except Exception as e:
            if settings.is_production:
                raise RuntimeError("Failed to send OTP email") from e
            logger.warning(
                f"Resend network call failed ({type(e).__name__}: {e}). "
                f"Falling back to console OTP logging."
            )
            console = ConsoleEmailSender()
            await console.send_otp_email(to_email, otp)


def _build_otp_html(otp: str) -> str:
    """Build a simple HTML email body for the OTP."""
    return f"""
    <div style="font-family: 'Outfit', 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
        <h2 style="color: #10b981; margin-bottom: 8px;">IIChE Student Chapter</h2>
        <p style="color: #64748b; margin-bottom: 24px;">BIT Mesra</p>
        <hr style="border: 1px solid #e2e8f0; margin: 16px 0;" />
        <p style="font-size: 16px; color: #334155;">Your password reset OTP is:</p>
        <div style="background: #f0fdf4; border: 2px solid #10b981; border-radius: 12px; padding: 20px; text-align: center; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #064e3b;">{otp}</span>
        </div>
        <p style="font-size: 14px; color: #64748b;">
            This code is valid for <strong>{settings.otp_expiry_seconds // 60} minutes</strong>.
            Do not share it with anyone.
        </p>
        <p style="font-size: 12px; color: #94a3b8; margin-top: 24px;">
            If you didn't request a password reset, please ignore this email.
        </p>
    </div>
    """


def get_email_sender() -> EmailSender:
    """Factory that returns the configured email sender."""
    provider = settings.email_provider.lower()
    if provider == "sendgrid":
        return SendGridEmailSender()
    elif provider == "resend":
        return ResendEmailSender()
    else:
        return ConsoleEmailSender()
