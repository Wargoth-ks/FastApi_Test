import datetime
import sys
import unittest

# sys.path.insert(1, 'fastapi_proj')

from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from fastapi_proj.source.schemas.contacts import ContactBaseModel, ContactSearchUpdateModel, ResponseContactModel
from fastapi_proj.source.db.models import User, Contact
from fastapi_proj.source.crud.crud_contacts import (
    get_contact,
    get_contacts,
    create_contact,
    delete_contact,
    update_contact
)


class TestCrudContacts(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        self.async_session = MagicMock(spec=AsyncSession)
        self.user = User(id=1)
        
    async def test_get_contact(self):
        contact_id = 1
        contact = Contact(id=contact_id)
        
        self.async_session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=contact))
        
        result = await get_contact(contact.id, self.user, self.async_session)
        
        self.assertEqual(result.id, contact_id)
        self.async_session.execute.assert_called_once()
        
    async def test_create_contact(self):
        contact_model = ContactBaseModel(
            name="Name",
            surname="Surname",
            email="user@example.com",
            phone="1234567890",
            birthday=datetime.date(year=2023, month=11, day=15),
        )
        
        new_contact = Contact(**contact_model.model_dump())
        
        self.async_session.add.return_value = None
        self.async_session.commit.return_value = None
        self.async_session.refresh.return_value = None
        
        self.async_session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=new_contact))
        
        await create_contact(contact_model, self.user, self.async_session)
        
        contact_id = 1
        test_contact = Contact(id=contact_id)
        
        result = await get_contact(test_contact.id, self.user, self.async_session)
        
        self.assertIsInstance(contact_model, BaseModel)
        self.assertEqual(result.id, new_contact.id)
        self.assertEqual(result.name, new_contact.name)
        self.assertEqual(result.surname, new_contact.surname)
        self.assertEqual(result.email, new_contact.email)
        self.assertEqual(result.birthday, new_contact.birthday)
        self.assertIsInstance(new_contact, Contact)
        self.assertTrue(hasattr(result, "id"))
        self.async_session.execute.assert_called_once()
        
        
    async def test_get_contacts(self):
        search_model = ContactSearchUpdateModel(
            name="Name",
            surname="Surname",
            email="user@example.com",
            phone="1234567890",
            birthday=datetime.date(year=2023, month=11, day=15),
        )
        search = search_model.model_dump(exclude_none=True)
        
        limit = 10
        offset = 0
        
        contacts = [Contact(
            id=i, 
            name=search["name"], 
            surname=search["surname"],
            email=search["email"],
            phone=search["phone"],
            birthday=search["birthday"],
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
            ) for i in range(10)]

        mock_result = MagicMock()
        mock_result.scalars().all.return_value = contacts
        self.async_session.execute.return_value = mock_result

        result = await get_contacts(search, self.user, self.async_session, limit, offset)

        self.assertEqual(len(result), len(contacts))
        for i, contact in enumerate(result):
            self.assertIsInstance(contact, Contact)
            self.assertIsInstance(search_model, BaseModel)
            response_model = ResponseContactModel.model_validate(contact)
            self.assertEqual(response_model.id, contacts[i].id)
            self.assertEqual(response_model.name, contacts[i].name)
            self.assertEqual(response_model.surname, contacts[i].surname)
            self.assertEqual(response_model.email, contacts[i].email)
            self.assertEqual(response_model.phone, contacts[i].phone)
            self.assertEqual(response_model.birthday, contacts[i].birthday)
            self.assertEqual(response_model.created_at, contacts[i].created_at)
            self.assertEqual(response_model.updated_at, contacts[i].updated_at)
            
    async def test_delete_contact(self):
        contact_id = 1
        test_contact = Contact(id=contact_id)
        self.async_session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=test_contact))
        
        result = await get_contact(contact_id, self.user, self.async_session)
        
        self.assertEqual(result, test_contact)
        self.assertIsInstance(result, Contact)
        self.assertIsNot(result, None)
        self.async_session.execute.assert_called_once()
        
        delete_result = await delete_contact(contact_id, self.user, self.async_session)
        
        self.assertTrue(delete_result)
        self.async_session.delete.assert_called_once_with(test_contact)
        self.async_session.commit.assert_called_once()
        self.async_session.refresh.assert_not_called()
            
    async def test_update_contact(self):
        contact_id = 1
        test_contact = Contact(
            id=contact_id,
            name="name",
            surname="surname",
            email="email@example.com",
            phone="0123456789",
            birthday=datetime.date(year=1999, month=12, day=16),
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        )
        
        self.async_session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=test_contact))
        
        update_model = ContactSearchUpdateModel(
            email="updated_email@example.com",
            phone="0987654321",
            birthday=datetime.date(year=1777, month=7, day=17),
        )
        
        await update_contact(test_contact.id, update_model, self.user, self.async_session)
        
        for field, value in update_model.model_dump(
            exclude_unset=True, exclude_none=True, exclude_defaults=True
            ).items():
            setattr(test_contact, field, value)

        self.async_session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=test_contact))
        
        # Extract data form db
        updated_contact = await get_contact(test_contact.id, self.user, self.async_session)

        # Get data from update model
        update_data = update_model.model_dump(exclude_none=True, exclude_defaults=True, exclude_unset=True)

        # Check if data was updated
        for field in update_data:
            self.assertEqual(getattr(updated_contact, field), getattr(update_model, field))
        
        self.assertIsInstance(updated_contact, Contact)
        
    async def test_update_contact_with_none(self):
        self.async_session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=None))
        
        update_model = ContactSearchUpdateModel(
            name="newname",
            surname="newsurname",
            email="updated_email@example.com",
            phone="0987654321",
            birthday=datetime.date(year=2023, month=12, day=16),
        )
        
        result = await update_contact(1, update_model, self.user, self.async_session)
        
        self.assertIsNone(result)
        

if __name__ == '__main__':
    unittest.main()