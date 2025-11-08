from sqlalchemy.ext.asyncio import AsyncSession
from models import User

# POST
async def create_user(db: AsyncSession, role: str) -> User:
    user = User(role=role)
    db.add(user)
    await db.flush()
    return user