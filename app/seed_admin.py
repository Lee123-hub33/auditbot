# app/seed_admin.py
import asyncio
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import User, UserRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "admin@auditbot.com"))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email="admin@auditbot.com",
                hashed_password=pwd_context.hash("Admin@2026"),
                full_name="Admin User",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            print("✓ Admin user created")
        else:
            user.role = UserRole.ADMIN
            await db.commit()
            print("✓ Existing user promoted to admin")

asyncio.run(seed())