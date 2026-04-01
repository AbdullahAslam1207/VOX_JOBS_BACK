from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl


class ApplyRunRequest(BaseModel):
    email: EmailStr
    url: HttpUrl
    job_title: Optional[str] = None
    company_name: Optional[str] = None


class ApplyRunCreateResponse(BaseModel):
    run_id: int
    status: str
    site: str


class ApplyRunStatusResponse(BaseModel):
    id: int
    email: str
    url: str
    site: str
    status: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ResumeUploadResponse(BaseModel):
    message: str
    email: str
    file_name: str
    content_type: str
    uploaded_at: datetime


class ResumeMetadataResponse(BaseModel):
    email: str
    file_name: str
    content_type: str
    file_size: int
    uploaded_at: datetime
    updated_at: datetime


class ProfilePictureUploadResponse(BaseModel):
    message: str
    email: str
    file_name: str
    content_type: str
    uploaded_at: datetime


class ProfilePictureMetadataResponse(BaseModel):
    email: str
    file_name: str
    content_type: str
    file_size: int
    uploaded_at: datetime
    updated_at: datetime


class MustaqbilCredentialRequest(BaseModel):
    email: EmailStr
    mustaqbil_email: EmailStr
    mustaqbil_password: str


class MustaqbilCredentialResponse(BaseModel):
    email: str
    mustaqbil_email: str
    mustaqbil_password: str
    created_at: datetime
    updated_at: datetime


class AppliedJobResponse(BaseModel):
    id: int
    user_id: int
    email: str
    site: str
    job_url: str
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    status: str
    run_id: Optional[int] = None
    error_message: Optional[str] = None
    applied_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppliedJobListResponse(BaseModel):
    jobs: list[AppliedJobResponse]
    total: int
