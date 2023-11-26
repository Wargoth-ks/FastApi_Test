from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr

from source.services.auth import auth_service
import logging

from pathlib import Path
from source.conf.configs import settings


logger = logging.getLogger("uvicorn")


email_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent / "../../front/templates",
)


class EmailService:
    def __init__(self, email_config):
        self.email_config = email_config
        self.fm = FastMail(email_config)

    async def send_email(
        self,
        email: EmailStr,
        username: str,
        host: str,
        token_purpose: str,
        subject: str,
        template: str,
    ):
        """
        The send_email function is used to send emails to users.

        :param self: Represent the instance of the class
        :param email: EmailStr: Validate the email address
        :param username: str: Pass in the username of the user who is receiving an email
        :param host: str: Pass the host of the application to the email template
        :param token_purpose: str: Specify the purpose of the token
        :param subject: str: Set the subject of the email
        :param template: str: Specify the name of the template that will be used to send the email
        :return: The message that was sent
        """
        try:
            token = auth_service.create_email_token({"sub": email}, token_purpose)
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                template_body={
                    "host": host,
                    "username": username,
                    "token": token,
                },
                subtype=MessageType.html,
            )

            await self.fm.send_message(message, template_name=template)
        except ConnectionErrors as e:
            logger.error(f"Something went wrong in {subject} email notification")
            logger.error(str(e))


email_service = EmailService(email_config)
