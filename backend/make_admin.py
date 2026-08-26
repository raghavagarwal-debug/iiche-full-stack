"""
CLI script to promote a user account to Admin role and optionally update their password.
Usage:
    python make_admin.py <user_email> [new_password]
"""

import sys
import asyncio
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.user import User
from app.core.security import hash_password


async def promote_to_admin(email: str, password: str = None):
    email_clean = email.strip().lower()
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.email == email_clean)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ Error: User with email '{email_clean}' not found in database.")
            print("Please create an account on the website first, then run this command again.")
            return

        user.role = "admin"
        user.is_active = True
        if password:
            user.password_hash = hash_password(password)
            print(f"[SUCCESS] Password updated for '{user.email}'!")

        await session.commit()
        print(f"[SUCCESS] User '{user.full_name}' ({user.email}) is now an ADMIN!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <user_email> [new_password]")
        print("Example: python make_admin.py satyamkumar29848@gmail.com mysecretpassword")
        sys.exit(1)

    target_email = sys.argv[1]
    new_pw = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(promote_to_admin(target_email, new_pw))

