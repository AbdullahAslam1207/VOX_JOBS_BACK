
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, LargeBinary
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
    favorite_jobs = relationship("FavoriteJob", back_populates="user", cascade="all, delete")
    profile_pictures = relationship("UserProfilePicture", back_populates="user", cascade="all, delete-orphan")
    resumes = relationship("UserResume", back_populates="user", cascade="all, delete-orphan")
    mustaqbil_credentials = relationship("MustaqbilCredential", back_populates="user", cascade="all, delete-orphan")
    apply_runs = relationship("ApplyRun", back_populates="user", cascade="all, delete-orphan")
    applied_jobs = relationship("AppliedJob", back_populates="user", cascade="all, delete-orphan")
  
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


class FavoriteJob(Base):
    __tablename__ = "favorite_jobs"
    user = relationship("User", back_populates="favorite_jobs")
    job_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
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
    job_description = Column(String)
    skills = Column(String)
    job_source = Column(String(100))
    is_active = Column(Boolean, default=True)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    jobs = relationship("JobShown", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    sender = Column(String(10), nullable=False)
    text = Column(Text, nullable=False)
    sequence_num = Column(Integer, nullable=False, index=True)
    job_sequence_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class JobShown(Base):
    __tablename__ = "jobs_shown"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    job_json = Column(JSON, nullable=False)
    sequence_num = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="jobs")


class UserProfilePicture(Base):
    __tablename__ = "user_profile_pictures"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    email = Column(String(255), index=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    image_data = Column(LargeBinary, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="profile_pictures")


class UserResume(Base):
    __tablename__ = "user_resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    email = Column(String(255), index=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_data = Column(LargeBinary, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="resumes")


class MustaqbilCredential(Base):
    __tablename__ = "mustaqbil_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    email = Column(String(255), index=True, nullable=False)
    mustaqbil_email = Column(String(255), nullable=False)
    mustaqbil_password_encrypted = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="mustaqbil_credentials")


class ApplyRun(Base):
    __tablename__ = "apply_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String(255), index=True, nullable=False)
    url = Column(String(1000), nullable=False)
    site = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="queued")
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="apply_runs")
    applied_jobs = relationship("AppliedJob", back_populates="run", cascade="all, delete-orphan")


class AppliedJob(Base):
    __tablename__ = "applied_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    email = Column(String(255), index=True, nullable=False)
    site = Column(String(50), nullable=False)
    job_url = Column(String(1000), nullable=False)
    job_title = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)
    run_id = Column(Integer, ForeignKey("apply_runs.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="applied_jobs")
    run = relationship("ApplyRun", back_populates="applied_jobs")