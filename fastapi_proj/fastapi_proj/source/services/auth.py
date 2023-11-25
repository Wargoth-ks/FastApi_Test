import orjson

from typing import Optional
from datetime import datetime, timedelta

from fastapi import HTTPException, status, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordBearer

from passlib.context import CryptContext
from jose import JWTError, jwt

from sqlalchemy.ext.asyncio import AsyncSession
from source.db.models import User

from source.db.connect_db import get_session
from source.crud import crud_users
from source.services.redis_service import get_redis

from source.conf.configs import settings


class Auth:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    SECRET_KEY = settings.SECRET_KEY
    ALGORITHM = settings.ALGORITHM
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", scheme_name="JWT")

    credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        return self.pwd_context.hash(password)

    # Define a function to generate a new access token
    def create_access_token(
        self, data: dict, expires_delta: Optional[float] = None
    ):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + timedelta(seconds=expires_delta)
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update(
            {"iat": datetime.utcnow(), "exp": expire, "scope": "access_token"}
        )
        encoded_access_token = jwt.encode(
            to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM
        )
        return encoded_access_token

    # Define a function to generate a new refresh token
    def create_refresh_token(
        self, data: dict, expires_delta: Optional[float] = None
    ):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + timedelta(seconds=expires_delta)
        else:
            expire = datetime.utcnow() + timedelta(days=7)
        to_encode.update(
            {"iat": datetime.utcnow(), "exp": expire, "scope": "refresh_token"}
        )
        encoded_refresh_token = jwt.encode(
            to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM
        )
        return encoded_refresh_token

    # Define a function to generate a new email token
    def create_email_token(self, data: dict, purpose: str):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"iat": datetime.utcnow(), "exp": expire, "scope": purpose})
        token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return token

    # Decode refresh/email/reset token
    def decode_token(self, token: str):
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if (
                payload["scope"] == "refresh_token"
                or payload["scope"] == "confirm_email"
                or payload["scope"] == "reset_password"
            ):
                email = payload["sub"]
                return email
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid {payload.get('scope')} verification",
            )
        except JWTError:
            raise self.credentials_exception

    # Decode access token and save data to redis cache
    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_session),
    ):

        try:
            # Decode access token
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload["scope"] == "access_token":
                email = payload["sub"]
                if email is None:
                    raise self.credentials_exception
            else:
                raise self.credentials_exception
        except JWTError:
            raise self.credentials_exception
        
        user = await crud_users.get_user_by_email(email, db)  # return Class
        if user is None:
            raise self.credentials_exception
        
        # Save data to Redis cache
        async with get_redis() as redis:
            key = f"user:{user.email}"
            print(key)
            cache_data = await redis.get(key)
            if cache_data is not None:
                user_data_dict = orjson.loads(cache_data)
                user_data = User(**user_data_dict)
                print(f"\nRedis get by email: {key} retrived from Redis cache\n")
                return user_data
            user_dict = jsonable_encoder(user)
            user_dict.pop("refresh_token") # exclude refresh_token value for security reasons
            serialize_data = orjson.dumps(user_dict) # return dict
            await redis.set(key, serialize_data)
            await redis.expire(key, 900)
            print(f"\nRedis get by email: {key} retrived from Database and set into Redis cache\n")
            
        return user


auth_service = Auth()
