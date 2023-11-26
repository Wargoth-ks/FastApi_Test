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
        """
        The verify_password function takes in a plain_password and hashed_password.
        It then uses the pwd_context to verify that the plain password matches the hashed password.

        :param self: Make the function a method of the user class
        :param plain_password: Store the password that is entered by the user
        :param hashed_password: Check if the password is correct
        :return: A boolean
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        """
        The get_password_hash function takes a password and returns the hashed version of it.
        The hashing algorithm is defined in the config file, which is passed to CryptContext.

        :param self: Represent the instance of the class
        :param password: str: Pass in the password that will be hashed
        :return: The hashed password
        """
        return self.pwd_context.hash(password)

    # Define a function to generate a new access token
    def create_access_token(self, data: dict, expires_delta: Optional[float] = None):
        """
        The create_access_token function creates a new access token.
        The function takes in the data to be encoded, and an optional expires_delta parameter.
        If no expires_delta is provided, the default value of 15 minutes will be used.
        The function then encodes the data using JWT with our SECRET_KEY and ALGORITHM.

        :param self: Make methods callable on an instance of the class
        :param data: dict: Pass the data to be encoded in the token
        :param expires_delta: Optional[float]: Set the expiration time of the access token
        :return: A jwt access token
        """
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
    def create_refresh_token(self, data: dict, expires_delta: Optional[float] = None):
        """
        The create_refresh_token function creates a refresh token for the user.
        The function takes in three arguments: self, data, and expires_delta.
        The self argument is the class itself (OAuth2PasswordBearer).
        The data argument is a dictionary containing information about the user's session. 
        This includes their username and password hash as well as other information 
        such as their id number and email address. 
        It also contains an iat key which stands for "issued at" 
        time which indicates when this token was created by using datetime 
        to get the current UTC time (datetime.utcnow()).
        
        The expires_delta argument is an optional parameter that sets the expiration time 
        of the refresh token.
        If no value is provided, the default expiration time is 7 days from the current UTC time.
        
        The function then updates the data dictionary with the issued at time, expiration time, and scope.
        It encodes this updated data into a refresh token using the jwt.encode method 
        and the class's secret key and algorithm.

        :param self: Make the function a method of the class
        :param data: dict: Pass in the user's id, which is used to identify the user
        :param expires_delta: Optional[float]: Set the expiration time of the refresh token
        :return: A refresh token
        """
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
        """
        The create_email_token function creates a token that is used to verify the user's email address.

        :param self: Represent the instance of the class
        :param data: dict: Pass in the data that will be encoded
        :param purpose: str: Specify the purpose of the token
        :return: A token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"iat": datetime.utcnow(), "exp": expire, "scope": purpose})
        token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return token

    # Decode refresh/email/reset token
    def decode_token(self, token: str):
        """
        The decode_token function is used to decode the token that was sent by the user.
        The function will check if the token is valid and then return an email address.
        If it's not a valid token, it will raise an exception.

        :param self: Represent the instance of the class
        :param token: str: Pass in the token that is being decoded
        :return: The email of the user who requested a token
        """
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
        """
        The get_current_user function is a dependency that will be used in the
        protected routes. It takes an access token as an argument and returns the user
        associated with that token. If no user is found, it raises a HTTPException with
        status code 401 (Unauthorized).

        :param self: Represent the instance of the class
        :param token: str: Get the token from the authorization header
        :param db: AsyncSession: Get the database connection
        :return: The user object
        """
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
            user_dict.pop(
                "refresh_token"
            )  # exclude refresh_token value for security reasons
            serialize_data = orjson.dumps(user_dict)  # return dict
            await redis.set(key, serialize_data)
            await redis.expire(key, 900)
            print(
                f"\nRedis get by email: {key} retrived from Database and set into Redis cache\n"
            )

        return user


auth_service = Auth()
