from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RecruiterSignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    company_name: str = Field(..., alias="companyName", min_length=2, max_length=255)
    company_website: Optional[str] = Field(default=None, alias="companyWebsite", max_length=255)

    model_config = ConfigDict(populate_by_name=True)


class RecruiterLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class RecruiterAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id: int
    role: str = "recruiter"
    name: str
    email: EmailStr
    company_name: Optional[str] = None
    company_website: Optional[str] = None


class JobSchemaFieldResponse(BaseModel):
    name: str
    label: str
    field_type: str
    required: bool = False
    max_length: Optional[int] = None
    default: Optional[Any] = None


class RecruiterApplicantResponse(BaseModel):
    name: str
    email: EmailStr
    resume_file_name: Optional[str] = None
    resume_download_url: Optional[str] = None
    applied_at: Optional[datetime] = None
    status: Optional[str] = None
    site: Optional[str] = None
