from pydantic import BaseModel, ConfigDict, EmailStr

class IUserCreate(BaseModel):
    name: str | None = None
    username: str
    email: EmailStr
    password: str
    
    
class IUserResponse(BaseModel):
    name: str | None = None
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class IUsersListResponse(BaseModel):
    message: str
    data: list[IUserResponse]
    
    
class IUserLogin(BaseModel):
    username: str
    password: str
    
class IUserLoginData(IUserResponse):
    token: str

class IUsersLoginResponse(BaseModel):
    message: str
    data: IUserLoginData