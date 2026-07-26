from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from src.utils.db import get_db
from src.interfaces.users import IUserCreate, IUsersListResponse, IUserLogin, IUsersLoginResponse
from src.models.users import User as UserModel
from src.utils.helper import ALGORITHM, SECRET_KEY, is_autheticated
from sqlalchemy.exc import SQLAlchemyError
import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from datetime import datetime, timedelta

# Security
ACCESS_TOKEN_EXPIRE_MINUTES = 30

password_hash = PasswordHash.recommended()
def get_password_hash(password):
    return password_hash.hash(password)

# Routers
users_router = APIRouter(prefix="/users")

@users_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: IUserCreate, db: Session = Depends(get_db)):
    
    try:
        # username validation
        if db.query(UserModel).filter(UserModel.username == body.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        # email validation
        if db.query(UserModel).filter(UserModel.email == body.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        # password validation + hashing
        if len(body.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        
        user = UserModel(**body.model_dump())
        user.password = get_password_hash(user.password)
        
        db.add(user)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    return {
        "message": "User created successfully",
        "data": user
    }
    

@users_router.get("/", response_model=IUsersListResponse, status_code=status.HTTP_200_OK)
async def get_users(db: Session = Depends(get_db)):
    
    users = db.query(UserModel).all()
    
    return {
        "message": "Users fetched successfully",
        "data": users
    }
    

@users_router.post("/login", response_model=IUsersLoginResponse, status_code=status.HTTP_200_OK)
async def login(
    body: IUserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    
    try:
        user = db.query(UserModel).filter(UserModel.username == body.username).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    
        if not password_hash.verify(body.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid password")
        
        token  = jwt.encode({
            "_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "exp": datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }, SECRET_KEY, algorithm=ALGORITHM)

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax",
            secure=False,
        )
        
    except UnknownHashError:
        raise HTTPException(status_code=401, detail="Stored password hash is invalid")
    
    return {
        "message": "User logged in successfully",
        "data": {
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "token": token,
        }
    }

# protected route:
@users_router.get("/test_protected_route", status_code=status.HTTP_200_OK)
async def me(current_user: UserModel = Depends(is_autheticated)):
    return {
        "message": "Authenticated user fetched successfully",
        "data": {
            "name": current_user.name,
            "username": current_user.username,
            "email": current_user.email,
        }
    }
