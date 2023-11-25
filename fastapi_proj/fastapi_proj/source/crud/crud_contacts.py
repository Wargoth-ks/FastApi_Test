from sqlalchemy import not_, select, update, func, and_, extract, case, Integer
from source.schemas.contacts import ContactSearchUpdateModel, ContactBaseModel
from source.db.models import Contact, User
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta


async def create_contact(body: ContactBaseModel, user: User, db: AsyncSession):
    contact = Contact(**body.model_dump())
    contact.user_id = user.id
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def get_contacts(
    search: dict, user: User, db: AsyncSession, limit: int, offset: int
):
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
    current_date = datetime.now().date()
    future_date = current_date + timedelta(days=for_days)

    # birthday_this_year = func.date(
    #     func.concat(
    #         extract("year", current_date),  # type: ignore
    #         "-",
    #         extract("month", Contact.birthday),
    #         "-",
    #         extract("day", Contact.birthday),
    #     )
    # )

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
    stmt = select(Contact).where(
        and_(Contact.id == contact_id, Contact.user_id == user.id)
    )
    result = await db.execute(stmt)
    contact = result.scalar_one()
    return contact


async def update_contact(
    contact_id: int, body: ContactSearchUpdateModel, user: User, db: AsyncSession
):
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
    contact = await get_contact(contact_id, user, db)
    if contact:
        await db.delete(contact)
        await db.commit()
    return contact
