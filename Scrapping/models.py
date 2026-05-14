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
from Database.Tables import Job

class JobAdd(BaseModel):
    id: Optional[int]=None
    title: str = Field(..., max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    company_link: Optional[str] = Field(None, max_length=255)
    job_link: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    source_city: Optional[str] = Field(None, max_length=100)
    salary: Optional[str] = Field(None, max_length=100)
    job_type: Optional[str] = Field(None, max_length=200)
    job_shift: Optional[str] = Field(None, max_length=100)
    experience: Optional[str] = Field(None, max_length=100)
    education: Optional[str] = Field(None, max_length=255)
    posted_date: Optional[str] = Field(None, max_length=100)
    apply_before: Optional[str] = Field(None, max_length=100)
    job_description: Optional[str]
    skills: Optional[str]
    job_source: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = True
    recruiter_id: Optional[int] = None
    application_status: Optional[str] = Field(default="open", max_length=20)
