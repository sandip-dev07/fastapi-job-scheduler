from fastapi import FastAPI
from starlette.responses import JSONResponse
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import EmailStr, BaseModel
from typing import List
from src.utils.mail import conf as MailConfig

class EmailSchema(BaseModel):
    email: List[EmailStr]

# mail_router = FastAPI(prefix="/mail")


