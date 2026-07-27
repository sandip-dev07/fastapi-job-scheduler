from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel
from typing import List
from starlette.responses import JSONResponse

class EmailSchema(BaseModel):
    email: List[EmailStr]

conf = ConnectionConfig(
    MAIL_USERNAME = "sarkarsandip97740@gmail.com",
    MAIL_PASSWORD = "rmir wtwg ymma vgrk",
    MAIL_FROM = "sarkarsandip97740@gmail.com",
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_FROM_NAME="Sarkar Sandip",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)



async def send_mail(emails: List[str]) -> JSONResponse:
    html = """<p>Hi There, Thanks for signing up</p> """

    message = MessageSchema(
        subject="Registration Onboarding Email",
        recipients=emails ,
        body=html,
        subtype=MessageType.html)

    fm = FastMail(conf)
    await fm.send_message(message)
    return JSONResponse(status_code=200, content={"message": "email has been sent"})