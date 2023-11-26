import sys

import asyncio
import pytest

from httpx import AsyncClient
from unittest.mock import MagicMock, patch

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine

# Why this import make tests succefull????
from source.db.connect_db import get_session

from app.main import fast_app

# from source.services.redis_service import get_redis

from app.source.db.models import Base
from app.source.conf.configs import settings


url = settings.TEST_SQLALCHEMY_DATABASE_URL_LOCAL

test_engine = create_async_engine(url, echo=True)

test_session = async_sessionmaker(
    class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)


@pytest.fixture(scope="session")
def event_loop(request):
    """
    The event_loop function is a pytest fixture that creates an event loop
    and passes it to the test function. The event loop is closed after the test
    has run. This allows us to use asyncio coroutines in our tests.

    :param request: Pass the request object to the event loop
    :return: A context manager that returns an event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def create_test_engine():
    """
    The create_test_engine function is a fixture that creates an engine for testing purposes.
    It will create the tables in the database, and then drop them when it's done.

    :return: A test_engine object
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture(scope="function", autouse=True)
async def create_test_session(create_test_engine):
    """
    The create_test_session function is a fixture that creates a new database session for each test.
    It also rolls back the transaction after each test,
    and closes the connection to the database when it's done.

    :param create_test_engine: Create a new engine for the test session
    :return: A context manager that can be used to create a test session
    """
    async with test_session(bind=test_engine) as session:
        try:
            yield session
        except Exception:
            await session.rollback()
        finally:
            await session.close()


@pytest.fixture(scope="function", autouse=True)
async def client_test(create_test_session):
    """
    The client_test function is a fixture that allows us to test our API endpoints.
    It creates an AsyncClient object, which we can use to make requests against the
    API and get responses back. The client_test function takes in a create_test_session
    parameter, which is used by the override_get_session function to return a mock session
    object for testing purposes.

    :param create_test_session: Create a test session
    :return: A client that is ready to make requests
    """

    async def override_get_session():
        yield create_test_session

    fast_app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(app=fast_app, base_url="http://test_client") as as_cl:
        yield as_cl


# @pytest.fixture(scope="module")
# async def mock_redis():
#     with patch('fastapi_proj.main.get_redis') as mock_get_redis:
#         mock_redis_instance = MagicMock()
#         mock_get_redis.return_value.__aenter__.return_value = mock_redis_instance
#         yield mock_redis_instance


def mock_upload_image(file, public_id, **kwargs):
    """
    The mock_upload_image function is a mock function that simulates the behavior
    of the upload_image function from cloudinary.uploader.
    It returns a dictionary with all the keys and values
    that are returned by cloudinary's upload_image function.

    :param file: Pass the file to be uploaded
    :param public_id: Specify the name of the image in cloudinary
    :param **kwargs: Capture any additional parameters that are passed into the function
    :return: A dictionary with the following keys:
    """
    return {
        "public_id": public_id,
        "version": "123456",
        "signature": "abcdef1234567890",
        "width": 200,
        "height": 200,
        "format": "jpg",
        "resource_type": "image",
        "created_at": "2023-12-01T12:00:00Z",
        "bytes": 12345,
        "type": "upload",
        "url": "https://res.cloudinary.com/dcbpbf8vv/c_fill,g_face,h_250,r_max,w_250/fast_api_users/JohnWick/avatar.jpg",
        "secure_url": "https://res.cloudinary.com/dcbpbf8vv/c_fill,g_face,h_250,r_max,w_250/fast_api_users/JohnWick/avatar.jpg",
    }


@pytest.fixture(scope="function")
def mock_cloudinary_upload():
    """
    The mock_cloudinary_upload function is a context manager that patches
    the cloudinary.uploader.upload function with
    the mock_upload_image function, and yields the mock object to allow for assertions on it.

    :return: The mock_upload_image function
    """
    with patch("cloudinary.uploader.upload", new=mock_upload_image) as _mock:
        yield _mock


@pytest.fixture(scope="module")
def user():
    """
    The user function is used to create a user model for testing purposes.

    :return: A dictionary
    """
    user_model = {
        "username": "JohnWick",
        "email": "wickwick@gmail.com",
        "password": "123456",
        "avatar": "string",
    }

    return user_model


@pytest.fixture()
async def login_tokens(client_test: AsyncClient, user: dict):
    """
    The login_tokens function is used to log in a user and return the tokens.

    :param client_test: AsyncClient: Create a client for testing
    :param user: dict: Pass in the user dictionary that we created earlier
    :return: A dictionary with two keys:
    """
    response = await client_test.post(
        "/api/auth/login",
        data={"username": user.get("email"), "password": user.get("password")},
    )
    tokens = response.json()
    return tokens
