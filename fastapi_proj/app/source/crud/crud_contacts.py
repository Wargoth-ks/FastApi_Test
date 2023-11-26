from sqlalchemy import not_, select, update, func, and_, extract, case, Integer
from source.schemas.contacts import ContactSearchUpdateModel, ContactBaseModel
from source.db.models import Contact, User
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta


async def create_contact(body: ContactBaseModel, user: User, db: AsyncSession):
    """
    The create_contact function creates a new contact in the database.

    :param body: ContactBaseModel: Pass the contact data to the function
    :param user: User: Get the user_id for the contact
    :param db: AsyncSession: Pass the database session into the function
    :return: A contact object

    """
    contact = Contact(**body.model_dump())
    contact.user_id = user.id
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def get_contacts(
    search: dict, user: User, db: AsyncSession, limit: int, offset: int
):
    """
    The get_contacts function is used to retrieve a list of contacts from the database.
    The function takes in a search dictionary, user object, database session object,
    limit integer and offset integer as parameters.
    The search dictionary contains key value pairs
    that are used to filter the results returned by the query.
    The keys are column names and values are column values for filtering purposes.
    If no filters exist then all contacts will be returned for that user (user_id).
    The limit parameter specifies how many records should be retrieved
    at most while offset specifies where in the result set we should start retrieving records from.

    :param search: dict: Filter the contacts by name, phone number, or email
    :param user: User: Get the user id of the logged in user
    :param db: AsyncSession: Pass the database session into the function
    :param limit: int: Limit the number of contacts returned
    :param offset: int: Specify the number of records to skip before returning results
    :return: A list of contacts
    """
    stmt = (
        select(Contact)
        .where(Contact.user_id == user.id)
        .order_by(Contact.id.asc())
        .limit(limit)
        .offset(offset)
    )
    for key, value in search.items():
        if value is not None:
            stmt = stmt.where(getattr(Contact, key) == value)
    result = await db.execute(stmt)
    contacts = result.scalars().all()
    return contacts


async def get_upcoming_birthdays(for_days: int, user: User, db: AsyncSession):
    """
    The get_upcoming_birthdays function returns a list of contacts with upcoming birthdays.

    :param for_days: int: Determine how many days in the future we want to look for birthdays
    :param user: User: Get the user's id from the database
    :param db: AsyncSession: Create a database connection
    :return: A list of contacts with upcoming birthdays

    """
    current_date = datetime.now().date()
    future_date = current_date + timedelta(days=for_days)

    year = extract("year", current_date).cast(Integer)  # type: ignore
    month = extract("month", Contact.birthday)
    day = extract("day", Contact.birthday)

    is_leap_year = year % 4 == 0
    is_feb_29 = and_(month == 2, day == 29)
    day = case({is_feb_29: case({not_(is_leap_year): 28}, else_=day)}, else_=day)

    birthday_this_year = func.date(func.concat(year, "-", month, "-", day))

    stmt = (
        select(Contact)
        .where(Contact.user_id == user.id)
        .where(
            and_(birthday_this_year >= current_date, birthday_this_year <= future_date)
        )
        .order_by(birthday_this_year)
    )
    result = await db.execute(stmt)
    users_with_upcoming_birthday = result.scalars().all()
    return users_with_upcoming_birthday


async def get_contact(contact_id: int, user: User, db: AsyncSession):
    """
    The get_contact function is used to retrieve a contact from the database.
    It takes in an integer representing the id of the contact, a user object, and
    a database session as parameters. It then creates an SQLAlchemy statement that
    selects all columns from Contact where both the id matches that of what was passed
    in and where it belongs to this particular user (as determined by their ID).
    The result of this query is then stored in a variable called 'result'.
    Finally, we return only one row from our result set using scalar_one().
    This function returns either None or an instance of Contact.&quot;

    :param contact_id: int: Specify the id of the contact we want to get
    :param user: User: Get the user id from the user object
    :param db: AsyncSession: Pass in the database session
    :return: A contact object
    """
    stmt = select(Contact).where(
        and_(Contact.id == contact_id, Contact.user_id == user.id)
    )
    result = await db.execute(stmt)
    contact = result.scalar_one()
    return contact


async def update_contact(
    contact_id: int, body: ContactSearchUpdateModel, user: User, db: AsyncSession
):
    """
    The update_contact function updates a contact in the database.

    :param contact_id: int: Identify the contact to be updated
    :param body: ContactSearchUpdateModel: Pass in the data that is being updated
    :param user: User: Ensure that the user is authenticated
    :param db: AsyncSession: Pass the database session to the function
    :return: The contact object
    """
    contact = await get_contact(contact_id, user, db)
    if contact is None:
        return None
    update_data = body.model_dump(
        exclude_none=True, exclude_defaults=True, exclude_unset=True
    )
    await db.execute(
        update(Contact).where(Contact.id == contact_id).values(**update_data)
    )
    await db.commit()
    await db.refresh(contact)
    return contact


async def delete_contact(contact_id: int, user: User, db: AsyncSession):
    """
    The delete_contact function deletes a contact from the database.

    :param contact_id: int: Specify the id of the contact to delete
    :param user: User: Ensure that the user is authorized to delete this contact
    :param db: AsyncSession: Pass the database session into the function
    :return: The contact that was deleted
    """
    contact = await get_contact(contact_id, user, db)
    if contact:
        await db.delete(contact)
        await db.commit()
    return contact
