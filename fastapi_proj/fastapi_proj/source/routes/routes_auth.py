import orjson

from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Depends,
    Request,
    status,
    Security,
    BackgroundTasks,
    File,
    UploadFile
)

from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy.ext.asyncio import AsyncSession
from source.db.models import User

from source.crud import crud_users

from source.db.connect_db import get_session

from source.schemas.users import (
    OAuth2Login,
    UserBaseModel,
    UserResponseModel,
    TokenModel,
    RequestEmail,
    UserForgotPasswordForm,
    UserResetPasswordForm,
)

from source.services.auth import auth_service
from source.services.cloudinary_service import cloud
from source.services.mail_service import email_service
from source.services.redis_service import get_redis


router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()


# Register user and sending email for confirmation
@router.post(
    "/signup",
    response_model=UserResponseModel,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account with the provided details",
)
async def signup(
    background_tasks: BackgroundTasks,
    request: Request,
    body: UserBaseModel = Body(...),
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_session)
):
    
    """
    ***Description:***

    This endpoint is used to register a new user. It accepts a JSON body with the user's username, email, and password.
    The password is hashed for security, and a new user is created in the database with these details.
    An optional avatar can be uploaded during registration.
    If the registration is successful, it returns a JSON response with the user's details and a success message.
    An email is also sent to the user for account confirmation.
    """
    
    upload_file = avatar.file    
    url = cloud.upload_image(upload_file, body.username)
    body.avatar = f"{url}" + "/" + f"{avatar.filename}"
    body.password = auth_service.get_password_hash(body.password)

    new_user = await crud_users.create_user(body, db)
    
    background_tasks.add_task(
        email_service.send_email, 
        new_user.email, 
        new_user.username,
        str(request.base_url),
        "confirm_email",
        "Confirm your email",
        "email_template.html"
        )
    
    return {
        "user": new_user,
        "avatar": avatar
    }


# Login user if email was confirmed
@router.post(
    "/login",
    response_model=TokenModel,
    summary="Authenticate a user and return an access and refresh token.",
)
async def login(body: OAuth2Login = Depends(), db: AsyncSession = Depends(get_session)):
    
    """
    ***Description:***

    This endpoint is used to authenticate a user. It accepts form data with the user's email and password.
    The credentials are checked against the database, and if they are valid, 
    a new JWT access token and refresh token are generated for the user.
    These tokens are returned in a JSON response.
    """
    
    user = await crud_users.get_user_by_email(body.username, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Please, confirm your email!"
            )
    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )
    access_token = auth_service.create_access_token(
        data={"sub": user.email}
    )
    refresh_token = auth_service.create_refresh_token(
        data={"sub": user.email}
    )
    await crud_users.update_token(user, refresh_token, db)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# Confirm user email after registration
@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_session)):
    
    """
    ***Description:***
    
    This endpoint is used to confirm a user's email after registration. 
    It accepts a token as a parameter, which is used to verify the user's email.
    If the email is successfully verified, a confirmation message is returned in a JSON response.
    """
    
    email = auth_service.decode_token(token)
    user = await crud_users.get_user_by_email(email, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.confirmed:
        return {"message": "Your email is alredy confirmed"}
    await crud_users.confirmed_email(email, db)
    return {"message": "Email confirmed"}


# Update user access and refresh token with refresh token
@router.get(
    "/refresh_token",
    response_model=TokenModel,
    summary="Refresh the user's access token using their refresh token",
)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_session),
):
    
    """
    ***Description:***

    This endpoint requires a Bearer token to be provided in the Authorization header of the request.
    It decodes this token to get the user's email, 
    then checks if this refresh token is valid for the user in the database.
    If it is valid, it generates a new access token and refresh token 
    for the user and updates these tokens in the database.
    These tokens are returned in a JSON response.
    """
    
    token = credentials.credentials
    email = auth_service.decode_token(token)
    user = await crud_users.get_user_by_email(email, db)
    if user.refresh_token != token:
        await crud_users.update_token(user, None, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    access_token = auth_service.create_access_token(data={"sub": email})
    refresh_token = auth_service.create_refresh_token(data={"sub": email})
    await crud_users.update_token(user, refresh_token, db)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# Logout user with refresh token
@router.get("/logout", summary="Log out a user by revoking their refresh token")
async def logout(
    user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_session),
):
    
    """
    ***Description:***

    This endpoint requires a Bearer token to be provided in the Authorization header of the request.
    It decodes this token to get the user's email, 
    then checks if this refresh token is valid for the user in the database.
    If it is valid, it sets the user's refresh token in the database to None, effectively logging them out.
    It returns a success message in a JSON response.
    """
    
    await crud_users.update_token(user, None, db)
    async with get_redis() as redis:
        key = f"user:{user.email}"
        cache_data = await redis.get(key)
        if cache_data is not None:
            await redis.delete(key)
            print(f"Redis: User cache data for {key} was deleted")
    return "You have logged out successfully"


