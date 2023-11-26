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
    UploadFile,
)

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
    db: AsyncSession = Depends(get_session),
):
    """
    The signup function creates a new user in the database.
    It also uploads the avatar image to cloudinary and saves it's url in the database.
    Finally, it sends an email to confirm that this is indeed your email address.

    :param background_tasks: BackgroundTasks: Add a task to the background queue
    :param request: Request: Get the base url of the request
    :param body: UserBaseModel: Get the user data from the request body
    :param avatar: UploadFile: Upload the avatar image to cloudinary
    :param db: AsyncSession: Get the database session
    :return: A dictionary with the user and avatar
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
        "email_template.html",
    )

    return {"user": new_user, "avatar": avatar}


# Login user if email was confirmed
@router.post(
    "/login",
    response_model=TokenModel,
    summary="Authenticate a user and return an access and refresh token.",
)
async def login(body: OAuth2Login = Depends(), db: AsyncSession = Depends(get_session)):
    """
    The login function is used to authenticate a user.
    It takes the username and password from the body of an HTTP POST request,
    and returns an access token and refresh token if successful.

    :param body: OAuth2Login: Get the username and password from the request body
    :param db: AsyncSession: Get the database session
    :return: A dict with the access token, refresh token and the type of token
    """
    user = await crud_users.get_user_by_email(body.username, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please, confirm your email!",
        )
    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )
    access_token = auth_service.create_access_token(data={"sub": user.email})
    refresh_token = auth_service.create_refresh_token(data={"sub": user.email})
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
    The confirmed_email function is used to confirm a user's email address.
    The function takes the token from the URL and decodes it using auth_service.decode_token().
    It then uses crud_users.get_user_by_email() to get the user with that email address,
    if one exists in our database.
    If no such user exists, we raise an HTTPException with status code 404 (Not Found).
    If there is a matching user but their confirmed field is already True,
    we return a message saying so; otherwise, we use crud_users.confirmed

    :param token: str: Get the token from the url
    :param db: AsyncSession: Pass the database session to the function
    :return: A message to the user that his email is already confirmed
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
    The refresh_token function is used to refresh the access token.
    It takes in a valid refresh token and returns a new access_token and refresh_token pair.
    The old tokens are invalidated.

    :param credentials: HTTPAuthorizationCredentials: Get the token from the request header
    :param db: AsyncSession: Access the database
    :return: An access_token and a refresh_token
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
    The logout function is used to logout a user.
    It takes in the current user and database session as parameters,
    and returns a string indicating that the user has logged out successfully.

    :param user: User: Get the user object from the database
    :param db: AsyncSession: Get a database session
    :return: A string
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
    The request_email function is used to send an email to the user with a link that they can click on
    to confirm their email address. The function takes in a body of type RequestEmail, which contains
    the user's email address. It also takes in background_tasks and request as parameters, which are
    used for sending emails and getting the base url respectively. Finally it takes in db as a parameter,
    which is used for accessing the database.

    :param body: RequestEmail: Validate the request body
    :param background_tasks: BackgroundTasks: Add a task to the background tasks queue
    :param request: Request: Get the base url of the application
    :param db: AsyncSession: Get a database session
    :return: A message to the user
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
            "email_template.html",
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
    The reset_password function is used to reset a user's password.

    :param background_tasks: BackgroundTasks: Add a task to the background queue
    :param request: Request: Get the base_url of the application
    :param body: UserForgotPasswordForm: Get the email from the request body
    :param db: AsyncSession: Get the database session
    :return: A message to the user
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
            "reset_password.html",
        )

    return {
        "message": "Check your email for reset password. You have 15 minutes for reset!"
    }


# Get reset token for changing password
@router.get("/get_reset_token/{token}", summary="Get token for reset password")
async def get_reset_token(
    token: str, request: Request, db: AsyncSession = Depends(get_session)
):
    """
    The get_reset_token function is used to get a reset token for the user.
    The function takes in a token and request as parameters, and returns an HTML response.

    :param token: str: Get the token from the url
    :param request: Request: Get the request object
    :param db: AsyncSession: Get the database session
    :return: A reset token
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
            return templates.TemplateResponse(
                "reset_token.html", {"request": request, "token": token}
            )


# Change user password witn reset token
@router.post("/reset_password", summary="Reset password with reset token")
async def confirm_reset_password(
    secret: UserResetPasswordForm = Depends(), db: AsyncSession = Depends(get_session)
):
    """
    The confirm_reset_password function is used to confirm a user's password reset request.
    It takes in the secret token that was sent to the user's email address and uses it to
    retrieve their account information from the database. It then updates their password with
    the new one provided by them.

    :param secret: UserResetPasswordForm: Get the reset token and new password
    :param db: AsyncSession: Get a database session
    :return: A message when the password is reset
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
                "Please request a new token to reset your password.",
            )
        if user:
            if user.confirmed:
                new_password = auth_service.get_password_hash(password)
                user.password = new_password
                await crud_users.update_password(user, new_password, db)
                await redis.delete(reset_token)  # Invalidate reset token
                print(f"\nRedis: Delete {reset_token}\n")
                return {"message": "Password succefuly updated"}
            return user
