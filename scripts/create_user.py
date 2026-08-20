#!/usr/bin/env python3
"""Create a user in the database. Usage:
python scripts/create_user.py username password [role]
"""
import sys
import asyncio

from app.db.engine import engine, AsyncSession, Base
from app.db.models import User
from app.security.password import hash_password


async def main():
    if len(sys.argv) < 3:
        print("usage: create_user.py username password [role]")
        return
    username = sys.argv[1]
    password = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else "user"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession() as session:
        hashed = hash_password(password)
        user = User(username=username, password_hash=hashed, role=role)
        session.add(user)
        await session.commit()
        print(f"created user {username} with role {role}")


if __name__ == "__main__":
    asyncio.run(main())
