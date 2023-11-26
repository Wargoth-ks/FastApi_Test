import sys
import unittest

# sys.path.insert(1, 'fastapi_proj')

from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.source.schemas.users import UserBaseModel
from app.source.db.models import User
from app.source.crud.crud_users import get_user_by_email, create_user, delete_user


class TestCrudUsers(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.async_session = MagicMock(spec=AsyncSession)

    async def test_get_user_by_email(self):
        """
        The test_get_user_by_email function tests the get_user_by_email function.

        :param self: Represent the instance of the object that is passed to the class
                        when you try to create an object of that class
        :return: The test_user object
        """
        # Arrange
        test_email = "test@example.com"
        test_user = User(email=test_email)
        self.async_session.execute.return_value = MagicMock(
            scalar_one=MagicMock(return_value=test_user)
        )

        # Act
        result = await get_user_by_email(test_email, self.async_session)

        # Assert
        self.assertEqual(result, test_user)
        self.async_session.execute.assert_called_once()

    async def test_create_user(self):
        # Arrange
        # Create pydantic model
        user_model = UserBaseModel(
            username="JohnWick",
            email="wick@example.com",
            password="123456",
            avatar="https://www.cloudinary/my_image.jpg",
        )

        # Create object User
        new_user = User(**user_model.model_dump())
        self.async_session.add.return_value = None
        self.async_session.commit.return_value = None
        self.async_session.refresh.return_value = None

        self.async_session.execute.return_value = MagicMock(
            scalar_one=MagicMock(return_value=new_user)
        )

        # Act
        await create_user(user_model, self.async_session)

        email = "wick@example.com"
        test_user = User(email=email)
        result = await get_user_by_email(test_user.email, self.async_session)

        # Asserts
        self.assertIsInstance(user_model, BaseModel)
        self.assertEqual(result.email, new_user.email)
        self.assertIsInstance(new_user, User)
        self.async_session.execute.assert_called_once()

    async def test_delete_user(self):
        # Arrange
        test_email = "wick@example.com"
        test_user = User(email=test_email)
        self.async_session.execute.return_value = MagicMock(
            scalar_one=MagicMock(return_value=test_user)
        )

        # Act
        result = await get_user_by_email(test_email, self.async_session)
        # Assert
        self.assertEqual(result, test_user)
        self.assertIsInstance(result, User)
        self.assertIsNot(result, None)
        self.async_session.execute.assert_called_once()

        # Act
        delete_result = await delete_user(test_email, self.async_session)

        # Assert
        self.assertTrue(delete_result)
        self.async_session.delete.assert_called_once_with(test_user)
        self.async_session.commit.assert_called_once()
        self.async_session.refresh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
