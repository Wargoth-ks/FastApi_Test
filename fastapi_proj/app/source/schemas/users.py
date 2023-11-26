from datetime import datetime
from typing import Annotated, Optional
from fastapi import Form
from fastapi.security import OAuth2PasswordRequestForm
import orjson
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)


class UserBaseModel(BaseModel):
    username: str = Field(min_length=2, max_length=50, examples=["Name"])
    email: EmailStr = Field(min_length=5, max_length=50)
    password: str = Field(min_length=6, max_length=80, examples=["0123456789"])
    avatar: Optional[str] = None

    @field_validator("username", mode="before")
    def check_name(cls, value):
        if not value.isalpha():
            raise ValueError("Username must contain only letters")
        return value

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_to_json

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**orjson.loads(value))
        return value


class UserDBModel(BaseModel):
    id: int
    username: str
    email: EmailStr
    avatar: Optional[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponseModel(BaseModel):
    user: UserDBModel
    detail: str = "User successfully created. Please, check your emailbox for confirm registration"


class OAuth2Login(OAuth2PasswordRequestForm):
    def __init__(
        self,
        *,
        username: Annotated[EmailStr, Form(...)],
        password: Annotated[SecretStr, Form(...)],
    ):
        super().__init__(
            username=username,
            password=password.get_secret_value(),
        )


class UserForgotPasswordForm:
    def __init__(self, email: EmailStr = Form(...)):
        self.email = email


class UserResetPasswordForm:
    def __init__(
        self,
        reset_token: SecretStr = Form(...),
        new_password: SecretStr = Form(..., min_length=6, max_length=80),
    ):
        self.reset_token = reset_token
        self.new_password = new_password


class TokenModel(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RequestEmail(BaseModel):
    email: EmailStr
