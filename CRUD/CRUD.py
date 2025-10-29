from datetime import datetime, timedelta
from typing import Annotated,Literal
from fastapi import APIRouter, Depends, Query
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel ,EmailStr, Field, field_validator
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from Database.Database_connection import db_dependency
from Database.Tables import User
from Auth_service.models import create_access_token,CreateUserRequest,bcrypt_context,UserLoginRequest,Token ,validate_password_strength

from Database.Database_connection import db_dependency
from Database.Tables import Job
from CRUD.models import JobCreateRequest, JobList

# Router definition
router = APIRouter(
    prefix="/CRUD",
    tags=["crud"],
)

@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_jobs(job_list: JobList,db: db_dependency):
    # Simple loop version — clear and easy to follow
    for job_data in job_list.jobs:
        job_dict = job_data.dict()  # Convert Pydantic object to Python dict
        new_job = Job(
            title=job_dict["title"],
            company_name=job_dict.get("company_name"),
            company_link=job_dict.get("company_link"),
            job_link=job_dict.get("job_link"),
            location=job_dict.get("location"),
            city=job_dict.get("city"),
            source_city=job_dict.get("source_city"),
            salary=job_dict.get("salary"),
            job_type=job_dict.get("job_type"),
            job_shift=job_dict.get("job_shift"),
            experience=job_dict.get("experience"),
            education=job_dict.get("education"),
            posted_date=job_dict.get("posted_date"),
            apply_before=job_dict.get("apply_before"),
            job_description=job_dict.get("job_description"),
            skills=job_dict.get("skills"),
            job_source=job_dict.get("job_source"),
            is_active=job_dict.get("is_active", True)
        )

        db.add(new_job)  # Add each job individually

    db.commit()
    return {"message": f"{len(job_list.jobs)} jobs successfully added."}
   
@router.get("/Get_jobs", response_model=list[JobCreateRequest])
async def get_jobs(db: db_dependency):
    jobs = db.query(Job).all()
    return jobs

@router.get("/get_jobs_by_city", response_model=list[JobCreateRequest])
async def get_jobs_by_city(
    city: str,db: db_dependency):
    jobs = db.query(Job).filter(Job.city == city).all()
    return jobs