"""Run the configured initial administrator bootstrap manually.

Usage from backend/: ``python seed_admin.py``
The normal production startup runs this same operation automatically.
"""

import asyncio

from app.db.session import async_session_factory, engine
from app.services.bootstrap_service import ensure_initial_admin


async def main() -> None:
    async with async_session_factory() as session:
        user = await ensure_initial_admin(session)
        if user:
            print(f"Initial administrator is present: {user.email} (role={user.role})")
        else:
            print("Initial administrator seed skipped; configure INITIAL_ADMIN_* first.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
