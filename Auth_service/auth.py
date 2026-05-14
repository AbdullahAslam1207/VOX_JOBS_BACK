from datetime import datetime, timedelta
from typing import Annotated,Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel ,EmailStr, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt

from Database.Database_connection import db_dependency
from Database.Tables import User
from Auth_service.models import (
    CreateUserRequest,
    Token,
    UpdatePasswordRequest,
    UpdateUserProfileRequest,
    UserLoginRequest,
    UserListItemResponse,
    UserProfileResponse,
    bcrypt_context,
    create_access_token,
    validate_password_strength,
)

# Router definition
router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, user: CreateUserRequest):
    normalized_email = user.email.strip().lower()
    normalized_fullname = user.fullname.strip()

    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_name = db.query(User).filter(User.fullname == normalized_fullname).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="Full name already registered")

    validate_password_strength(user.password)
    new_user = User(
        fullname=normalized_fullname,
        email=normalized_email,
        hashed_password=bcrypt_context.hash(user.password),
        role=user.role,       
        is_active=True
    )
    db.add(new_user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        error_message = str(exc.orig)
        if "users_email_key" in error_message:
            raise HTTPException(status_code=400, detail="Email already registered") from exc
        if "users_fullname_key" in error_message:
            raise HTTPException(status_code=400, detail="Full name already registered") from exc
        raise HTTPException(status_code=400, detail="User already exists") from exc

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


@router.get("/profile/{email}", response_model=UserProfileResponse)
async def get_user_profile(db: db_dependency, email: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileResponse(
        user_id=user.id,
        fullname=user.fullname,
        email=user.email,
        role=user.role,
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(db: db_dependency, payload: UpdateUserProfileRequest):
    user = db.query(User).filter(User.email == payload.current_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    same_email = payload.email.strip().lower() == user.email.strip().lower()
    if not same_email:
        existing_email = db.query(User).filter(User.email == payload.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email is already in use")

    same_name = payload.fullname.strip().lower() == user.fullname.strip().lower()
    if not same_name:
        existing_name = db.query(User).filter(User.fullname == payload.fullname).first()
        if existing_name:
            raise HTTPException(status_code=400, detail="Full name is already in use")

    user.fullname = payload.fullname.strip()
    user.email = payload.email.strip().lower()
    db.commit()
    db.refresh(user)

    return UserProfileResponse(
        user_id=user.id,
        fullname=user.fullname,
        email=user.email,
        role=user.role,
    )


@router.put("/password")
async def update_user_password(db: db_dependency, payload: UpdatePasswordRequest):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not bcrypt_context.verify(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    user.hashed_password = bcrypt_context.hash(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


@router.get("/users", response_model=list[UserListItemResponse])
async def get_all_users(db: db_dependency):
    users = db.query(User).order_by(User.id.desc()).all()
    return [
        UserListItemResponse(
            user_id=u.id,
            fullname=u.fullname,
            email=u.email,
            role=u.role,
            is_active=bool(u.is_active),
        )
        for u in users
    ]

    
