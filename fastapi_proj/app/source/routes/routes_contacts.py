import orjson
import logging

from fastapi import APIRouter, Body, HTTPException, Depends, status, Query
from fastapi.encoders import jsonable_encoder

from sqlalchemy.ext.asyncio import AsyncSession
from source.db.models import User
from source.services.auth import auth_service
from source.services.redis_service import get_redis

from source.crud import crud_contacts
from source.db.connect_db import get_session
from source.schemas.contacts import (
    ResponseContactModel,
    ContactSearchUpdateModel,
    ContactBaseModel,
    CommonQueryParams,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.post(
    "/",
    response_model=ResponseContactModel,
    status_code=status.HTTP_201_CREATED,
    summary="Create contact",
)
async def add_contact(
    body: ContactBaseModel,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    The add_contact function creates a new contact in the database.
    The function takes in a ContactBaseModel object, which is defined as:

    :param body: ContactBaseModel: Get the contact data from the request body
    :param db: AsyncSession: Pass the database session to the function
    :param current_user: User: Get the current user
    :return: A contactbasemodel
    """
    contact = await crud_contacts.create_contact(body, current_user, db)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid input data"
        )
    return contact


@router.get(
    "/search",
    response_model=list[ResponseContactModel],
    summary="Search for contacts who meet different criteria",
)
async def get_contacts(
    search: ContactSearchUpdateModel = Depends(),
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_session),
    query: CommonQueryParams = Depends(),
):
    """
    The get_contacts function is used to get a list of contacts.

    :param search: ContactSearchUpdateModel: Pass the search parameters to the get_contacts function
    :param current_user: User: Get the current user
    :param db: AsyncSession: Get the database session
    :param query: CommonQueryParams: Get the limit and offset parameters
    :return: A list of contacts
    """
    contacts = await crud_contacts.get_contacts(
        search.model_dump(), current_user, db, query.limit, query.offset
    )
    return contacts


@router.get(
    "/birthdays",
    response_model=list[ResponseContactModel],
    summary="Search for contacts whose birthday is in the next << n >> days",
)
async def get_bd(
    for_days: int = Query(),
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    The get_bd function returns a list of contacts with upcoming birthdays.

    :param for_days: int: Specify how many days in the future to look for birthdays
    :param current_user: User: Get the current user
    :param db: AsyncSession: Get the database session
    :return: A list of contacts with upcoming birthdays
    """
    contacts = await crud_contacts.get_upcoming_birthdays(for_days, current_user, db)
    return contacts


@router.get(
    "/{contact_id}",
    response_model=ResponseContactModel,
    summary="Search for contacts by ID",
)
async def get_contact(
    contact_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    The get_contact function retrieves a contact from the database.

    :param contact_id: int: Define the contact_id as an integer
    :param current_user: User: Get the current user from the auth_service
    :param db: AsyncSession: Pass the database session to the function
    :return: A contact object
    """
    contact = await crud_contacts.get_contact(contact_id, current_user, db)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )

    async with get_redis() as redis:
        cache_key = f"contact_id:{contact_id}"
        cache_data = await redis.get(cache_key)
        if cache_data is not None:
            contact_data = orjson.loads(cache_data)

            logger.info(
                f"\nRedis: Contact data for contact_id: {contact_id} retrieved from Redis cache.\n"
            )

            return contact_data

        contact_dict = jsonable_encoder(contact)
        serialize_contact = orjson.dumps(contact_dict)
        await redis.set(cache_key, serialize_contact)
        await redis.expire(cache_key, 3600)

        logger.info(
            f"\nContact data for contact_id: {contact_id} retrieved from database and set in Redis cache.\n"
        )

    return contact


@router.put(
    "/{contact_id}",
    response_model=ResponseContactModel,
    summary="Partial update of contact information",
)
async def update_contact(
    contact_id: int,
    body: ContactSearchUpdateModel = Body(...),
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    The update_contact function updates a contact in the database and Redis cache.

    :param contact_id: int: Identify the contact to be deleted
    :param body: ContactSearchUpdateModel: Define the data that is passed in the request body
    :param current_user: User: Get the current user who is making the request
    :param db: AsyncSession: Get a database session
    :return: The updated contact object
    """
    contact = await crud_contacts.update_contact(contact_id, body, current_user, db)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    async with get_redis() as redis:
        cache_key = f"contact_id:{contact_id}"
        contact_dict = jsonable_encoder(contact)
        serialize_data = orjson.dumps(contact_dict)
        await redis.set(cache_key, serialize_data)
        await redis.expire(cache_key, 3600)

        logger.info(
            f"\nContact data for contact_id: {contact_id} updated in database and Redis cache.\n"
        )

    return contact


@router.delete(
    "/{contact_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete contact"
)
async def remove_contact(
    contact_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    The remove_contact function deletes a contact from the database.
        It takes in an integer, contact_id, and uses it to find the corresponding
        contact in the database. If no such contact exists, then a 404 error is raised.

    :param contact_id: int: Specify the contact_id of the contact to be deleted
    :param current_user: User: Get the current user
    :param db: AsyncSession: Pass the database session to the function
    :return: The contact that was deleted
    """
    contact = await crud_contacts.delete_contact(contact_id, current_user, db)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found"
        )

    async with get_redis() as redis:
        cache_key = f"contact_id:{contact_id}"
        cache_data = await redis.get(cache_key)
        if cache_data is not None:
            logger.info(
                f"\nRedis: Cache data for contact_id: {contact_id} deleted from Redis cache.\n"
            )

            await redis.delete(cache_key)

    logger.info(f"\nContact {contact_id} deleted from Database.\n")
    return contact
