from sqlalchemy.ext.asyncio import AsyncSession
from models import User

# POST
async def create_user(db: AsyncSession) -> User:
    user = User()
    db.add(user)
    await db.flush()
    return user