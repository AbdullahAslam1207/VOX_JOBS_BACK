from datetime import datetime, timedelta
from typing import Annotated,Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel ,EmailStr, Field, field_validator
from typing import List, Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt

from Database.Database_connection import db_dependency
from Database.Tables import Job, FavoriteJob

class JobCreateRequest(BaseModel):
    id: Optional[int]
    title: str = Field(..., max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    company_link: Optional[str] = Field(None, max_length=255)
    job_link: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    source_city: Optional[str] = Field(None, max_length=100)
    salary: Optional[str] = Field(None, max_length=100)
    job_type: Optional[str] = Field(None, max_length=100)
    job_shift: Optional[str] = Field(None, max_length=100)
    experience: Optional[str] = Field(None, max_length=100)
    education: Optional[str] = Field(None, max_length=255)
    posted_date: Optional[str] = Field(None, max_length=100)
    apply_before: Optional[str] = Field(None, max_length=100)
    job_description: Optional[str]
    skills: Optional[str]
    job_source: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = True

class Config:
    from_attributes = True

class JobList(BaseModel):
    jobs: List[JobCreateRequest]

class FavoriteJobCreate(BaseModel):
    user_id: int
    email: str
    title: str
    company_name: Optional[str]
    company_link: Optional[str]
    job_link: Optional[str]
    location: Optional[str]
    city: Optional[str]
    source_city: Optional[str]
    salary: Optional[str]
    job_type: Optional[str]
    job_shift: Optional[str]
    experience: Optional[str]
    education: Optional[str]
    posted_date: Optional[str]
    apply_before: Optional[str]
    job_description: Optional[str]
    skills: Optional[str]
    job_source: Optional[str]
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True



class FavoriteJobResponse(BaseModel):
    user_id: int
    job_id: int
    email: str
    title: str
    company_name: Optional[str]
    company_link: Optional[str]
    job_link: Optional[str]
    location: Optional[str]
    city: Optional[str]
    source_city: Optional[str]
    salary: Optional[str]
    job_type: Optional[str]
    job_shift: Optional[str]
    experience: Optional[str]
    education: Optional[str]
    posted_date: Optional[str]
    apply_before: Optional[str]
    job_description: Optional[str]
    skills: Optional[str]
    job_source: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

class Delete_Favorite_Job(BaseModel):
    fav_id: int
    user_id: int