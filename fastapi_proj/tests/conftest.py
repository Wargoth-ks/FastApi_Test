import asyncio
import pytest

from httpx import AsyncClient
from unittest.mock import MagicMock, patch

from sqlalchemy.ext.asyncio import (
    async_sessionmaker, AsyncSession, create_async_engine
    )
from source.db.connect_db import get_session
from fastapi_proj.main import fast_app
# from source.services.redis_service import get_redis

from source.db.models import Base
from source.conf.configs import settings


url = settings.TEST_SQLALCHEMY_DATABASE_URL_LOCAL

test_engine = create_async_engine(
        url, echo=True
        ) 

test_session = async_sessionmaker(
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def create_test_engine():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()

    
@pytest.fixture(scope="function", autouse=True)
async def create_test_session(create_test_engine):
    async with test_session(bind=create_test_engine) as session:
        try:
            yield session
        except Exception:
            await session.rollback()
        finally:
            await session.close()


@pytest.fixture(scope="function", autouse=True)
async def client_test(create_test_session):
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
    return {
        'public_id': public_id,
        'version': '123456',
        'signature': 'abcdef1234567890',
        'width': 200,
        'height': 200,
        'format': 'jpg',
        'resource_type': 'image',
        'created_at': '2023-12-01T12:00:00Z',
        'bytes': 12345,
        'type': 'upload',
        'url': "https://res.cloudinary.com/dcbpbf8vv/c_fill,g_face,h_250,r_max,w_250/fast_api_users/JohnWick/avatar.jpg",
        'secure_url': "https://res.cloudinary.com/dcbpbf8vv/c_fill,g_face,h_250,r_max,w_250/fast_api_users/JohnWick/avatar.jpg"
    }


@pytest.fixture(scope="function")
def mock_cloudinary_upload():
    with patch('cloudinary.uploader.upload', new=mock_upload_image) as _mock:
        yield _mock


@pytest.fixture(scope="module")
def user():
    user_model = {
        "username": "JohnWick",
        "email": "wickwick@gmail.com",
        "password": "123456",
        "avatar": "string"
    }

    return user_model

@pytest.fixture()
async def login_tokens(client_test: AsyncClient, user: dict):
    response = await client_test.post(
        "/api/auth/login",
        data={"username": user.get('email'), "password": user.get('password')},
    )
    tokens = response.json()
    return tokens