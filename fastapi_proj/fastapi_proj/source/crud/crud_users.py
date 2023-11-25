from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from source.db.models import User
from source.schemas.users import UserBaseModel


async def get_user_by_email(email: str, db: AsyncSession) -> User:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one()
    return user  # type: ignore


async def create_user(body: UserBaseModel, db: AsyncSession) -> User:
    new_user = User(**body.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def update_password(user: User, new_password: str, db: AsyncSession):
    user.password = new_password
    await db.commit()
    await db.refresh(user)


async def update_token(user: User, token: str | None, db: AsyncSession) -> None:
    user.refresh_token = token  # type: ignore
    await db.commit()


async def confirmed_email(email: str, db: AsyncSession):
    user = await get_user_by_email(email, db)
    user.confirmed = True  # type: ignore
    await db.commit()


async def update_avatar(email, url: str | None, db: AsyncSession) -> User:
    user = await get_user_by_email(email, db)
    user.avatar = url # type: ignore
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(email: str, db: AsyncSession):
    user = await get_user_by_email(email, db)
    if user:
        await db.delete(user)
        await db.commit()
    return user