# Repeat send email for confirmation if user didn't received it
@router.post("/request_email", summary="Check email confirmation")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    
    """
    ***Description:***
    
    This endpoint is used to resend the confirmation email if the user didn't receive it. 
    It accepts a JSON body with the user's email.
    If the user's email is confirmed, a message is returned stating that the email is already confirmed.
    If the user's email is not confirmed, a confirmation email is sent to the user 
    and a message is returned asking the user to check their email for confirmation.
    """
    
    user = await crud_users.get_user_by_email(body.email, db)
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    
    if user:
        background_tasks.add_task(
        email_service.send_email, 
        user.email, 
        user.username,
        str(request.base_url),
        "confirm_email",
        "Confirm your email",
        "email_template.html"
        )
        
    return {"message": "Check your email for confirmation."}


# Send email for reset password
@router.post("/forgot_password", summary="Request for changing password")
async def reset_password(
    background_tasks: BackgroundTasks,
    request: Request,
    body: UserForgotPasswordForm = Depends(),
    db: AsyncSession = Depends(get_session),
):
    
    """
    ***Description:***
    
    This endpoint is used to send a password reset email to the user. It accepts a form with the user's email.
    If the user's email is found in the database, a password reset email is sent to the user.
    A message is returned asking the user to check their email for the password reset link. 
    The user has 15 minutes to reset their password.
    """
    
    user = await crud_users.get_user_by_email(body.email, db)
    if user:
        background_tasks.add_task(
        email_service.send_email, 
        user.email, 
        user.username,
        str(request.base_url),
        "reset_password",
        "Reset your password",
        "reset_password.html"
        )
        
    return {
        "message": "Check your email for reset password. You have 15 minutes for reset!"
    }


# Get reset token for changing password
@router.get("/get_reset_token/{token}", summary="Get token for reset password")
async def get_reset_token(token: str, request: Request, db: AsyncSession = Depends(get_session)):
    
    """
    ***Description:***
    
    This endpoint is used to get a reset token for changing the password. 
    It accepts a token as a parameter, which is used to verify the user's email.
    If the user's email is successfully verified, 
    a reset token is returned in a TemplateResponse with an HTML page.
    """
    
    from main import templates
    
    email = auth_service.decode_token(token)
    user = await crud_users.get_user_by_email(email, db)

    async with get_redis() as redis:
        reset_token = f"reset_token_{user.email}:{token}"
        token_data = await redis.get(reset_token)
        if user:
            if token_data is None:
                serialize_user = orjson.dumps(token)
                await redis.set(reset_token, serialize_user)
                await redis.expire(reset_token, 900)
            # return {"Reset token": token}
            return templates.TemplateResponse("reset_token.html", {"request": request, "token": token})


# Change user password witn reset token
@router.post("/reset_password", summary="Reset password with reset token")
async def confirm_reset_password(
    secret: UserResetPasswordForm = Depends(), db: AsyncSession = Depends(get_session)
):
    
    """
    ***Description:***
    
    This endpoint is used to reset a user's password. 
    It accepts a form with a reset token and the new password.
    The reset token is used to verify the user's 
    email, and if the email is successfully verified, the user's password is updated in the database.
    A success message is returned in a JSON response.
    """
    
    token = secret.reset_token.get_secret_value()
    password = secret.new_password.get_secret_value()

    email = auth_service.decode_token(token)
    user = await crud_users.get_user_by_email(email, db)

    async with get_redis() as redis:
        reset_token = f"reset_token_{user.email}:{token}"
        token_data = await redis.get(reset_token)
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Your password reset token has expired. "
                "Please request a new token to reset your password."
            )
        if user:
            if user.confirmed:
                new_password = auth_service.get_password_hash(password)
                user.password = new_password
                await crud_users.update_password(user, new_password, db)
                await redis.delete(reset_token) # Invalidate reset token
                print(f"\nRedis: Delete {reset_token}\n")
                return {"message": "Password succefuly updated"}
            return user
