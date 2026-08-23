import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.db.engine import AsyncSession
from app.db.models import User
from app.security.password import hash_password


async def main() -> None:
    if not settings.admin_password:
        raise RuntimeError("ADMIN_PASSWORD não configurado")
    async with AsyncSession() as session:
        user = (await session.execute(select(User).where(User.username == settings.admin_username))).scalars().first()
        if user is None:
            raise RuntimeError(f"Usuário {settings.admin_username} não existe")
        user.password_hash = hash_password(settings.admin_password)
        await session.commit()
    print("admin-password-synced")


if __name__ == "__main__":
    asyncio.run(main())