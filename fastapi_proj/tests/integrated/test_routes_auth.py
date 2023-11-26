import orjson
from httpx import AsyncClient

from io import BytesIO
from unittest.mock import AsyncMock

from fastapi import UploadFile
import pytest
from sqlalchemy import select
from app.source.db.models import User


@pytest.mark.asyncio
async def test_signup(
    client_test: AsyncClient, user: dict, monkeypatch, mock_cloudinary_upload
):
    mock_send_email = AsyncMock()
    monkeypatch.setattr("app.source.routes.routes_auth.email_service", mock_send_email)

    print("=== Start test_signup ===")
    avatar = UploadFile(
        filename="avatar.jpg",
        file=BytesIO(b"This is a test"),
    )

    data = {"body": orjson.dumps(user)}
    files = {"avatar": avatar.file.read()}

    response = await client_test.post("/api/auth/signup", data=data, files=files)

    assert response.status_code == 201, response.text
    received_data = response.json()
    assert received_data["user"]["email"] == user.get("email")
    assert "id" in received_data["user"]


@pytest.mark.asyncio
async def test_repeat_signup(
    client_test: AsyncClient, user: dict, mock_cloudinary_upload
):
    avatar = UploadFile(
        filename="avatar.jpg",
        file=BytesIO(b"This is a test"),
    )

    data = {"body": orjson.dumps(user)}
    files = {"avatar": avatar.file.read()}

    response = await client_test.post("/api/auth/signup", data=data, files=files)

    print(f"\nRepeat Signup: {response}\n")
    assert response.status_code == 409, response.text
    received_data = response.json()
    print(f"\nRepeat: {received_data}\n")
    assert received_data["Detail"] == "Data already exists. Check input data, please"


@pytest.mark.asyncio
async def test_login_user_not_confirmed(client_test: AsyncClient, user: dict):
    response = await client_test.post(
        "/api/auth/login",
        data={"username": user.get("email"), "password": user.get("password")},
    )
    assert response.status_code == 401, response.text
    received_data = response.json()
    assert received_data["detail"] == "Please, confirm your email!"


@pytest.mark.asyncio
async def test_login_user(client_test: AsyncClient, user: dict, create_test_session):
    stmt = select(User).where(User.email == user.get("email"))
    result = await create_test_session.execute(stmt)
    test_user = result.scalar_one()
    test_user.confirmed = True  # type: ignore
    await create_test_session.commit()
    response = await client_test.post(
        "/api/auth/login",
        data={"username": user.get("email"), "password": user.get("password")},
    )
    assert response.status_code == 200, response.text
    received_data = response.json()
    assert "access_token" in received_data
    assert "refresh_token" in received_data
    assert received_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client_test: AsyncClient, user: dict):
    response = await client_test.post(
        "/api/auth/login",
        data={"username": user.get("email"), "password": "password"},
    )
    assert response.status_code == 401, response.text
    received_data = response.json()
    assert received_data["detail"] == "Invalid password"


@pytest.mark.asyncio
async def test_login_wrong_email(client_test: AsyncClient, user: dict):
    response = await client_test.post(
        "/api/auth/login",
        data={"username": "wick@gmail.net", "password": user.get("password")},
    )
    assert response.status_code == 404, response.text
    received_data = response.json()
    assert received_data["Detail"] == "User not found."


@pytest.mark.asyncio
async def test_login_wrong_syntax(client_test: AsyncClient, user: dict):
    response = await client_test.post(
        "/api/auth/login",
        data={"username": "wickgmail.net", "password": user.get("password")},
    )
    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_refresh_token(client_test: AsyncClient, user: dict, create_test_session):
    stmt = select(User).where(User.email == user.get("email"))
    result = await create_test_session.execute(stmt)
    test_user = result.scalar_one()
    refresh_token = test_user.refresh_token  # type: ignore

    response = await client_test.get(
        "/api/auth/refresh_token", headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert response.status_code == 200, response.text
    received_data = response.json()
    assert "access_token" in received_data
    assert "refresh_token" in received_data
    assert received_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_logout(client_test: AsyncClient, login_tokens):
    access_token = login_tokens["access_token"]

    response = await client_test.get(
        "/api/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200, response.text
    received_data = response.json()
    assert received_data == "You have logged out successfully"
