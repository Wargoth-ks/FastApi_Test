import logging
from fastapi import HTTPException, status, APIRouter, Depends, File, UploadFile
from fastapi.encoders import jsonable_encoder
import orjson

from source.db.models import User
from source.schemas.users import UserDBModel
from source.services.auth import auth_service
from source.db.connect_db import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from source.crud import crud_users
from source.services.cloudinary_service import cloud
from source.services.redis_service import get_redis
import cloudinary.exceptions as cloud_exc

router = APIRouter(prefix="/users", tags=["Users"])


# Get current user's data profile
@router.get("/my_profile", response_model=UserDBModel)
async def get_profile(current_user: User = Depends(auth_service.get_current_user)):
    """
    The get_profile function returns the profile of a user.
    The function takes in an optional parameter, current_user, which is a User object.
    If no user is passed into the function, it will attempt to get one from auth_service.get_current_user().
    If that fails (i.e., if there's no logged-in user),
    then it raises an HTTPException with status code 404 and detail "User not found".

    :param current_user: User: Pass in the current user
    :return: The current user object
    :doc-author: Trelent
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return current_user


# Update user's avatar
@router.patch("/update_avatar", response_model=UserDBModel)
async def update_avatar(
    avatar: UploadFile = File(),
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    The update_avatar function allows a user to update their avatar.

    :param avatar: UploadFile: Get the file from the request
    :param current_user: User: Get the current user's email
    :param db: AsyncSession: Get the database session
    :return: A user object with the updated avatar url
    """
    try:
        upload_file = avatar.file
        url = cloud.upload_image(upload_file, current_user.username)
        updated_avatar = f"{url}" + "/" + f"{avatar.filename}"
        user = await crud_users.update_avatar(current_user.email, updated_avatar, db)

        async with get_redis() as redis:
            cache_key = f"user:{user.email}"
            user_dict = jsonable_encoder(user)
            user_dict.pop(
                "refresh_token"
            )  # exclude refresh_token value for security reasons
            serialize_data = orjson.dumps(user_dict)
            await redis.set(cache_key, serialize_data)
            await redis.expire(cache_key, 900)
        return user
    except cloud_exc.Error:
        raise HTTPException(
            status_code=408, detail="Request timeout. Please, try again"
        )


# Delete user's profile
@router.delete("/delete_profile", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    The delete_profile function deletes the user's profile from the database
    and removes their avatar image from Cloudinary.
    It also deletes any cached data for that user in Redis.

    :param current_user: User: Get the current user from the database
    :param db: AsyncSession: Get a database session
    :return: A user object
    """
    try:
        avatar = current_user.username
        cloud.delete_image(avatar)
        user = await crud_users.delete_user(current_user.email, db)
        async with get_redis() as redis:
            cache_key = f"user:{current_user.email}"
            cache_data = await redis.get(cache_key)
            if cache_data is not None:
                logging.info(
                    f"\nRedis: Cache data for user: {current_user.email} deleted from Redis cache.\n"
                )
                await redis.delete(cache_key)

        return user
    except cloud_exc.Error:
        raise HTTPException(
            status_code=408, detail="Request timeout. Please, try again"
        )
