from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from source.db.models import User
from source.schemas.users import UserBaseModel


async def get_user_by_email(email: str, db: AsyncSession):
    """
    The get_user_by_email function takes an email address and a database connection,
    and returns the user with that email address. If no such user exists, it returns None.

    :param email: str: Specify the email of a user
    :param db: AsyncSession: Create a database connection
    :return: A user object
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one()
    return user  # type: ignore


async def create_user(body: UserBaseModel, db: AsyncSession):
    """
    The create_user function creates a new user in the database.

    :param body: UserBaseModel: Validate the data that is passed in
    :param db: AsyncSession: Pass in a database session to the function
    :return: A user object
    """
    new_user = User(**body.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def update_password(user: User, new_password: str, db: AsyncSession):
    """
    The update_password function takes a user object, a new password string, and an async database session.
    It sets the user's password to the new_password string and commits it to the database. It then refreshes
    the user object from the database.

    :param user: User: Specify the user whose password is being updated
    :param new_password: str: Pass the new password to the function
    :param db: AsyncSession: Pass the database session into the function
    :return: None
    """
    user.password = new_password
    await db.commit()
    await db.refresh(user)


async def update_token(user: User, token: str | None, db: AsyncSession):
    """
    The update_token function updates the refresh token for a user.

    :param user: User: Specify the type of the user parameter
    :param token: str | None: Set the refresh token for a user
    :param db: AsyncSession: Commit the changes to the database
    :return: None
    """
    user.refresh_token = token  # type: ignore
    await db.commit()


async def confirmed_email(email: str, db: AsyncSession):
    """
    The confirmed_email function takes an email and a database connection as arguments.
    It then queries the database for the user with that email, and sets their confirmed field to True.

    :param email: str: Get the user's email
    :param db: AsyncSession: Pass the database session to the function
    :return: A boolean
    """
    user = await get_user_by_email(email, db)
    user.confirmed = True  # type: ignore
    await db.commit()


async def update_avatar(email, url: str | None, db: AsyncSession):
    """
    The update_avatar function takes an email and a url, and updates the avatar of the user with that email to be
    the given url. If no user exists with that email, it raises a ValueError.

    :param email: Get the user from the database
    :param url: str | None: Specify that the url parameter can be a string or none
    :param db: AsyncSession: Pass the database session to the function
    :return: A user object
    """
    user = await get_user_by_email(email, db)
    user.avatar = url  # type: ignore
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(email: str, db: AsyncSession):
    """
    The delete_user function takes an email and a database connection as parameters.
    It then queries the database for a user with that email address, and if it finds one,
    it deletes it from the database. It returns either None or the deleted User object.

    :param email: str: Specify the email of the user that we want to delete
    :param db: AsyncSession: Pass in the database session
    :return: The user that was deleted
    """
    user = await get_user_by_email(email, db)
    if user:
        await db.delete(user)
        await db.commit()
    return user
