from datetime import datetime, timedelta
from typing import Annotated,Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel ,EmailStr, Field, field_validator
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt

from Database.Database_connection import db_dependency
from Database.Tables import User
from Auth_service.models import create_access_token,CreateUserRequest,bcrypt_context,UserLoginRequest,Token ,validate_password_strength

# Router definition
router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, user: CreateUserRequest):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    validate_password_strength(user.password)
    new_user = User(
        fullname=user.fullname,
        email=user.email,
        hashed_password=bcrypt_context.hash(user.password),
        role=user.role,       
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"User Registered Succesfully"}

@router.post("/login", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, user: UserLoginRequest):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        if not bcrypt_context.verify(user.password, existing_user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password")
        if existing_user.role != user.role:
            raise HTTPException(status_code=404, detail="Not a ")
        access_token = create_access_token(email=existing_user.email, user_id=existing_user.id)
        return Token(access_token=access_token, token_type="bearer",id=existing_user.id)
    else: 
        raise HTTPException(status_code=400, detail="Incorrect Username")   

    
