
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from Database.database import Base
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    fullname = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(512), nullable=False)
    role = Column(String(20), default="customer")  
    is_active = Column(Boolean, default=True)
  
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    company_name = Column(String(255))
    company_link = Column(String(255))
    job_link = Column(String(255))
    location = Column(String(255))
    city = Column(String(100))
    source_city = Column(String(100))
    salary = Column(String(100))
    job_type = Column(String(100))
    job_shift = Column(String(100))
    experience = Column(String(100))
    education = Column(String(255))
    posted_date = Column(String(100))
    apply_before = Column(String(100))
    job_description = Column(Text)
    skills = Column(Text)
    job_source = Column(String(100))
    is_active = Column(Boolean, default=True)
